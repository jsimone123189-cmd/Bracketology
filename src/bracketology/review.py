from __future__ import annotations
"""Owner-only review tool (docs/37-38). Never published on the public site, and production code doesn't call it.
Builds, for one moment in the season:
  B1 frozen v2.0 (the untouched model bracket), B2 the head-to-head/common-opponent shadow, B3 v2.0 plus the owner's logged edits,
plus per-team evidence, "why the model might be wrong" flags, and a change report against the previous review.
Edits live in reviews/{season}.json (a list, oldest first). Every edit keeps line sizes valid by construction: the bracket is an
ordered list and lines come from the format's slots, so moving a team shifts exactly one team across each boundary it passes.
Run: python -m bracketology.review build [season] | demo 2026 [d7|final] | freeze [season] | grade [season] [official.json]"""
import hashlib, json, math, os, statistics, sys, time
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import numpy as np
from . import fieldformat, model, project
from .report import team_points
from .shadow_h2h import PairEvidence, ShadowH2H

REASONS = {"injury_or_availability": "Injury or availability", "recent_form": "Recent form", "committee_precedent": "Committee precedent",
           "metric_disagreement": "Metrics disagree", "head_to_head": "Head-to-head", "schedule_quality": "Schedule quality",
           "conference_tournament": "Conference tournament", "bracketing_rule": "Bracketing rule", "other": "Other (explain)"}
OPS = {"move", "swap", "add", "remove", "undo"}

# ------------------------------------------------------------------ edit engine
def lines_of(order: list[str], season: int) -> dict[str, int]:
    slots = fieldformat.format_for(season).slots
    return {k: slots[i] for i, k in enumerate(order)}

def _line_span(slots: list[int], line: int) -> tuple[int, int]:
    if line not in slots: raise ValueError(f"line {line} doesn't exist")
    return slots.index(line), len(slots) - 1 - slots[::-1].index(line)

def check_edit(e: dict) -> list[str]:
    bad = []
    if e.get("op") not in OPS: bad.append(f"op must be one of {sorted(OPS)}")
    if e.get("op") != "undo":
        if e.get("reason_code") not in REASONS: bad.append("reason_code missing or unknown")
        if e.get("reason_code") == "other" and not (e.get("explanation") or "").strip(): bad.append("'other' needs an explanation")
        if e.get("confidence") not in (1, 2, 3): bad.append("confidence must be 1, 2 or 3")
    if not e.get("id") or not e.get("at"): bad.append("needs id and at")
    elif _when(e["at"]) is None: bad.append("at must be an ISO timestamp")
    return bad

def apply_edits(order: list[str], rest: list[str], edits: list[dict], season: int, info: dict[str, dict]) -> tuple[list[str], list[dict], list[str]]:
    """order: field team keys in model order (best first). rest: non-field keys, best at-large candidate first.
    info: key -> {champ, projected_auto, rank_score, p_in, team}. Returns the new order, one record per edit, and notes."""
    slots = fieldformat.format_for(season).slots; order, rest = list(order), list(rest); notes, out = [], []
    undone = {e.get("undo_of") or e["id"] for e in edits if e.get("op") == "undo"}     # undo_of names the retracted edit (older logs reuse its id)
    auto = lambda k: bool(info[k].get("champ") or info[k].get("projected_auto"))
    def insert_by_score(k):
        i = next((j for j, x in enumerate(order) if info[x]["rank_score"] < info[k]["rank_score"]), len(order)); order.insert(i, k)
    for e in edits:
        if e.get("op") == "undo" or e["id"] in undone: continue
        bad = check_edit(e)
        if bad: notes.append(f"Edit {e.get('id')} skipped: {'; '.join(bad)}"); continue
        before = lines_of(order, season); before_order = list(order); op = e["op"]; k = e.get("team")
        try:
            if k not in info: raise ValueError(f"unknown team {k}")
            if op == "move":
                if k not in order: raise ValueError(f"{info[k]['team']} isn't in the field")
                cur = order.index(k); a, b = _line_span(slots, int(e["to_line"]))
                if slots[cur] != int(e["to_line"]): order.pop(cur); order.insert(a if int(e["to_line"]) < slots[cur] else b, k)
            elif op == "swap":
                o = e.get("with")
                if k not in order or o not in order: raise ValueError("both teams must be in the field")
                i, j = order.index(k), order.index(o); order[i], order[j] = o, k
            elif op == "add":
                if k in order: raise ValueError(f"{info[k]['team']} is already in the field")
                x = e.get("remove") or next((t for t in reversed(sorted(order, key=lambda t: info[t]["p_in"], reverse=True)) if not auto(t)), None)
                if x not in order or auto(x): raise ValueError("the team removed must be an at-large team in the field")
                a = _line_span(slots, int(e["to_line"]))[0] if e.get("to_line") else None      # validated before anything changes
                order.remove(x); rest.insert(0, x); rest = [t for t in rest if t != k]
                if a is not None: order.insert(a, k)
                else: insert_by_score(k)
            elif op == "remove":
                if k not in order or auto(k): raise ValueError("only at-large teams in the field can be removed")
                y = e.get("add") or next((t for t in rest if t not in order), None)
                if y is None or y in order: raise ValueError("no replacement available")
                order.remove(k); rest = [t for t in rest if t != y]; rest.insert(0, k); insert_by_score(y)
        except (ValueError, KeyError, TypeError) as err:
            notes.append(f"Edit {e['id']} not applied: {err}"); continue
        after = lines_of(order, season)
        changed = sorted(t for t in set(before) | set(after) if before.get(t) != after.get(t))
        pos = lambda o, x: o.index(x) + 1 if x in o else None
        out.append({**e, "phase": e.get("phase") or phase(season, e["at"]), "line_before": before.get(k), "line_after": after.get(k),
                    "overall_before": before_order.index(k) + 1 if k in before_order else None, "overall_after": pos(order, k), "teams_changed": changed})
    return order, out, notes

