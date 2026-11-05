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
    os.makedirs(outdir, exist_ok=True); json.dump(rows, open(path, "w"))
    return rows
