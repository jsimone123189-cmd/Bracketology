from __future__ import annotations
"""Daily projection: live data -> model bracket -> your overrides -> output files. Run: python -m bracketology.project [season]
Your adjustments live in overrides/{season}.json and are never mixed into the model. ledger.py has the format and rules."""
import json, os, re, statistics, sys, time
from datetime import date, datetime
from . import checks, fieldformat, history, ledger, metrics, model
from .dataset import _d, completed_champions
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

def live_rows(season: int, today: str | None = None, info: dict | None = None) -> tuple[list[dict], list[str]]:
    """Live data reachable from GitHub Actions: NCAA results, arenas and NET, plus Warren Nolan's table and auto-bids.
    Torvik refuses cloud servers, so his files are used only for the local training history.
    info, if given, receives what the snapshot needs to show where this run's inputs came from."""
    today = today or time.strftime("%Y-%m-%d", time.gmtime()); warn = []; info = info if info is not None else {}
    wn = {key(r["team"]): r for r in warrennolan.collect(season)["rows"]}
    net = {}; info.update(net_source="ncaa", net_asof=None); feed_records = {}
    try:
        feed = ncaa_net.collect(); info["net_asof"] = feed["asof"]
        if net_is_current(feed["asof"], season):
            net = {key(r["team"]): r["net"] for r in feed["rows"]}; feed_records = {key(r["team"]): r["record"] for r in feed["rows"]}
        else: warn.append(f"Official NCAA NET not published for {season} yet (feed shows {feed['asof']}).")
    except Exception as e: warn.append(f"NCAA NET unavailable: {e}")
    if not net:
        net = {k: r["r_net"] for k, r in wn.items() if "r_net" in r}; warn.append("Using Warren Nolan's NET column in place of the official feed."); info["net_source"] = "warren_nolan"
    universe = set(wn); status = {}
    cutoff = SELECTION_SUNDAY_LIVE.get(season)
    games = ncaa_games.season_games(season, date.fromisoformat(today), universe, key, end=cutoff, warn=warn, status=status)
    info.update(games_through=min(date.fromisoformat(today), cutoff).isoformat() if cutoff else today, game_rows=len(games))
    names, lg, rec, played_all = {}, {}, {}, {}
    for g in games:
        g["team_key"], g["opp_key"], g["date_iso"] = key(g["team"]), key(g["opp"]), _d(g["date"])
        if g["team_key"] in universe:
            names[g["team_key"]] = g["team"]; lg[g["team_key"]] = g["conf"]
            played_all[g["team_key"]] = played_all.get(g["team_key"], 0) + 1
            if g["opp_key"] in universe:     # D-I games only, the same way training records are counted
                w, l = rec.get(g["team_key"], (0, 0)); rec[g["team_key"]] = (w + g["win"], l + (not g["win"]))
    first = metrics.compute(games, {k: 100 for k in universe}, today)
    missing = [k for k in universe if k not in net]
    if missing: warn.append(f"{len(missing)} teams have no NET rank and use their own rating rank: {missing[:5]}")
    ranks = {k: net.get(k, first[k]["rating_rank"]) for k in universe}
    M = metrics.compute(games, ranks, today)
    listed_ok = True
    try: champs = {key(t) for t in warrennolan.autobids(season).values()}
    except Exception as e: champs = set(); listed_ok = False; warn.append(f"Auto-bid list unavailable, using champions from NCAA results: {e}")
    ncaa_champs = ncaa_champions(games, universe, today)
    if not listed_ok: champs = set(ncaa_champs)
    info.update(champions=sorted(champs), ncaa_champions=sorted(ncaa_champs))
    unknown = sorted(c for c in champs if c not in universe)
    if unknown: warn.append(f"Auto-bid names not matched: {unknown}")
    rows = []
    for k in universe:
        w, l = rec.get(k, (0, 0))
        rows.append({"team": names.get(k, wn[k]["team"]), "key": k, "year": season, "net": ranks[k], "w": w, "l": l, "lg": lg.get(k, ""), "champ": k in champs,
                     "is_power": 1.0 if lg.get(k) in POWER else 0.0, **M[k], **{c: v for c, v in wn[k].items() if c.startswith("r_")}})
    today_d = date.fromisoformat(today); decided = bool(cutoff) and today_d >= cutoff
    age = None
    m = re.search(r"([A-Za-z]{3})\.? (\d+) (\d{4})", info["net_asof"] or "")
    if m and info["net_source"] == "ncaa": age = (today_d - datetime.strptime(" ".join(m.groups()), "%b %d %Y").date()).days
    found = checks.source_health(today_d, season, info["net_source"], age, len(universe), status["missing_days"], status["arena_unknown"], status["arena_total"])
    found += checks.team_matching(universe, set(net) if info["net_source"] == "ncaa" else set(), played_all, today_d, season)
    di_games = {k: sum(v) for k, v in rec.items()}
    if feed_records: found += checks.game_counts(di_games, feed_records, ranks, "the NCAA NET records")
    found += checks.game_counts(di_games, {k: r["record"] for k, r in wn.items()}, ranks, "Warren Nolan's records")
    if listed_ok: found += checks.champions(set(ncaa_champs), champs, decided)
    else: found.append({"level": "alert", "check": "champions", "message": "Auto-bid list unavailable, so champions come from NCAA results alone."})
    info["checks"] = found
    played = statistics.median(r["w"] + r["l"] for r in rows)
    if played < 15: warn.append(f"Early season: teams have played a median of {played:.0f} games. The model is trained on full Selection Sunday resumes, so treat this as a rough preview.")
    return rows, warn

