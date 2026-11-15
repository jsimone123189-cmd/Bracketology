# Different seeding formulas for different parts of the bracket

Committed before running.

## Why (`research/ceiling_output.txt`)
Fit on all seven seasons and graded on those same seasons, with the answers available, v2.0's linear seed model gets only 44 37 45 43 38 49 47 exact seeds (43.3). That's barely above its held-out 41.6. The consistent nine average about 50 on seasons they haven't seen. So one linear formula over these features can't express the committee's order even in hindsight. It underfits; it isn't overfitting. A deep boosted model memorizes 50-65, which is overfitting and doesn't carry over (docs/16).

The committee works through the seed list in batches. The ESPN mock-selection notes say résumé weighs more for some decisions and predictive metrics for others. A structured middle ground: a separate linear formula for each part of the list.

## Test 20
- Stage 1: v2.0 as is orders the field (v2.0's field).
- Stage 2: the predicted order is split into three fixed bands by position: 1-16, 17-40 and 41-68. Within each band, teams are re-ordered by that band's own pairwise logistic model. Lines are then filled in the new order.
- **Band model training:** same features, C and pair rule as v2.0, but only pairs where both teams' actual positions fall in the band widened by 4 on each side (1-20, 13-44, 37-68). It's trained on the six other seasons.

Bar: +3 mean, better in at least 5 of 7, no season worse than -5. The control must reproduce 335 326 347 344 329 363 356. Also reported: exact seeds, Matrix percentile, and the band models' in-sample exact seeds (fit on all seasons), to check whether the formula is more expressive than v2.0's 43.3.

## Results (2026-11-14)
`research/band_seeding_output.txt`. The control reproduced.
- Band formulas are more expressive: 46.3 exact in-sample, against 43.3 for one formula.
- Held out they failed: 341 330 335 340 325 356 348. Mean -3.6, better in 2, worse in 5, worst -12. The extra flexibility fit noise.
