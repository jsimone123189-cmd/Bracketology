from __future__ import annotations
"""Post-Selection Sunday report. Scores the untouched model and the adjusted bracket from saved snapshots, and gives each adjustment's score impact.
Run: python -m bracketology.report 2027 [official.json] [snapshot folder]. official.json is {team: seed line}; without it the final Bracket Matrix page is used."""
import glob, json, os, sys
from . import fieldformat
from .project import SELECTION_SUNDAY_LIVE
from .sources import bracketmatrix as bm
from .teams import key

def team_points(line: int | None, seed: int | None) -> int:
    if line is None or seed is None: return 0
    return 3 + (3 if line == seed else 1 if abs(line - seed) == 1 else 0)

def bracket_stats(lines: dict[str, int], official: dict[str, int], order: list[str] | None = None) -> dict:
    """lines = {team key: projected line}. order = team keys in projected rank, for pairwise agreement near seed boundaries."""
    s = bm.score(lines, official)
    both = [(lines[k], official[k]) for k in lines if k in official]
    big = [abs(a - b) for a, b in both if abs(a - b) >= 2]
    out = {**s, "wrong_teams": sorted(k for k in lines if k not in official), "missed_teams": sorted(k for k in official if k not in lines), "two_plus_line_misses": len(big),
           "mean_excess_seed_error": round(sum(abs(a - b) - 1 for a, b in both if abs(a - b) > 1) / max(1, len(both)), 3)}
    if order:
        pos = {k: i for i, k in enumerate(order) if k in official}; agree = pairs = 0
        ks = sorted(pos, key=pos.get)
        for i, a in enumerate(ks):
            for b in ks[i + 1:]:
                if abs(official[a] - official[b]) == 1:     # teams either side of a seed boundary
                    pairs += 1; agree += official[a] < official[b]
        out["boundary_pair_agreement"] = round(agree / max(1, pairs), 3)
    return out

def selection_stats(ranked: list[dict], official: dict[str, int], bubble: dict) -> dict:
    """Candidates match the backtest's: NET 100 or better, not champions."""
    cand = [r for r in ranked if r["net"] <= 100 and not r["champ"]]
    brier = sum((r["p_in"] - (r["key"] in official)) ** 2 for r in cand) / max(1, len(cand))
    in_ = bubble.get("last_in", []) + bubble.get("byes", []); out = bubble.get("first_out", []) + bubble.get("next_out", [])
    right = sum(k in official for k in in_) + sum(k not in official for k in out)
    return {"brier": round(brier, 4), "candidates": len(cand), "bubble_right": right, "bubble_total": len(in_) + len(out)}

def adjustment_impact(snapshot: dict, official: dict[str, int]) -> list[dict]:
    """Points each adjustment gained or lost, teams it moved included. Teams changed by more than one entry are charged once."""
    model = {key(r["team"]): r["line"] for r in snapshot["model_bracket"]}; final = {key(r["team"]): r["line"] for r in snapshot["teams"]}
    out, seen = [], set()
    for e in snapshot.get("ledger", []):
        impact = 0
        for t in filter(None, (e["team"], e.get("swap_with"))):
            k = key(t)
            if k not in seen: impact += team_points(final.get(k), official.get(k)) - team_points(model.get(k), official.get(k)); seen.add(k)
        k = key(e["team"])
        out.append({**e, "final_outcome": official.get(k), "score_impact": impact})
    return out

def evaluate(snapshot: dict, official: dict[str, str | int]) -> dict:
    off = {key(t): int(s) for t, s in official.items()}
    model_lines = {key(r["team"]): r["line"] for r in snapshot["model_bracket"]}; order = [key(r["team"]) for r in snapshot["model_bracket"]]
    final_lines = {key(r["team"]): r["line"] for r in snapshot["teams"]}
    final_order = [key(r["team"]) for r in sorted(snapshot["teams"], key=lambda r: r["overall"])]
    return {"snapshot_id": snapshot["snapshot_id"], "generated_at": snapshot["generated_at"], "model_version": snapshot["model"]["version"], "max": fieldformat.max_score(snapshot["season"]),
            "model": bracket_stats(model_lines, off, order), "adjusted": bracket_stats(final_lines, off, final_order), "selection": selection_stats(snapshot["ranked"], off, snapshot["bubble"]),
            "adjustments": adjustment_impact(snapshot, off)}

def load_snapshots(season: int, folder: str) -> list[dict]:
    out = []
    for p in sorted(glob.glob(f"{folder}/{season}_*.json")):
        s = json.load(open(p))
        if s.get("schema", 0) >= 2: out.append(s)
    return out

def final_before(snapshots: list[dict], deadline: str) -> dict:
    """Last snapshot before the bracket came out. Later runs can't count, even if they scored better."""
    done = [s for s in snapshots if s["generated_at"] <= deadline]
    if not done: raise SystemExit(f"No snapshot before {deadline}.")
    return done[-1]

def as_text(r: dict, history: list[dict]) -> str:
    def row(name, b): return f"| {name} | {b['score']} | {b['picked']} | {b['exact']} | {b['within1']} | {b['two_plus_line_misses']} | {b['mean_excess_seed_error']} | {b.get('boundary_pair_agreement')} |"
    t = [f"# Selection Sunday report: {r['snapshot_id']}", f"Model {r['model_version']}. Saved {r['generated_at']}. Maximum {r['max']}.", "",
         "| Bracket | Score | Picked | Exact | Within 1 | 2+ lines off | Excess error | Boundary pairs |", "|---|---|---|---|---|---|---|---|", row("Untouched model", r["model"]), row("With adjustments", r["adjusted"]), "",
         f"Wrong teams (model): {r['model']['wrong_teams']}", f"Missed teams (model): {r['model']['missed_teams']}",
         f"Selection Brier {r['selection']['brier']} over {r['selection']['candidates']} candidates. Bubble calls right: {r['selection']['bubble_right']} of {r['selection']['bubble_total']}.", ""]
    if r["adjustments"]:
        t += ["## Adjustments", "| Team | Model line | Adjusted | Swap | Final seed | Points | Category | Reason |", "|---|---|---|---|---|---|---|---|"]
        t += [f"| {a['team']} | {a['original_line']} | {a['adjusted_line']} | {a.get('swap_with') or ''} | {a['final_outcome']} | {a['score_impact']:+d} | {a['category']} | {a['reason']} |" for a in r["adjustments"]] + [""]
    else: t += ["No adjustments.", ""]
    if history:
        t += ["## Every saved projection", "| Saved | Model | With adjustments |", "|---|---|---|"] + [f"| {h['generated_at']} | {h['model']['score']} | {h['adjusted']['score']} |" for h in history]
    return "\n".join(t) + "\n"

def main(season: int, official_path: str | None = None, folder: str = "data/output/snapshots") -> str:
    official = json.load(open(official_path)) if official_path else bm.collect(season)["official"]
    snaps = load_snapshots(season, folder)
    deadline = f"{SELECTION_SUNDAY_LIVE[season].isoformat()}T22:00:00Z"     # the bracket show starts at 6 p.m. ET
    last = final_before(snaps, deadline)
    text = as_text(evaluate(last, official), [evaluate(s, official) for s in snaps if s["generated_at"] <= deadline])
    os.makedirs("data/output/reports", exist_ok=True); path = f"data/output/reports/{season}.md"; open(path, "w").write(text)
    return path

if __name__ == "__main__":
    print(main(int(sys.argv[1]), *(sys.argv[2:4])))