# ------------------------------------------------------------------ evidence
RESUME = [("NET", "net", 1), ("WAB rank", "rk_wab", 1), ("SOR rank", "rk_sor", 1), ("Rating rank", "rk_rating", 1)]
THIRD = [("KPI", "r_kpi"), ("ESPN SOR", "r_sor"), ("BPI", "r_bpi"), ("KenPom", "r_kp"), ("T-Rank", "r_trk"), ("Official WAB", "r_wab")]
ZFEAT = [("NET", lambda r: -math.log(r["net"])), ("WAB", lambda r: r["wab"]), ("SOR", lambda r: r["sor"]), ("rating", lambda r: r["rating"]),
         ("Q1 wins", lambda r: r["cq1_w"]), ("Q1A wins", lambda r: r["q1a_w"]), ("few Q1 losses", lambda r: -r["cq1_l"]),
         ("no Q3/Q4 losses", lambda r: -(r["cq3_l"] + r["cq4_l"])), ("schedule", lambda r: r["sos"]), ("road wins", lambda r: r["road_w"])]

def _ranks(rows, f):
    return {r["key"]: i + 1 for i, r in enumerate(sorted(rows, key=lambda r: -r[f]))}

def ct_record(games: list[dict], k: str, day: str) -> tuple[int, int]:
    w = l = 0; seen = set()
    for g in games:
        if g["team_key"] != k or g["date_iso"] > day or not (g.get("ct") or g.get("type") == 2): continue
        sig = (g["date_iso"], g["opp_key"])
        if sig in seen: continue
        seen.add(sig); w += bool(g["win"]); l += not g["win"]
    return w, l

