from __future__ import annotations
"""Daily projection: live data -> model bracket -> your overrides -> output files. Run: python -m bracketology.project [season]
Your adjustments live in overrides/{season}.json and are never mixed into the model:
  {"Team Name": {"line": 5, "reason": "..."}, "Other": {"out": true, "reason": "..."}, "Third": {"line": 11, "reason": "..."}}"""
import json, os, re, statistics, sys, time
from datetime import date, datetime
from . import fieldformat, history, metrics, model
from .dataset import _d
from .features import build_year
from .sources import ncaa_games, ncaa_net, warrennolan
from .teams import key

POWER = {"acc", "big-ten", "big-12", "big-east", "sec"}     # NCAA conference codes
SELECTION_SUNDAY_LIVE = {2027: date(2027, 3, 14)}          # confirm each season; games after this date are ignored

def net_is_current(asof: str | None, season: int) -> bool:
    """The NCAA feed keeps showing last season's final NET until the new one is published in-season."""
    m = re.search(r"([A-Za-z]{3})\.? (\d+) (\d{4})", asof or "")
    if not m: return False
    return datetime.strptime(" ".join(m.groups()), "%b %d %Y").date() >= date(season - 1, 11, 1)

def live_rows(season: int, today: str | None = None) -> tuple[list[dict], list[str]]:
    """Live data reachable from GitHub Actions: NCAA results, arenas and NET, plus Warren Nolan's table and auto-bids.
    Torvik refuses cloud servers, so his files are used only for the local training history."""
    today = today or time.strftime("%Y-%m-%d", time.gmtime()); warn = []
    wn = {key(r["team"]): r for r in warrennolan.collect(season)["rows"]}
    net = {}
    try:
        feed = ncaa_net.collect()
        if net_is_current(feed["asof"], season): net = {key(r["team"]): r["net"] for r in feed["rows"]}
        else: warn.append(f"Official NCAA NET not published for {season} yet (feed shows {feed['asof']}).")
    except Exception as e: warn.append(f"NCAA NET unavailable: {e}")
    if not net:
        net = {k: r["r_net"] for k, r in wn.items() if "r_net" in r}; warn.append("Using Warren Nolan's NET column in place of the official feed.")
    universe = set(wn)
    cutoff = SELECTION_SUNDAY_LIVE.get(season)
    games = ncaa_games.season_games(season, date.fromisoformat(today), universe, key, end=cutoff)
    names, lg, rec = {}, {}, {}
    for g in games:
        g["team_key"], g["opp_key"], g["date_iso"] = key(g["team"]), key(g["opp"]), _d(g["date"])
        if g["team_key"] in universe:
            names[g["team_key"]] = g["team"]; lg[g["team_key"]] = g["conf"]
            if g["opp_key"] in universe or True:
                w, l = rec.get(g["team_key"], (0, 0)); rec[g["team_key"]] = (w + g["win"], l + (not g["win"]))
    first = metrics.compute(games, {k: 100 for k in universe}, today)
    missing = [k for k in universe if k not in net]
    if missing: warn.append(f"{len(missing)} teams have no NET rank and use their own rating rank: {missing[:5]}")
    ranks = {k: net.get(k, first[k]["rating_rank"]) for k in universe}
    M = metrics.compute(games, ranks, today)
    try: champs = {key(t) for t in warrennolan.autobids(season).values()}
    except Exception as e: champs = set(); warn.append(f"Auto-bid list unavailable, projecting every league: {e}")
    unknown = sorted(c for c in champs if c not in universe)
    if unknown: warn.append(f"Auto-bid names not matched: {unknown}")
    rows = []
    for k in universe:
        w, l = rec.get(k, (0, 0))
        rows.append({"team": names.get(k, wn[k]["team"]), "key": k, "year": season, "net": ranks[k], "w": w, "l": l, "lg": lg.get(k, ""), "champ": k in champs,
                     "is_power": 1.0 if lg.get(k) in POWER else 0.0, **M[k], **{c: v for c, v in wn[k].items() if c.startswith("r_")}})
    played = statistics.median(r["w"] + r["l"] for r in rows)
    if played < 15: warn.append(f"Early season: teams have played a median of {played:.0f} games. The model is trained on full Selection Sunday resumes, so treat this as a rough preview.")
    return rows, warn

def training_rows(exclude=()) -> list[dict]:
    out = []
    for y in history.SELECTION_SUNDAY:
        if y in exclude: continue
        rows = model.prepare(build_year(y)); model.attach_overall(rows, y); out += rows
    return out

