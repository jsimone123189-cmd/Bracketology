# Head-to-head results in seeding

Committed before running. The NCAA's selection and seeding criteria name head-to-head results, and the committee builds its seed list by comparing small groups of nearby teams. v2.0 scores each team on its own numbers, so it can't use a result between two specific teams.

## Test 9
- **Pair feature `h2h`:** for teams i and j, i's wins over j minus j's wins over i, in D-I games through Selection Sunday (0 if they didn't play). It's added to each ranking pair next to v2.0's feature differences. The flipped pair gets the negative value.
- **Same training otherwise:** pairs within 16 overall positions, the same logistic ranking settings.
- **Ordering:** a pair feature means teams can't be scored one at a time. Each field team's score is its mean predicted chance of ranking above every other field team, then lines are filled in that order.
- **Reference, reported but not judged:** the same mean-chance ordering without `h2h`. It separates the ordering method from head-to-head.
- **Judged:** Test 9 against v2.0 with the usual bar. Also reported: percentile each season, whether it reaches the 75th in all seven, exact seeds, and how many pairs in each held-out field met during the season.

## Result (2026-11-14): didn't pass, but no downside
`research/head_to_head_output.txt`. The control reproduced. The mean-chance ordering without head-to-head matched v2.0 exactly, so any change comes from head-to-head itself.
- Scores: 335 326 347 348 329 363 359. Mean +1.0, better in 2 (2023 +4, 2026 +3), worse in 0. Exact seeds 41.6 to 42.0.
- The head-to-head coefficient was positive (0.41 in the fold without 2019).
- 181-283 pairs of field teams met during each season.

This is the first change in this series that never hurt a season. The effect is small because only a few close pairs actually played each other. It fails the bar, so it isn't in production. It's a sound candidate to shadow-track in 2027 next to v2.0.