def build(rows: list[dict], season: int, fitted: model.Model, games: list[dict], day: str, shadow: ShadowH2H | None = None,
          edits: list[dict] | None = None, prev: dict | None = None, sources: dict | None = None) -> dict:
    """rows: live or historical rows (unprepared). day: games cutoff for evidence. prev: the previous review, for the change report."""
    model.prepare(rows); fitted.score(rows)
    field, rest_rows = model.choose_field(rows, season); order_rows = model.assign_lines(field, season); project.confidence(order_rows, season)
    R = {r["key"]: r for r in rows}
    for f, n in (("wab", "rk_wab"), ("sor", "rk_sor"), ("rating", "rk_rating")):
        for k, v in _ranks(rows, f).items(): R[k][n] = v
    ev = PairEvidence(games, day)
    m_order = [r["key"] for r in order_rows]; rest = [r["key"] for r in rest_rows]
    info = {k: {"team": R[k]["team"], "lg": R[k].get("lg"), "champ": bool(R[k]["champ"]), "projected_auto": bool(R[k].get("projected_auto")), "rank_score": R[k]["rank_score"], "p_in": R[k]["p_in"]} for k in R}
    B1 = lines_of(m_order, season)
    B2 = None
    if shadow is not None:
        sc = shadow.scores(order_rows, ev); B2 = lines_of(sorted(m_order, key=lambda k: -sc[k]), season)
    edits = edits or []; b3_order, applied, notes = apply_edits(m_order, rest, edits, season, info); B3 = lines_of(b3_order, season)
    s = [R[k]["rank_score"] for k in m_order]; u = statistics.median(abs(a - b) for a, b in zip(s, s[1:])) or 1e-9
    Z = np.array([[fn(R[k]) for _, fn in ZFEAT] for k in m_order]); Z = (Z - Z.mean(0)) / (Z.std(0) + 1e-9)
    logs = {k: [math.log(max(1, R[k][f])) for _, f, _ in RESUME] + [math.log(R[k][f]) for _, f in THIRD if R[k].get(f)] for k in m_order}
    spread = {k: max(v) - min(v) for k, v in logs.items()}; q75 = float(np.percentile(list(spread.values()), 75))
    teams = []
    for i, k in enumerate(m_order):
        r = R[k]; line = B1[k]; nb = [j for j in range(max(0, i - 4), min(len(m_order), i + 5)) if j != i]
        up = [R[x]["rank_score"] for x in m_order if B1[x] == line - 1]; dn = [R[x]["rank_score"] for x in m_order if B1[x] == line + 1]
        d_up = (min(up) - r["rank_score"]) / u if up else None; d_dn = (r["rank_score"] - max(dn)) / u if dn else None
        diff = Z[i] - Z[nb].mean(0); idx = np.argsort(diff)
        ctw, ctl = ct_record(games, k, day)
        neighbours = []
        for j in nb:
            o = m_order[j]; w, l = ev.games_between(k, o)
            neighbours.append({"key": o, "team": R[o]["team"], "line": B1[o], "overall": j + 1, "gap_u": round((R[o]["rank_score"] - r["rank_score"]) / u, 2),
                               "h2h": [w, l], "common": ev.common_detail(k, o), "net": R[o]["net"], "rk_wab": R[o]["rk_wab"], "q1": f"{R[o]['cq1_w']}-{R[o]['cq1_l']}"})
        flags = []
        c = r.get("confidence", 1.0)
        if c < .5: flags.append(f"Low confidence: about {c:.0%} chance of exactly this line. Nearly all 2+ line misses come from teams under 50% (docs/12).")
        if d_up is not None and d_up < 1: flags.append(f"Within {d_up:.1f} positions' worth of score of line {line - 1}.")
        if d_dn is not None and d_dn < 1: flags.append(f"Within {d_dn:.1f} positions' worth of score of line {line + 1}.")
        if r["champ"] and not r["is_power"]: flags.append("Small-conference champion: v2.0's weakest group, misses go both ways (docs/11).")
        if not r["champ"] and not r["is_power"]: flags.append("Non-power at-large: v2.0's bias here flips from season to season (docs/11).")
        if not r["champ"] and r["is_power"] and 33 <= r["net"] <= 56: flags.append("Power team with NET 33-56: the profile v2.0 most often wrongly selects (docs/11).")
        if spread[k] >= q75: flags.append(f"Metrics disagree: best {min(zip(logs[k], [n for n, _, _ in RESUME] + [n for n, f in THIRD if r.get(f)]))[1]}, worst {max(zip(logs[k], [n for n, _, _ in RESUME] + [n for n, f in THIRD if r.get(f)]))[1]}.")
        for o in nb:
            ok_ = m_order[o]; w, l = ev.games_between(k, ok_)
            if w > l and B1[ok_] < line: flags.append(f"Beat {R[ok_]['team']} (line {B1[ok_]}) head-to-head {w}-{l}.")
            if l > w and B1[ok_] > line: flags.append(f"Lost to {R[ok_]['team']} (line {B1[ok_]}) head-to-head {w}-{l}.")
        if ctw >= 2: flags.append(f"Won {ctw} conference-tournament games: the committee moved strong tournament runs less than v2.0 does (docs/39-40).")
        if ctl and not ctw: flags.append("Lost its first conference-tournament game: the committee moved these teams less than v2.0 does (docs/39-40).")
        if prev:
            pt = prev.get("teams_by_key", {}).get(k)
            if pt:
                ds = (r["rank_score"] - pt["rank_score"]) / u
                if abs(ds) >= 2 and pt["model_line"] == line: flags.append(f"Score moved {ds:+.1f} positions' worth since {prev['asof']} but its line didn't change.")
                if abs(ds) < .5 and pt["model_line"] != line: flags.append(f"Line changed {pt['model_line']}→{line} since {prev['asof']} mostly because other teams moved.")
        third = {n: r[f] for n, f in THIRD if r.get(f)}
        teams.append({"key": k, "team": r["team"], "lg": r.get("lg"), "overall": i + 1, "model_line": line, "shadow_line": B2.get(k) if B2 else None, "manual_line": B3.get(k),
                      "confidence": round(c, 3), "p_in": round(r["p_in"], 3), "rank_score": round(r["rank_score"], 4), "champ": bool(r["champ"]), "projected_auto": bool(r.get("projected_auto")),
                      "power": bool(r["is_power"]), "boundary_up_u": None if d_up is None else round(d_up, 2), "boundary_down_u": None if d_dn is None else round(d_dn, 2),
                      "resume": {"Record": f"{r['w']}-{r['l']}", "NET": r["net"], "WAB": round(r["wab"], 2), "WAB rank": r["rk_wab"], "SOR rank": r["rk_sor"], "Rating rank": r["rk_rating"],
                                 "Q1A": f"{r['q1a_w']}-{r.get('q1a_l', 0)}", "Q1": f"{r['cq1_w']}-{r['cq1_l']}", "Q2": f"{r['cq2_w']}-{r.get('cq2_l', 0)}", "Q3 losses": r["cq3_l"], "Q4 losses": r["cq4_l"],
                                 "Road wins": r["road_w"], "Neutral wins": r["neutral_w"], "Last 10": round(r["last10"] * 10), "Conf. tourney": f"{ctw}-{ctl}", **third},
                      "advantages": [ZFEAT[j][0] for j in idx[::-1][:2] if diff[j] > .25], "disadvantages": [ZFEAT[j][0] for j in idx[:2] if diff[j] < -.25],
                      "metric_spread": round(spread[k], 2), "neighbours": neighbours, "flags": flags})
    outside = [{"key": r["key"], "team": r["team"], "p_in": round(r["p_in"], 3), "net": r["net"], "lg": r.get("lg"), "rank_score": round(r["rank_score"], 4)} for r in rest_rows[:16]]
    atl = sorted((t for t in teams if not t["champ"] and not t["projected_auto"]), key=lambda t: t["p_in"])
    asof = sources.get("games_through", day) if sources else day
    sources = sources or {}
    inputs = {"collected_at": sources.get("collected_at") or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "games_through": day,
              "latest_game_used": max((g["date_iso"] for g in games if g["date_iso"] <= day), default=None), "net_source": sources.get("net_source"),
              "net_asof": sources.get("net_asof"), "game_rows": sources.get("game_rows", len(games)),
              "conference_games_pending": sources.get("conference_games_pending")}     # None = not checked (only checked on Selection Sunday)
    consistency = {"one_cutoff_for_all_brackets": day, "B2_same_field_as_B1": None if B2 is None else set(B2) == set(B1),
                   "B3_is_B1_plus_logged_edits": True, "field_size": len(B1), "expected_field_size": fieldformat.format_for(season).size}
    out = {"season": season, "asof": asof, "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "model_version": model.MODEL_VERSION,
           "lines": fieldformat.line_sizes(season), "u": u, "sources": sources, "inputs": inputs, "consistency": consistency,
           "shadow": None if shadow is None else {"train_years": sorted(getattr(shadow, "train_years", [])) or None, "fingerprint": fingerprint(shadow)},
           "v2_fingerprint": fingerprint(fitted), "phase": phase(season, asof),
           "teams": teams, "outside": outside, "bubble": {"last_in": [t["key"] for t in atl[:6]], "first_out": [t["key"] for t in outside[:6]]},
           "brackets": {"B1_model": B1, "B2_shadow": B2, "B3_manual": B3}, "edits": applied, "edit_notes": notes, "all_info": {k: {"team": v["team"], "lg": v["lg"], "champ": v["champ"], "projected_auto": v["projected_auto"], "rank_score": round(v["rank_score"], 4), "p_in": round(v["p_in"], 4)} for k, v in info.items() if k in set(m_order) | set(rest[:40])},
           "model_order": m_order, "rest_order": rest[:40]}
    out["teams_by_key"] = {t["key"]: {"rank_score": t["rank_score"], "model_line": t["model_line"], "confidence": t["confidence"], "champ": t["champ"]} for t in teams}
    out["changes"] = change_report(out, prev) if prev else None
    return out