def apply_overrides(order: list[dict], rest: list[dict], overrides: dict, season: int) -> tuple[list[dict], list[str]]:
    """Returns the final field and warnings. Every team keeps model_line so your edits can be graded separately."""
    by = {key(r["team"]): r for r in order + rest}; field = {key(r["team"]): r for r in order}; notes = []
    for r in order: r["model_line"] = r["line"]
    for name, o in overrides.items():
        k = key(name)
        if k not in by: notes.append(f"Override ignored, unknown team: {name}"); continue
        if o.get("out"):
            if field.pop(k, None) is None: notes.append(f"{name}: already out of the field")
            continue
        field[k] = by[k]; by[k].setdefault("model_line", None); by[k]["line"] = int(o["line"]); by[k]["override_reason"] = o.get("reason", "")
    final = sorted(field.values(), key=lambda r: (r["line"], -r["rank_score"]))
    sizes = fieldformat.line_sizes(season)
    if len(final) != sum(sizes): notes.append(f"Field has {len(final)} teams, expected {sum(sizes)}")
    for i, n in enumerate(sizes, 1):
        c = sum(r["line"] == i for r in final)
        if c != n: notes.append(f"Line {i} has {c} teams; usual size is {n}")
    return final, notes

def closest_calls(order: list[dict], rest: list[dict], n: int = 12) -> dict:
    """Where your review time is best spent: tightest line boundaries and the bubble."""
    gaps = [(order[i]["rank_score"] - order[i + 1]["rank_score"], order[i], order[i + 1]) for i in range(len(order) - 1) if order[i]["line"] != order[i + 1]["line"]]
    gaps.sort(key=lambda g: g[0])
    atl = [r for r in order if not r["champ"] and not r.get("projected_auto")]
    return {"line_boundaries": [{"line": a["line"], "team_above": a["team"], "team_below": b["team"], "gap": round(g, 3)} for g, a, b in gaps[:n]],
            "last_in": [{"team": r["team"], "p_in": round(r["p_in"], 3), "line": r["line"]} for r in sorted(atl, key=lambda r: r["p_in"])[:8]],
            "first_out": [{"team": r["team"], "p_in": round(r["p_in"], 3)} for r in rest[:8]]}

def build(rows: list[dict], season: int, fitted: model.Model, overrides: dict | None = None) -> dict:
    model.prepare(rows); fitted.score(rows)
    field, rest = model.choose_field(rows, season); order = model.assign_lines(field, season)
    final, notes = apply_overrides(order, rest, overrides or {}, season)
    keep = ("overall", "team", "line", "model_line", "override_reason", "p_in", "champ", "projected_auto", "lg", "w", "l", "net", "r_kpi", "r_sor", "r_wab", "r_bpi", "r_kp", "r_trk")
    return {"season": season, "max_score": fieldformat.max_score(season), "notes": notes,
            "field": [{k: r[k] for k in keep if k in r} for r in final], "closest_calls": closest_calls(order, rest)}

def grade(result: dict, official: dict[str, int]) -> dict:
    """After Selection Sunday: did the model or your edits score better? official = {team: seed line}."""
    from .sources.bracketmatrix import score
    off = {key(t): s for t, s in official.items()}
    final = {key(r["team"]): r["line"] for r in result["field"]}
    base = {key(r["team"]): r["model_line"] for r in result["field"] if r.get("model_line")}
    return {"model": score(base, off), "final": score(final, off)}

def main(season: int | None = None) -> int:
    t = time.gmtime(); season = season or (t.tm_year + (1 if t.tm_mon >= 8 else 0))
    rows, warn = live_rows(season)
    path = f"overrides/{season}.json"; overrides = json.load(open(path)) if os.path.exists(path) else {}
    result = build(rows, season, model.Model().fit(training_rows(exclude={season})), overrides)
    result["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()); result["warnings"] = warn + result.pop("notes")
    os.makedirs("data/output", exist_ok=True); json.dump(result, open(f"data/output/projection_{season}.json", "w"), indent=1)
    print("\n".join(result["warnings"]) or "no warnings")
    for r in result["field"][:8]: print(r["line"], r["team"], round(r["p_in"], 3))
    print(f"... {len(result['field'])} teams. Written to data/output/projection_{season}.json")
    return 0

if __name__ == "__main__":
    sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else None))
