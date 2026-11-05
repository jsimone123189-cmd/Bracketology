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