def selection_sunday(season: int) -> date | None:
    from .history import SELECTION_SUNDAY
    return project.SELECTION_SUNDAY_LIVE.get(season) or (date.fromisoformat(SELECTION_SUNDAY[season]) if season in SELECTION_SUNDAY else None)

def fingerprint(m) -> str:
    """SHA-256 of a fitted model's learned numbers (the objects actually used, not a file on disk)."""
    parts = []
    for name in ("coef", "sd", "lr", "rank", "s_sel", "s_seed"):
        o = getattr(m, name, None)
        if o is None: continue
        for a in ("coef_", "intercept_", "mean_", "scale_"):
            if hasattr(o, a): parts.append(np.asarray(getattr(o, a), float).round(12).tobytes())
        if isinstance(o, np.ndarray): parts.append(o.astype(float).round(12).tobytes())
    return hashlib.sha256(b"".join(parts)).hexdigest()

def phase(season: int, asof: str) -> str:
    ss = selection_sunday(season)
    if not ss: return "unknown"
    return "championship_week" if date.fromisoformat(asof[:10]) >= ss - timedelta(days=7) else "pre_championship_week"

def change_report(cur: dict, prev: dict) -> dict:
    P, C = prev["teams_by_key"], cur["teams_by_key"]; names = {t["key"]: t["team"] for t in cur["teams"]}
    names.update({k: v["team"] for k, v in prev.get("all_info", {}).items() if k not in names})
    moved = [{"team": names[k], "from": P[k]["model_line"], "to": C[k]["model_line"]} for k in C if k in P and P[k]["model_line"] != C[k]["model_line"]]
    conf = [{"team": names[k], "from": P[k]["confidence"], "to": C[k]["confidence"]} for k in C if k in P and abs(P[k]["confidence"] - C[k]["confidence"]) >= .15]
    new_champs = sorted(k for k in C if C[k]["champ"] and not (P.get(k) or {}).get("champ"))
    pin = {k: v["p_in"] for k, v in cur["all_info"].items()}; lg = {k: v.get("lg") for k, v in cur["all_info"].items()}
    # bid thief: an unlikely champion (would not be an at-large) from a league that also has at-large teams in the field
    thief = lambda k: pin.get(k, 1) < .5 and any(o != k and lg.get(o) == lg.get(k) and not C[o]["champ"] for o in C)
    return {"since": prev["asof"], "line_changes": sorted(moved, key=lambda m: m["to"]), "entered_field": sorted(names[k] for k in C if k not in P), "left_field": sorted(names.get(k, k) for k in P if k not in C),
            "new_champions": [names[k] for k in new_champs], "bid_thieves": [names[k] for k in new_champs if thief(k)],
            "near_boundary": sorted(t["team"] for t in cur["teams"] if min(x for x in (t["boundary_up_u"], t["boundary_down_u"], 99) if x is not None) < .5),
            "confidence_changes": conf}

# ------------------------------------------------------------------ storage (private; never in the public repo or site)
PRIVATE = "private"          # gitignored. Edits, reviews and freezes stay on the owner's machine (or a private store) only.
def edits_path(season: int) -> str: return f"{PRIVATE}/reviews/{season}.json"
def reviews_dir() -> str: return f"{PRIVATE}/review"
def freeze_dir() -> str: return f"{PRIVATE}/freeze"
_FORBIDDEN = ("data/output/site", "site", "data/output/snapshots")

def _ts(s: str) -> datetime: return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
def _when(s) -> datetime | None:
    """Edit timestamps (browser ISO strings may carry milliseconds). None if missing or unreadable."""
    try: return datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone(timezone.utc)
    except ValueError: return None
