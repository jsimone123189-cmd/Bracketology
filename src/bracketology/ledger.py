from __future__ import annotations
"""Manual-adjustment rules. Entries live in overrides/{season}.json, one per team:
  {"Team A": {"line": 5, "swap_with": "Team B", "at": "2027-03-14T19:00:00Z", "category": "availability", "reason": "...", "evidence": "..."},
   "Team C": {"out": true, "at": "...", "category": "factual_correction", "reason": "...", "evidence": "..."}}
Allowed categories are verified availability, factual corrections and unusual circumstances. Evidence can't come from other bracketologists or the Matrix.
An entry missing any of this isn't applied. Each snapshot adds the original line and model version, so its public copy shows what was decided before the bracket came out."""
from datetime import datetime, timezone

CATEGORIES = {"availability", "factual_correction", "unusual_circumstance"}
REQUIRED = ("at", "category", "reason", "evidence")

def _time(s: str) -> datetime | None:
    try:
        t = datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ"); return t.replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None

def problems(entry: dict, now: datetime) -> list[str]:
    bad = [f"missing {f}" for f in REQUIRED if not entry.get(f)]
    if entry.get("category") and entry["category"] not in CATEGORIES: bad.append(f"category must be one of {sorted(CATEGORIES)}")
    if entry.get("at"):
        t = _time(entry["at"])
        if t is None: bad.append("at must look like 2027-03-14T19:00:00Z")
        elif t > now: bad.append("at is in the future")
    if not entry.get("out") and not isinstance(entry.get("line"), int): bad.append("needs a line or out")
    return bad

def validate(overrides: dict, now: datetime | None = None) -> tuple[dict, list[str]]:
    """Returns the entries that may be applied, and one message for each that may not."""
    now = now or datetime.now(timezone.utc); ok, rejected = {}, []
    for team, entry in overrides.items():
        bad = problems(entry, now)
        if bad: rejected.append(f"Adjustment for {team} not applied: {'; '.join(bad)}.")
        else: ok[team] = entry
    return ok, rejected

def records(applied: dict, untouched: list[dict], final: list[dict], key, model_version: str, snapshot_id: str | None = None) -> list[dict]:
    """One line per entry, in the plan's ledger shape. final_outcome and score_impact are filled in by report.py after the bracket is out."""
    before = {key(r["team"]): r["line"] for r in untouched}; after = {key(r["team"]): r["line"] for r in final}
    out = []
    for team, e in applied.items():
        k = key(team); swap = e.get("swap_with")
        row = {"team": team, "original_line": before.get(k), "adjusted_line": after.get(k), "swap_with": swap, "at": e["at"], "category": e["category"], "reason": e["reason"],
               "evidence": e["evidence"], "model_version": model_version, "snapshot_id": snapshot_id}
        if swap: row["swap_original_line"], row["swap_adjusted_line"] = before.get(key(swap)), after.get(key(swap))
        out.append(row)
    return out
