from __future__ import annotations
"""Historical walk-through of the review tool (local only; needs the local Torvik logs and data/history/edge_timing).
Season h is rebuilt a week before Selection Sunday (D-7) and at Selection Sunday, with the model and shadow trained without h.
Demo edits replay some of the owner's actual 2026 Matrix-bracket moves, to show logging, freezing and grading. They are not advice."""
import json, os
from datetime import date, timedelta, datetime, timezone
from . import dataset, features, metrics, model, project, review
from .history import SELECTION_SUNDAY
from .shadow_anchor import annotate
from .sources import torvik
from .teams import key

DEMO_EDITS_2026 = [
    {"op": "move", "team": "saintlouis", "to_line": 9, "reason_code": "committee_precedent", "confidence": 2, "explanation": "Demo: owner's 2026 call"},
    {"op": "move", "team": "byu", "to_line": 6, "reason_code": "metric_disagreement", "confidence": 2, "explanation": "Demo"},
    {"op": "move", "team": "texasaandm", "to_line": 10, "reason_code": "schedule_quality", "confidence": 1, "explanation": "Demo"},
    {"op": "move", "team": "saintmarysca", "to_line": 7, "reason_code": "committee_precedent", "confidence": 2, "explanation": "Demo"},
    {"op": "add", "team": "miamioh", "remove": "auburn", "reason_code": "other", "confidence": 2, "explanation": "Demo: owner had Miami (OH) in, Auburn out"},
]

def rows_at(season: int, day: str, net: dict | None) -> tuple[list[dict], list[dict]]:
    games = annotate(torvik.collect_games(season, ttl=10 ** 9)["rows"], key)
    rows = [dict(r) for r in features.build_year(season)]
    sw = dataset.INELIGIBLE_CHAMPS.get(season, {}); champs = {key(sw.get(t, t)) for t in dataset.completed_champions(games, day).values()}
    for r in rows:
        if net is not None: r["net"] = net.get(r["key"], 365)
        r["champ"] = r["key"] in champs; r.pop("projected_auto", None)
    M = metrics.compute(games, {r["key"]: r["net"] for r in rows}, day); wl = {}; seen = set()
    for g in games:
        if g["date_iso"] > day or (g["date_iso"], g["team_key"], g["opp_key"]) in seen: continue
        seen.add((g["date_iso"], g["team_key"], g["opp_key"])); w, l = wl.get(g["team_key"], (0, 0)); wl[g["team_key"]] = (w + g["win"], l + (not g["win"]))
    for r in rows:
        r.update(M.get(r["key"], {})); r["w"], r["l"] = wl.get(r["key"], (r["w"], r["l"]))
        for f in ("in_field", "seed", "ov"): r.pop(f, None)       # the review never sees the answer
    return rows, games

def demo(season: int = 2026, which: str = "final", outdir: str = "private/review_demo") -> tuple[str, ...]:
    ss = SELECTION_SUNDAY[season]; d7 = (date.fromisoformat(ss) - timedelta(days=7)).isoformat()
    fitted = model.Model().fit(project.training_rows(exclude={season})); shadow = review._shadow({season})
    p7 = f"data/history/edge_timing/{season}_net_d7.json"
    net7 = {key(r["team"]): r["net"] for r in json.load(open(p7))["rows"]} if os.path.exists(p7) else None
    rows, games = rows_at(season, d7, net7)
    prev = review.build(rows, season, fitted, games, d7, shadow, [], None, {"games_through": d7, "net_source": "ncaa (Wayback capture)", "net_asof": d7, "collected_at": f"{d7}T23:00:00Z"})
    prev["generated_at"] = f"{d7}T23:00:00Z"
    out = list(review.write(prev, outdir))
    if which == "d7": return tuple(out)
    edits = [{**e, "id": f"demo{i}", "at": f"{ss}T15:{i:02d}:00Z"} for i, e in enumerate(DEMO_EDITS_2026 if season == 2026 else [])]
    rows, games = rows_at(season, ss, None)
    rv = review.build(rows, season, fitted, games, ss, shadow, edits, prev, {"games_through": ss, "net_source": "ncaa (Saturday-night capture)", "net_asof": ss, "collected_at": f"{ss}T15:30:00Z"})
    rv["generated_at"] = f"{ss}T15:31:00Z"
    out += list(review.write(rv, outdir))
    ef = f"{outdir}/{season}_demo_edits.json"; json.dump(edits, open(ef, "w"), indent=1)
    fz = f"{outdir}/freeze"; p = f"{fz}/{season}_freeze.json"
    for q in (p, p + ".sha256"):
        if os.path.exists(q): os.chmod(q, 0o644); os.remove(q)
    y, mo, d = map(int, ss.split("-"))
    review.freeze(season, folder=outdir, outdir=fz, now=datetime(y, mo, d, 15, 35, tzinfo=timezone.utc), edits_file=ef); out.append(p)
    out.append(json.dumps(review.verify(season, fz, now=datetime(y, mo, d, 16, 5, tzinfo=timezone.utc))["ok"]))
    from .sources import bracketmatrix as bm
    m = bm.collect(season); off = {key(t): int(s) for t, s in m["official"].items()}
    ms = [int(v) for k, v in m["reported"]["SCORE"].items() if v.isdigit() and k != "MATRIX"]
    g = review.grade(json.load(open(p)), off, ms); gp = f"{outdir}/{season}_grade.json"
    json.dump(g, open(gp, "w"), indent=1, default=list); out.append(gp)
    return tuple(out)