def _sha(b: bytes) -> str: return hashlib.sha256(b).hexdigest()
def _file_sha(p: str) -> str | None: return _sha(open(p, "rb").read()) if os.path.exists(p) else None

def load_edits(season: int) -> list[dict]:
    p = edits_path(season)
    return json.load(open(p)) if os.path.exists(p) else []

def write(review: dict, outdir: str | None = None) -> tuple[str, str]:
    from .review_page import render
    outdir = outdir or reviews_dir()
    if any(os.path.abspath(outdir).startswith(os.path.abspath(f)) for f in _FORBIDDEN): raise SystemExit(f"Refusing to write the private review into public output {outdir}.")
    os.makedirs(outdir, exist_ok=True); stamp = review["inputs"]["collected_at"].replace("-", "").replace(":", "")
    jp = f"{outdir}/{review['season']}_{stamp}.json"; json.dump(review, open(jp, "w"), indent=1)
    hp = f"{outdir}/{review['season']}_{stamp}.html"; open(hp, "w").write(render(review))
    return jp, hp

def all_reviews(season: int, folder: str | None = None) -> list[tuple[str, dict]]:
    import glob
    out = []
    for p in sorted(glob.glob(f"{folder or reviews_dir()}/{season}_*.json")):
        try: rv = json.load(open(p))
        except (OSError, ValueError): continue      # a half-written file is skipped, never frozen
        if isinstance(rv, dict) and (rv.get("inputs") or {}).get("collected_at"): out.append((p, rv))
    return sorted(out, key=lambda x: x[1]["inputs"]["collected_at"])

def previous(season: int, collected_at: str, folder: str | None = None) -> dict | None:
    ps = [r for _, r in all_reviews(season, folder) if r["inputs"]["collected_at"] < collected_at]
    return ps[-1] if ps else None

# ------------------------------------------------------------------ freeze, verify, grade
# Two Selection Sunday snapshots (docs/43):
#   research - noon America/New_York, fixed in advance (docs/38). B1, B2, B3 for the 2027 evaluation.
#   final    - the competitive bracket: newest review taken after every Selection Sunday conference final is over, and before
#              the submission deadline. The deadline is not guessed: it stays None until the 2027 selection-show time and the
#              Matrix's final collection time are confirmed, and freezing "final" refuses until it is set (local time, New York).
FINAL_DEADLINE_ET = {2027: None}          # e.g. {2027: "2027-03-14 17:45"}; set and commit once confirmed
KINDS = ("research", "final")

def freeze_deadline(season: int, kind: str = "research") -> datetime:
    ny = ZoneInfo("America/New_York")
    if kind == "final":
        s = FINAL_DEADLINE_ET.get(season)
        if not s: raise SystemExit(f"No confirmed final-snapshot deadline for {season}. Set FINAL_DEADLINE_ET once the selection show and Matrix collection times are known.")
        return datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=ny).astimezone(timezone.utc)
    ss = selection_sunday(season)
    return datetime(ss.year, ss.month, ss.day, 12, 0, tzinfo=ny).astimezone(timezone.utc)

def freeze_path(season: int, outdir: str, kind: str = "research") -> str:
    return f"{outdir}/{season}_freeze.json" if kind == "research" else f"{outdir}/{season}_final_freeze.json"

def pending_conference_games(d: date, ttl: int = 60) -> tuple[list[dict], int] | None:
    """Conference-tournament games scheduled on day d that are not final yet, and how many are scheduled in all
    (scoreboard feed already used by production). None when the feed can't be read: the final freeze treats that as not complete."""
    try:
        from .http import fetch
        from .sources.ncaa_games import url
        out, n = [], 0
        for g in json.loads(fetch(url(d), ttl=ttl, retries=2))["games"]:
            g = g["game"]; h, a = g["home"], g["away"]
            hc = (h.get("conferences") or [{}])[0].get("conferenceSeo", ""); ac = (a.get("conferences") or [{}])[0].get("conferenceSeo", "")
            if h.get("seed") and a.get("seed") and hc and hc == ac:
                n += 1
                if g.get("gameState") != "final": out.append({"conf": hc, "game": f"{a['names']['short']} vs {h['names']['short']}", "state": g.get("gameState"), "start": g.get("startTime")})
        return out, n
    except Exception:
        return None

def results_complete(pending: tuple[list[dict], int] | None, games: list[dict], day: str) -> list[dict] | None:
    """[] only if the scoreboard showed every conference final of the day over before collection AND all of them are in the
    games the model used. None = unknown (treated as not complete)."""
    if pending is None: return None
    left, n = pending
    used = len({g.get("id") or (min(g["team_key"], g["opp_key"]), max(g["team_key"], g["opp_key"])) for g in games if g["date_iso"] == day and g.get("ct")})
    if left: return left
    return [] if used >= n else None

