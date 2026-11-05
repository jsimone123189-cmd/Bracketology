from __future__ import annotations
"""Per-season leak-free feature table (cached to data/features/{year}.json)."""
import json, os
from . import dataset, history, metrics
from .sources import torvik
from .teams import key

def build_year(year: int, outdir="data/features") -> list[dict]:
    path = f"{outdir}/{year}.json"
    if os.path.exists(path): return json.load(open(path))
    rows, rep = dataset.build_year(year)
    day = history.SELECTION_SUNDAY[year]
    games = torvik.collect_games(year)["rows"]
    for g in games:
        g["team_key"], g["opp_key"] = key(g["team"]), key(g["opp"]); m, d, y = g["date"].split("/")
        g["date_iso"] = f"20{y}-{int(m):02d}-{int(d):02d}"
    from .sources import bracketmatrix as bm
    from .teams import key as _k
    mx = bm.collect(year); cons = {_k(t): v for t, v in mx["consensus"].items()}
    for r in rows:
        avg, n = cons.get(r["key"], (17.0, 0))
        r["cons_avg"], r["cons_share"] = avg, n / max(1, mx["n_brackets"])
        r["cons_avg_all"] = avg * (n / max(1, mx["n_brackets"])) + 17.0 * (1 - n / max(1, mx["n_brackets"]))
    nr = {r["key"]: r["net"] for r in rows}
    M = metrics.compute(games, nr, day)
    for r in rows: r.update(M.get(r["key"], {}))
    # conference context (committee bias vs. pure metrics): league code from the game log, league strength
    conf_of = {}
    for g in games:
        conf_of.setdefault(g["team_key"], g["conf"])
    byconf = {}
    for r in rows:
        r["lg"] = conf_of.get(r["key"], "")
        byconf.setdefault(r["lg"], []).append(r.get("rating", 0.0))
    strength = {c: float(sorted(v, reverse=True)[:4] and sum(sorted(v, reverse=True)[:4]) / len(sorted(v, reverse=True)[:4])) for c, v in byconf.items()}
    for r in rows:
        r["conf_strength"] = strength.get(r["lg"], 0.0)
        r["is_power"] = 1.0 if r["lg"] in ("ACC", "B12", "BE", "B10", "SEC") else 0.0
    os.makedirs(outdir, exist_ok=True); json.dump(rows, open(path, "w"))
    return rows
