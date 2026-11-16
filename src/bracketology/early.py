from __future__ import annotations
"""Outside-rank blend (docs/46; owner decisions 2026-11-16). Live boards only; never touches backtests or Selection Sunday.

v2.0 was trained on full Selection Sunday resumes. In November its own metrics come from three to six games, so one road win plus
blowouts of weak teams put LSU on the 1 line (own rating and SOR rank 1; NET 77, BPI 53, T-Rank 69). The owner's direction: the
outside ranks matter most, so rely on them heavily and don't wait for games to accumulate. Every live board before Selection
Sunday blends each team's place with the median of the outside predictive ranks already collected (NET, BPI, KenPom and T-Rank
columns from Warren Nolan's table):

    blended position = (1 - WEIGHT) * model position + WEIGHT * outside median rank,   WEIGHT = 0.8

On Selection Sunday the weight is 0, so the graded v2.0 bracket (B1, the research snapshot) is unchanged. Evidence for keeping
it there: at Selection Sunday, real KPI/SOR/BPI/KenPom ranks scored worse than v2.0 (plain average -8.8, learned weights -2.8,
four seasons; HANDOFF "tried and failed"), and by then our own rebuilt metrics correlate .95-.99 with them.
Only the order changes: the season's rank_score values are re-dealt in the blended order, so lines, gaps and boundaries keep
working. p_in (who is in the field) is unchanged. No accuracy improvement is claimed for in-season boards (none are graded)."""
import statistics
from datetime import date

WEIGHT = 0.8
OUTSIDE = ("r_net", "r_bpi", "r_kp", "r_trk")

def weight(today: date, selection_sunday: date | None) -> float:
    """WEIGHT on every live day before Selection Sunday; 0 on Selection Sunday and after (and if the date isn't configured)."""
    return WEIGHT if selection_sunday and today < selection_sunday else 0.0

def mark(rows: list[dict], today: date, selection_sunday: date | None) -> float:
    """Called by project.live_rows only: stores the weight on each live row. Rows without the mark are never changed."""
    w = weight(today, selection_sunday) if rows else 0.0
    for r in rows: r["early_w"] = w
    return w

def stabilize(rows: list[dict]) -> list[dict]:
    """After model.score(rows). No-op unless the rows were marked live with a positive weight."""
    w = rows[0].get("early_w", 0.0) if rows else 0.0
    if not w: return rows
    by_model = sorted(rows, key=lambda r: -r["rank_score"]); scores = [r["rank_score"] for r in by_model]
    for i, r in enumerate(by_model):
        r["model_rank_score"], r["model_pos"] = r["rank_score"], i + 1
        out = [r[c] for c in OUTSIDE if isinstance(r.get(c), (int, float)) and r[c] > 0]
        r["outside_rank"] = statistics.median(out) if out else None
        r["blend_pos"] = (1 - w) * (i + 1) + w * (r["outside_rank"] if out else i + 1)
    for s, r in zip(scores, sorted(by_model, key=lambda r: (r["blend_pos"], r["model_pos"]))): r["rank_score"] = s
    return rows