def problems(review: dict, deadline: datetime) -> list[str]:
    """Why a review can't be frozen. Empty list = freezable."""
    bad = []; fmt = fieldformat.format_for(review["season"]); inp = review.get("inputs") or {}
    if not inp.get("collected_at"): return ["no collection time recorded"]
    if _ts(inp["collected_at"]) > deadline: bad.append(f"data collected {inp['collected_at']} after the {deadline:%H:%M}Z cutoff")
    if _ts(review["generated_at"]) > deadline: bad.append(f"generated {review['generated_at']} after the cutoff")
    late = [e.get("id") for e in review.get("edits", []) if (_when(e.get("at")) or deadline) > deadline]
    if late: bad.append(f"edits logged after the cutoff: {late}")
    if inp.get("latest_game_used") and inp["latest_game_used"] > deadline.date().isoformat(): bad.append("uses games dated after Selection Sunday")
    for name, L in review["brackets"].items():
        if L is None: bad.append(f"{name} missing"); continue
        sizes = [sum(1 for v in L.values() if v == l) for l in range(1, 17)]
        if len(L) != fmt.size or sizes != list(fmt.lines): bad.append(f"{name} has {len(L)} teams / line sizes {sizes}, expected {fmt.size} / {list(fmt.lines)}")
    c = review.get("consistency") or {}
    if c.get("B2_same_field_as_B1") is False: bad.append("B2 field differs from B1")
    if review.get("shadow") and review["shadow"].get("train_years") and review["season"] in review["shadow"]["train_years"]: bad.append("shadow was trained on the season being frozen")
    alerts = [x["message"] for x in (review.get("sources") or {}).get("checks", []) if x.get("level") == "alert"]
    if alerts: bad.append(f"data-check alerts: {alerts[:3]}")
    return bad

def full_bracket(review: dict, name: str) -> list[dict]:
    L = review["brackets"][name]; info = review["all_info"]
    return sorted(({"key": k, "team": info.get(k, {}).get("team", k), "line": v, "champ": info.get(k, {}).get("champ"), "projected_auto": info.get(k, {}).get("projected_auto")}
                   for k, v in L.items()), key=lambda r: (r["line"], -info.get(r["key"], {}).get("rank_score", 0)))

def freeze(season: int, folder: str | None = None, outdir: str | None = None, now: datetime | None = None, deadline: datetime | None = None,
           edits_file: str | None = None, kind: str = "research") -> dict:
    """Freezes the newest review whose data were collected before the cutoff and that passes every check.
    kind="final" also prefers the newest review taken after every Selection Sunday conference final was over; if none qualifies
    before the deadline it falls back to the newest valid review and records final_results_complete = false with what was pending.
    Idempotent: if a valid freeze exists it is verified and returned, never overwritten. A late run (missed schedule) may still freeze,
    but only a review collected before the cutoff; frozen_at records when it happened."""
    assert kind in KINDS
    deadline = deadline or freeze_deadline(season, kind); now = now or datetime.now(timezone.utc); outdir = outdir or freeze_dir()
    path = freeze_path(season, outdir, kind)
    if os.path.exists(path):
        v = verify(season, outdir, deadline, write_record=False, kind=kind)
        if not v["ok"]: raise SystemExit(f"{path} exists but fails verification: {v['problems']}. Not overwriting; investigate.")
        return {"status": "already_frozen", "path": path, "sha256": v["sha256"]}
    skipped, valid = [], []
    for p, rv in reversed(all_reviews(season, folder)):
        bad = problems(rv, deadline)
        if bad: skipped.append({"review": os.path.basename(p), "problems": bad})
        else: valid.append((p, rv))
    if not valid: raise SystemExit(f"No freezable review for {season}. Skipped: {skipped}")
    complete = lambda rv: rv["inputs"].get("conference_games_pending") == []
    chosen = next((x for x in valid if complete(x[1])), valid[0]) if kind == "final" else valid[0]
    p, rv = chosen; ep = edits_file or edits_path(season)
    v2 = "models/v2.joblib"
    body = {"schema": 2, "kind": kind, "season": season, "frozen_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "cutoff": deadline.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "final_results_complete": complete(rv), "conference_games_pending": rv["inputs"].get("conference_games_pending"),
            "frozen_after_cutoff": now > deadline, "review_file": os.path.basename(p), "review_sha256": _file_sha(p), "review_generated_at": rv["generated_at"],
            "inputs": rv["inputs"], "sources": {k: v for k, v in rv["sources"].items() if k != "checks"}, "data_checks": rv["sources"].get("checks", []),
            "model": {"version": rv["model_version"], "v2_fingerprint_used": rv.get("v2_fingerprint"), "v2_saved_fingerprint": _saved_fp(v2),
                      "v2_file_sha256": _file_sha(v2), "v2_expected_file_sha256": model.MODEL_SHA256,
                      "shadow_fingerprint_used": (rv.get("shadow") or {}).get("fingerprint"), "shadow_train_years": (rv.get("shadow") or {}).get("train_years"),
                      "code_commit": os.environ.get("GITHUB_SHA") or _git_head()},
            "consistency": rv["consistency"], "brackets": {n: full_bracket(rv, n) for n in rv["brackets"]},
            "edit_history": {"file_sha256": _file_sha(ep), "entries_as_logged": json.load(open(ep)) if os.path.exists(ep) else [], "applied": rv["edits"], "not_applied": rv["edit_notes"]},
            "skipped_reviews": skipped}
    raw = json.dumps(body, sort_keys=True, indent=1).encode()
    os.makedirs(outdir, exist_ok=True); tmp = path + ".tmp"
    with open(tmp, "wb") as f: f.write(raw)
    try: os.link(tmp, path)                                  # atomic create-only: fails if another run froze first
    except FileExistsError:
        os.remove(tmp); return freeze(season, folder, outdir, now, deadline, edits_file, kind)
    os.remove(tmp); open(path + ".sha256", "w").write(_sha(raw) + "\n"); os.chmod(path, 0o444)
    return {"status": "frozen", "path": path, "sha256": _sha(raw), "review": os.path.basename(p), "skipped": skipped}