def ncaa_champions(games: list[dict], universe: set[str], day: str) -> set[str]:
    """Conference champions worked out from NCAA results alone, as an independent check on the auto-bid list."""
    ct = [dict(g, type=2) for g in games if g.get("ct") and g["team_key"] in universe and g["opp_key"] in universe]
    return {key(t) for t in completed_champions(ct, day).values()}

def training_rows(exclude=()) -> list[dict]:
    out = []
    for y in history.SELECTION_SUNDAY:
        if y in exclude: continue
        rows = model.prepare(build_year(y)); model.attach_overall(rows, y); out += rows
    return out

def model_bracket(order: list[dict]) -> list[dict]:
    """The untouched model bracket. Take this before apply_overrides, which removes and moves teams."""
    return [{"key": r["key"], "team": r["team"], "line": r["line"], "overall": r["overall"], "p_in": round(r["p_in"], 4),
             "champ": bool(r["champ"]), "projected_auto": bool(r.get("projected_auto"))} for r in order]

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
        old = field[k]["line"] if k in field else None
        field[k] = by[k]; by[k].setdefault("model_line", None); by[k]["line"] = int(o["line"]); by[k]["override_reason"] = o.get("reason", "")
        if o.get("swap_with"):      # the other team takes this team's old line, or its place in the field
            other = field.get(key(o["swap_with"]))
            if other is None: notes.append(f"{name}: swap team {o['swap_with']} is not in the field")
            elif old is None: field.pop(key(o["swap_with"]))
            else: other["line"] = old; other["override_reason"] = f"Swapped with {name}: {o.get('reason', '')}"
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
    field, rest = model.choose_field(rows, season); order = model.assign_lines(field, season); untouched = model_bracket(order)
    final, notes = apply_overrides(order, rest, overrides or {}, season)
    keep =("overall", "team", "line", "model_line", "override_reason", "p_in", "champ", "projected_auto", "lg", "w", "l", "net", "r_kpi", "r_sor", "r_wab", "r_bpi", "r_kp", "r_trk")
    return {"season": season, "max_score": fieldformat.max_score(season), "notes": notes, "model_bracket": untouched,
            "field": [{k: r[k] for k in keep if k in r} for r in final], "closest_calls": closest_calls(order, rest)}

def grade(result: dict, official: dict[str, int]) -> dict:
    """After Selection Sunday: did the model or your edits score better? official = {team: seed line}.
    Takes a saved snapshot or the output of build()."""
    from .sources.bracketmatrix import score
    off = {key(t): s for t, s in official.items()}
    final = {key(r["team"]): r["line"] for r in result.get("teams", result.get("field"))}
    base = {key(r["team"]): r["line"] for r in result["model_bracket"]}
    return {"model": score(base, off), "final": score(final, off)}

def main(season: int | None = None) -> int:
    t = time.gmtime(); season = season or (t.tm_year + (1 if t.tm_mon >= 8 else 0))
    rows, warn = live_rows(season)
    path = f"overrides/{season}.json"; overrides, rejected = ledger.validate(json.load(open(path)) if os.path.exists(path) else {}); warn += rejected
    result = build(rows, season, model.Model().fit(training_rows(exclude={season})), overrides)
    result["generated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()); result["warnings"] = warn + result.pop("notes")
    os.makedirs("data/output", exist_ok=True); json.dump(result, open(f"data/output/projection_{season}.json", "w"), indent=1)
    print("\n".join(result["warnings"]) or "no warnings")
    for r in result["field"][:8]: print(r["line"], r["team"], round(r["p_in"], 3))
    print(f"... {len(result['field'])} teams. Written to data/output/projection_{season}.json")
    return 0

if __name__ == "__main__":
    sys.exit(main(int(sys.argv[1]) if len(sys.argv) > 1 else None))
