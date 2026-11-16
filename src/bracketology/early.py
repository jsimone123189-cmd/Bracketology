from __future__ import annotations
"""Early-season stabilizer (docs/46, owner decision 2026-11-16). Live boards only; never touches backtests or Selection Sunday.

v2.0 was trained on full Selection Sunday resumes. In November its own metrics come from three to six games, so one road win plus
blowouts of weak teams can put a team on the 1 line (LSU, 2026-11-16: own rating and SOR rank 1; NET 77, BPI 53, T-Rank 69).
Until teams have played FULL_GAMES games, each team's place is blended with the median of the outside predictive ranks that are
already collected (NET, BPI, KenPom and T-Rank columns from Warren Nolan's table):

    weight w = max(0, 1 - median games played / FULL_GAMES)
    blended position = (1 - w) * model position + w * outside median rank

The weight reaches 0 by about mid-January and is exactly 0 on Selection Sunday, so the graded v2.0 bracket is unchanged.
Only the order changes: the season's rank_score values are kept and re-dealt in the blended order, so line gaps and
boundaries keep working. p_in (who is in the field) is not changed. No accuracy improvement is claimed (no out-of-sample test
exists for November boards); this is a documented owner adjustment for how the early boards read."""
import statistics

FULL_GAMES = 20
OUTSIDE = ("r_net", "r_bpi", "r_kp", "r_trk")

def weight(median_games: float) -> float:
    return max(0.0, 1.0 - median_games / FULL_GAMES)

def mark(rows: list[dict]) -> float:
    """Called by project.live_rows only: stores the weight on each live row. Rows without the mark are never changed."""
    w = weight(statistics.median(r["w"] + r["l"] for r in rows)) if rows else 0.0
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