def model_files() -> dict:
    """Fingerprints of the model files on disk at build time. The Worker's freeze can't read files, so the build records them."""
    v2 = "models/v2.joblib"
    return {"v2_file_sha256": _file_sha(v2), "v2_expected_file_sha256": model.MODEL_SHA256, "v2_saved_fingerprint": _saved_fp(v2),
            "code_commit": os.environ.get("GITHUB_SHA") or _git_head()}

def upload(rv: dict, url: str | None = None) -> dict:
    """Send a review (public data only: B1, B2, evidence; never edits) to the private review Worker. Authenticates with a
    Cloudflare Access service token from the environment (REVIEW_URL, CF_ACCESS_CLIENT_ID, CF_ACCESS_CLIENT_SECRET); prints nothing private."""
    import urllib.request
    url = url or os.environ["REVIEW_URL"]
    if rv.get("edits"): raise SystemExit("refusing to upload a review that carries edits")
    body = json.dumps({k: v for k, v in rv.items() if k != "teams_by_key"}).encode()
    req = urllib.request.Request(url.rstrip("/") + "/api/machine/review", data=body, method="POST", headers={
        "Content-Type": "application/json", "User-Agent": "bracketology-review-upload",
        "CF-Access-Client-Id": os.environ["CF_ACCESS_CLIENT_ID"], "CF-Access-Client-Secret": os.environ["CF_ACCESS_CLIENT_SECRET"]})
    with urllib.request.urlopen(req, timeout=60) as r: return json.loads(r.read())

def _saved_fp(p: str) -> str | None:
    try:
        import joblib; return fingerprint(joblib.load(p)) if os.path.exists(p) else None
    except Exception: return None

def _git_head() -> str | None:
    try:
        import subprocess; return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10).stdout.strip() or None
    except Exception: return None

def verify(season: int, outdir: str | None = None, deadline: datetime | None = None, write_record: bool = True, now: datetime | None = None,
           kind: str = "research") -> dict:
    """Independent check (run after the cutoff). Recomputes the hash, re-checks the cutoff and contents, and writes a separate dated
    verification record. Never modifies the freeze."""
    outdir = outdir or freeze_dir(); deadline = deadline or freeze_deadline(season, kind); path = freeze_path(season, outdir, kind); now = now or datetime.now(timezone.utc)
    res = {"season": season, "kind": kind, "checked_at": now.strftime("%Y-%m-%dT%H:%M:%SZ"), "path": path, "problems": []}
    if not os.path.exists(path): res["problems"].append("no freeze file"); res["ok"] = False
    else:
        raw = open(path, "rb").read(); res["sha256"] = _sha(raw)
        rec = open(path + ".sha256").read().strip() if os.path.exists(path + ".sha256") else None
        if rec != res["sha256"]: res["problems"].append(f"hash mismatch: file {res['sha256']} recorded {rec}")
        b = json.loads(raw); fmt = fieldformat.format_for(season)
        if _ts(b["inputs"]["collected_at"]) > deadline: res["problems"].append("frozen data collected after the cutoff")
        if _ts(b["review_generated_at"]) > deadline: res["problems"].append("frozen review generated after the cutoff")
        if b.get("kind", "research") != kind: res["problems"].append(f"file is a {b.get('kind')} freeze, expected {kind}")
        if b.get("cutoff") != deadline.strftime("%Y-%m-%dT%H:%M:%SZ"): res["problems"].append(f"recorded cutoff {b.get('cutoff')} differs from {deadline:%Y-%m-%dT%H:%M:%SZ}")
        late = [e.get("id") for e in b.get("edit_history", {}).get("applied", []) if (_when(e.get("at")) or deadline) > deadline]
        if late: res["problems"].append(f"edits after the cutoff: {late}")
        for n, rows in b["brackets"].items():
            sizes = [sum(1 for r in rows if r["line"] == l) for l in range(1, 17)]
            if len(rows) != fmt.size or sizes != list(fmt.lines): res["problems"].append(f"{n} incomplete")
        m = b["model"]
        if season in project.SELECTION_SUNDAY_LIVE:      # live seasons must use the frozen v2.0 exactly (historical replays refit without the season)
            if m.get("v2_file_sha256") != m.get("v2_expected_file_sha256"): res["problems"].append("models/v2.joblib differs from the frozen baseline")
            if m.get("v2_fingerprint_used") != m.get("v2_saved_fingerprint"): res["problems"].append("the model used is not the saved v2.0")
        res["ok"] = not res["problems"]; res["frozen_after_cutoff"] = b["frozen_after_cutoff"]
    if write_record:
        os.makedirs(outdir, exist_ok=True)
        json.dump(res, open(f"{outdir}/{season}_{kind}_verify_{res['checked_at'].replace(':', '').replace('-', '')}.json", "w"), indent=1)
    return res

