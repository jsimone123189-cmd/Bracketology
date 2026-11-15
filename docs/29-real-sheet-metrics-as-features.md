# The real team-sheet metrics, learned instead of averaged

Committed before running. The owner's point: this is metric-based, and the top bracketologists read metrics v2.0 doesn't have. RFS Bracket Science (Matrix entry RFS, rfsbracketscience.blogspot.com) beat v2.0's held-out score in 6 of 7 seasons: 349 362 342 363 349 368 380 against 335 326 347 344 329 363 356. Its blog publishes no method, but its sidebar links exactly the committee's sheet metrics: KenPom, Sagarin, ESPN BPI and SOR, KPI and NET.

docs/14 only tested a plain average of those ranks, which did badly. That doesn't show whether the model could learn to use them. This test lets the seed model learn their weights.

## Data
Torvik's team-sheet captures, held locally: 2021, 2022, 2023 (Saturday before Selection Sunday) and 2025. Ranks used: KPI, SOR, BPI, KenPom, the four present in all four seasons. A team missing from a sheet gets rank 365. Live, Warren Nolan publishes the same ranks daily, so this could run in production.

## Test 19
Leave-one-season-out over the four seasons only. Each model trains on the other three.
- **Control:** v2.0 unchanged, trained on the same three seasons.
- **Test 19 (judged):** v2.0 with log rank of KPI, SOR, BPI and KenPom added to the **seed** model. Selection is unchanged.
- **Reported, not judged:** the same four added to selection as well.

**Bar, scaled to four seasons, fixed now:** +3 mean, better in at least 3 of 4, no season worse than -5. Also reported: exact seeds and Matrix percentile.

If it passes, it can't meet the seven-season bar on four seasons. It goes to 2027 shadow tracking from Warren Nolan's daily columns, and I'll look for as-of copies of the 2019, 2024 and 2026 ranks to extend the test.

## Results (2026-11-14)
`research/sheet_features_output.txt`. All 68 field teams were found on every sheet.

| Variant | 2021 2022 2023 2025 | Mean change | Better / worse | Worst |
|---|---|---|---|---|
| Control (v2.0 on three seasons) | 321 338 340 357 | | | |
| Test 19, seed model | 325 328 336 356 | -2.8 | 1 / 3 | -10 |
| Seed + selection (reported) | 325 328 336 362 | -1.2 | 2 / 2 | -10 |

Failed. Learned weights on the real KPI, SOR, BPI and KenPom ranks don't help either. The missing piece isn't one of the committee's sheet metrics.
