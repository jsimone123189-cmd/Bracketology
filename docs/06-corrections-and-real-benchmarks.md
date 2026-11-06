# Corrections and real benchmarks (2026-11-05). Supersedes conclusions in docs/02 and docs/05 where they conflict.

## Same-season scores (real Bracket Matrix rubric, no consensus inputs)
| | 2019 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Mean |
|---|---|---|---|---|---|---|---|---|
| Trained model, fixed metrics (leave-one-season-out) | 331 | 320 | 342 | 337 | 327 | 352 | 363 | 338.9 |
| 75% trained model + 25% V1 formula | 333 | 329 | 334 | 340 | 327 | 360 | 360 | 340.4 |
| V1 formula, rebuilt metrics (no training) | 309 | 335 | 314 | 317 | 308 | 350 | 348 | 325.9 |
| T-Rank (Torvik's bracket, actual Matrix score) | 329 | 339 | 331 | 354 | 344 | 371 | 374 | 348.9 |
| Human median | 345 | 351 | 350 | 360 | 341 | 358 | 373 | 354.0 |
| Best site | 367 | 372 | 376 | 382 | 355 | 376 | 393 | 374.4 |
| Jay (actual) | | | | | | | 370 | |

V1 formula on real archived metrics (official WAB only in 2025; rebuilt WAB otherwise; KenPom rank in Torvik's slot):
2021 337, 2022 316, 2023 326, 2025 364. Trained ensemble on real metrics, same seasons: 324, 313, 348, 364 (3 training seasons each).
2026 sheet: order from the real V1 sheet, using Jay's field, Jay's line sizes and Jay's seeds for the 7 field teams not on
the sheet: 362. Jay: 370. So manual adjustment was worth about 8 points that season, not 76.

## What I got wrong
1. "Formula alone is ~294, your 370 is manual judgment": false. 294 came from my weak rebuilt metrics, not your formula.
2. "Rebuilt WAB validated, Spearman .987": that was across all D-I, which hides errors. Among NET<=90 it was .92 against
   official WAB. Same-team seed-order test on 2026: rebuilt WAB 12 exact of 61, real WAB 28, real V1 score 40.
   Fix: margin cap 40, ridge alpha .5, SOR sigma 7, calibrated only against official metric values, never seeds.
   Result: WAB .92 -> .99, SOR .97 -> .98, V1 formula mean 287 -> 326.
3. "Independent ceiling 330-334": unsupported. T-Rank averages 349 and scored 371 and 374 in the last two seasons.
4. "30-35 points below the human median": mixed season sets. Correct gap now is about 15 (339 vs 354).
5. "SOR/KPI cannot be pulled": Warren Nolan publishes NET, ELO, KPI, SOR, WAB, BPI, POM, T-Rank, RPI in one table
   (robots.txt allows; terms unconfirmed). Past-season pages there are FINAL and must not be used as history.
6. "Line sizes are fixed": 2022 had 5 and 5 on lines 11 and 12; 2024 had 6 on line 10.
7. Reclassifying champions (Bellarmine 2022, Merrimack 2023) were forced into the field. Fixed.
8. Earlier requests sent the owner's email in the User-Agent to barttorvik.com, ncaa-api, bracketmatrix.com without asking. Removed.
9. "Consensus beats ~90% of sites": not in 2024 (342 vs median 341).
10. Top-16 reveal was rejected using consensus error. That reason does not apply to an independent model; retest it.

## Limits
Seven seasons; a few points of difference is noise. Earlier configuration choices were made on these same seasons, so
339-340 is somewhat optimistic. As-of real metrics exist for only 2021, 2022, 2023, 2025 (2023 capture is from the Saturday before).
Team sheet captures after the reveal contain seeds in the team name; the parser strips them.

## Research rounds after the corrections (2026-11-05). Scripts and outputs in research/.
Base for each round is leave-one-season-out over 2019, 2021-2026. Benchmarks: T-Rank 348.9, human median 354.0.
| Change | Mean | Vs its base | Better/worse seasons |
|---|---|---|---|
| Seeds: ranking pairs on the committee's published 1-68 order | 340.9 | +2.0 | 4/1 |
| Seeds: + few-Q1-games, Q1 games, Q1 wins x power, NET x non-power | 342.9 | +2.0 | 4/2 |
| Low-major auto-bid slots ordered by NET | 342.0 | +1.1 | 2/1 |
| Nested choice among round 3 variants (honest estimate) | 342.0 | +1.1 | 3/3 |
No gain: Top-16 reveal (-1.0), regression on 1-68 (-2.6), bubble-only or pairwise field, tiered re-rank (-3.0), separate low-major model (-4.4),
conference tournament wins once combined with the power flag (-0.3), Q1+Q2 count (-1.1).
Adding 2014-18 hurt seeding (-3 to -4), but own rating stood in for NET and a few older team names were unmatched, so that test is not clean.
Points lost per season: model 67, T-Rank 59, median site 54. Largest gaps to median: lines 1-4 (3.9), lines 14-16 (3.1), lines 8-9 (3.0).

## More corrections (2026-11-05)
- 76 teams: I called the Matrix text stale. Wrong: 2027 expands to 76. Model code still assumes 68 (CAP, field size, 68 - champs).
- Brad Evans and Bracket Science are Matrix bracketologists: The Gaming Juice Big Board - Brad Evans (Board, rank 37) and RFS Bracket Science (RFS, rank 23).
  I wrongly matched them to Yahoo pick'em commentary and to Peter Tiernan's CBS column.
- Jay's 2026 moves: 20, not 16. An earlier script misaligned line sizes. Corrected sheet order is about 357, so moves net +13: lines 1-11 net -8, lines 12-16 net +21.
  13 helped, 7 hurt, 16 of 20 moved toward the Matrix average. Owner says the moves came from reading other bracketologists.
- Same seasons, research/experts.py (simple rule: auto-bids + most-listed at-large, mean seed rounded):
  all sites 365 373 372 381 352 378 388 = 372.7; top 25 by prior record 369.3; top 10 364.1; top 5 362.7. Experts picked by past record do worse than the whole crowd.
  It reads final Matrix pages, so a real pre-deadline copy would miss late submissions and score somewhat differently.

## Production V2 (owner chose: stats model, then owner's adjustments, no crowd inputs)
src/bracketology/model.py + project.py reproduce research exactly on 68-team seasons: 335 326 347 344 329 363 356, mean 342.9.
Below T-Rank (348.9) and the median (354.0) before owner adjustments. Field/lines switch to 76 for 2027; line sizes are an assumption and no 76-team season exists to test on.
overrides/{season}.json holds adjustments separately so grade() can score model and adjustments apart. Reclassifying teams for 2027 still need adding to INELIGIBLE_CHAMPS.

## Outside audit round (2026-11-05). research/loss_audit.py, challengers.py, benchmark_losses.py.
Production loses 65.1 points a season: field 11.1, one line off 39.4, two or more off 14.6. Real field given: 352.1. Perfect seeds on its own field: 396.9. Real line sizes add 0.3.
Cutoff audit found no leakage: game logs filter post-cutoff rows, NET files stop before the tournament. 2019 has no through date, but its deep tournament teams show no extra games.
Bar set before running: +3 mean, better in 5+ of 7, no season below -5. Nothing passed. Best: shared resume score in selection +0.6 (one season changed), continuous win and loss quality in seeding +0.7 (better 3, worse 2).
Clearly worse: ridge on seed line (-10 to -14), ordinal by expected line (-7 to -13), ordinal with expected-score assignment (-15 to -20, worse in 7 of 7).
Caveat: production settings were chosen on these same seasons, so small negatives are not evidence against a challenger. Production unchanged.

## Big-miss round (2026-11-05). research/big_misses.py, pattern_tests.py.
Same bar, test list fixed before running. Nothing passed. Best: non-power at-large flag in seeding +1.3 (better 4, worse 2), conference record x power in field +0.7 (better 2, worse 0; 2014-18 field 63.2 vs 62.8 of 68).
Counting the Pac-12 as power through 2024 scored -5.7 (better 1, worse 6), so the five-league flag stays, though the flag was itself chosen on these seasons.
Big misses run both ways with no stable group: every group's mean signed error is within about 0.3 lines except a small non-conference group (n=14). Mountain West teams were too high 5 times in 2023-24, but too low in 2019 and 2022, and San Diego St. was too low in 2024.
About 45 variants have now been tried against this baseline, so a best result near +1.3 is what chance alone could produce. Production unchanged.
