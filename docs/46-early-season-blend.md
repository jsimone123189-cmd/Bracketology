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

## Update, same day (owner decision): heavy all season, no fade
The owner: "Those other ranks are the number 1 thing that matters... don't wait for 20 games. Rely heavily on that."
- Weight is now a constant **0.8 on every live board before Selection Sunday**, and **0 on Selection Sunday** (`early.weight(today, selection_sunday)`).
- Why not on Selection Sunday too: that was already tested. Real KPI/SOR/BPI/KenPom ranks at Selection Sunday scored worse than v2.0 (plain average −8.8, learned weights −2.8 over four seasons), and by then the model's own metrics correlate .95-.99 with them. The graded B1 and the research snapshot therefore stay v2.0, and the control still reproduces.
- **KenPom source:** kenpom.com and masseyratings.com both refuse automated clients (403 / Cloudflare challenge), and the project doesn't get around blocks. ESPN's own BPI feed (LSU 59th, updated Nov 14) agrees with Warren Nolan's BPI (53), so Warren Nolan's columns are about a day behind rather than wrong; KenPom's 23 already included LSU's Nov 14 win at Gonzaga. Candidate for a fresher official copy: the NCAA team sheets, which list KenPom, BPI, T-Rank, KPI, SOR and WAB once NET is published (usually early December). Not built yet.