def grade(frozen: dict, official: dict[str, int], matrix_scores: list[int] | None = None) -> dict:
    """Bracket Matrix scores for B1-B3 and the owner's contribution. Scoring is a sum over teams, so edits are grouped by the teams
    they changed (union-find): each group's points are exact and groups add up to the total. Edits in one group interact and are credited jointly."""
    from .sources.bracketmatrix import score
    br = {n: ({r["key"]: r["line"] for r in L} if isinstance(L, list) else L) for n, L in frozen["brackets"].items()}
    res = {}
    for name, L in br.items():
        if L is None: continue
        s = score(L, official); res[name] = {**s, "max": 6 * len(official), "percentile": None if not matrix_scores else round(100 * sum(x < s["score"] for x in matrix_scores) / len(matrix_scores))}
    B1, B3 = br["B1_model"], br["B3_manual"]
    parent = {}
    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x: parent[x] = parent[parent[x]]; x = parent[x]
        return x
    def union(a, b): parent[find(a)] = find(b)
    edits = frozen["edit_history"]["applied"] if "edit_history" in frozen else frozen["edits"]
    for e in edits:
        for t in e["teams_changed"]: union(t, ("edit", e["id"]))
    groups = {}
    for e in edits:
        g = groups.setdefault(find(("edit", e["id"])), {"edits": [], "teams": set()}); g["edits"].append(e["id"]); g["teams"].update(e["teams_changed"])
    out = []
    for g in groups.values():
        pts = sum(team_points(B3.get(t), official.get(t)) - team_points(B1.get(t), official.get(t)) for t in g["teams"])
        out.append({"edits": g["edits"], "teams": sorted(g["teams"]), "points": pts, "joint": len(g["edits"]) > 1})
    total = res["B3_manual"]["score"] - res["B1_model"]["score"]
    return {"scores": res, "manual_minus_model": total, "edit_groups": out, "groups_sum": sum(g["points"] for g in out)}

# ------------------------------------------------------------------ CLI
def _games_live(season: int) -> list[dict]:
    from .dataset import _d
    from .teams import key
    gs = json.load(open(f"data/output/gamecache/{season}.json"))["rows"]
    for g in gs: g["team_key"], g["opp_key"], g["date_iso"] = key(g["team"]), key(g["opp"]), _d(g["date"])
    return gs

def _shadow(exclude: set[int]) -> ShadowH2H | None:
    """Saved weights are used only if they were trained without every excluded season; otherwise refit."""
    import joblib
    p = "models/shadow_h2h.joblib"
    if os.path.exists(p):
        s = joblib.load(p); ty = set(getattr(s, "train_years", []) or [])
        if ty and not (ty & set(exclude)): return s
    try:
        from .shadow_h2h import history_evidence
        from .history import SELECTION_SUNDAY
        years = [y for y in SELECTION_SUNDAY if y not in exclude]
        s = ShadowH2H().fit(project.training_rows(exclude=exclude), history_evidence(years, SELECTION_SUNDAY.get)); s.train_years = years; return s
    except Exception as e:
        print("Shadow unavailable:", e); return None

def main(argv: list[str]) -> None:
    cmd = argv[0] if argv else "build"; season = int(argv[1]) if len(argv) > 1 else 2027
    if cmd == "build":
        from .sitebuild import load_or_fit
        info = {"collected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        ss, today_ny = selection_sunday(season), datetime.now(ZoneInfo("America/New_York")).date()
        pend = pending_conference_games(ss) if ss and today_ny == ss else False     # read BEFORE the data, so completeness is never overstated
        rows, warn = project.live_rows(season, info=info); games = _games_live(season)
        day = info.get("games_through"); prev = previous(season, info["collected_at"])
        if pend is not False: info["conference_games_pending"] = results_complete(pend, games, ss.isoformat())
        rv = build(rows, season, load_or_fit(season=season), games, day, _shadow({season}), load_edits(season), prev, info)
        rv["model_files"] = model_files()
        rv["warnings"] = warn; print(*write(rv))
    elif cmd == "upload":     # prepared for the daily workflow (docs/44); needs approval and credentials, not wired anywhere yet
        p = argv[2] if len(argv) > 2 else all_reviews(season)[-1][0]
        print(json.dumps(upload(json.load(open(p))), indent=1))
    elif cmd == "freeze": print(json.dumps(freeze(season, kind=argv[2] if len(argv) > 2 else "research"), indent=1))
    elif cmd == "verify":
        v = verify(season, kind=argv[2] if len(argv) > 2 else "research"); print(json.dumps(v, indent=1)); sys.exit(0 if v["ok"] else 1)
    elif cmd == "grade":
        from .sources import bracketmatrix as bm
        from .teams import key
        kind = argv[2] if len(argv) > 2 and argv[2] in KINDS else "research"; rest = [a for a in argv[2:] if a not in KINDS]
        fz = json.load(open(freeze_path(season, freeze_dir(), kind))); m = bm.collect(season)
        off = json.load(open(rest[0])) if rest else m["official"]; off = {key(t): int(s) for t, s in off.items()}
        ms = [int(v) for k, v in m["reported"]["SCORE"].items() if v.isdigit() and k != "MATRIX"]
        print(json.dumps(grade(fz, off, ms), indent=1, default=list))
    elif cmd == "demo":
        from .review_demo import demo
        print(*demo(season if len(argv) > 1 else 2026, argv[2] if len(argv) > 2 else "final"))

if __name__ == "__main__":
    main(sys.argv[1:])
