# Working backwards from our own misses, and a three-model ensemble

Committed before running. The owner asked for something that works in every season, "even if you have to work backwards." Working backwards from the real brackets is allowed only inside each fold. The season being scored is never used to find or fit anything. Otherwise any rule would fit all seven seasons by construction and say nothing about 2027.

Usual bar: +3 mean, better in at least 5 of 7, no season worse than -5. Leave-one-season-out over 2019 and 2021-26. The control must reproduce 335 326 347 344 329 363 356. Also reported: the Matrix percentile in each season and whether all seven are at the 75th or better (the owner's standard). Field selection is v2.0's in both tests, so only seeding changes. This is about the 73rd and 74th variants tried on these seasons. Anything that passes goes to 2027 shadow tracking before it can replace v2.0.

## Test 17: residual correction, learned from v2.0's own held-out misses
For each target season h:
1. **Find the misses without seeing h.** For each other season s, fit v2.0 on the remaining five seasons, choose s's field, and rank it. For each correctly selected team, residual = actual overall position (`ov`) minus the predicted position (1-68 in the predicted order).
2. **Learn the pattern.** Fit a gradient-boosted regression of residual on: the SEED features (as raw values), automatic bid, power conference, and the predicted position. Settings fixed now: 100 trees, depth 2, learning rate 0.05, subsample 0.8, at least 10 teams per leaf, seed 0.
3. **Apply to h.** Fit v2.0 on all six other seasons as usual and rank h's field. Corrected position = predicted position + predicted residual. Re-sort and fill the lines.

Judged: full correction. Also reported but not judged: half correction.

## Test 18: ensemble of v2.0 and the two shadow candidates
Head-to-head plus common opponents (docs/23, +1.6) and nonlinear pairs (docs/16) each helped in some seasons and hurt in others, and they work differently. Averaging can cancel each one's mistakes.
- Each of the three scores (v2.0 `rank_score`, the docs/23 Test 10 pair score, the docs/16 M2 score) is z-scored within h's field. The equal-weight mean sets the order. The weights are fixed now and won't be tuned.
- Each component is built exactly as in its own doc, trained on the six other seasons.
