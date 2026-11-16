# 46. Early-season blend (owner decision, 2026-11-16)

## What the owner found
On the 2026-11-16 board, v2.0 had LSU on the 1-2 line. LSU was 4-0: three home wins by 40+ over weak teams and an 81-80 win at Gonzaga.
The game data were correct (checked game by game). The cause is that v2.0 was trained on full Selection Sunday resumes. With four games,
its own rating and strength-of-record both ranked LSU 1st, while the outside predictive ranks disagreed: NET 77, BPI 53, T-Rank 69,
and KenPom 60 in Warren Nolan's table. KenPom's own site showed 23 through Nov. 15, so Warren Nolan's copy lags. Our page labelled that copy simply "KenPom".

## Rule (fixed before looking at the result)
`src/bracketology/early.py`, live boards only:
- weight `w = max(0, 1 - median games played / 20)`; 0.8 at four games, 0 from 20 games (about mid-January), so **0 on Selection Sunday**;
- blended position = `(1 - w)` × model position + `w` × the median of NET, BPI, KenPom and T-Rank (Warren Nolan's columns, already collected);
- the season's `rank_score` values are re-dealt in the blended order, so lines, gaps and boundaries keep working; `p_in` is unchanged;
- rows that `project.live_rows` didn't mark are never changed. Backtests, the 2027 Selection Sunday B1 and the research snapshot are therefore v2.0 exactly.
- The page warns while the blend is on and says the outside ranks are Warren Nolan's copies that can lag.

## Evidence
- Control backtest after the change: 335 326 347 344 329 363 356 (`research/v1_vs_v2.py`, "control reproduces: True").
- `tests/test_early.py`: unmarked rows unchanged; no-op at 30 games; the outlier moves and the score set is preserved.
- **No accuracy claim.** There is no out-of-sample test for November boards (only Selection Sunday is graded). This is a documented owner adjustment to how the early boards read.
- 2026-11-16 board after the change: LSU overall 30 (8 line); top line Florida, Arizona, Michigan, Duke. LSU would be higher if Warren Nolan's KenPom column matched KenPom (23); the blend uses the collected value, not a hand-entered one.
