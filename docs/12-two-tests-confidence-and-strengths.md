# Two feature tests, team confidence, and the consistent group's strengths

Committed before any of these were run. Each test is judged on its own against v2.0, with the usual bar: at least +3 mean points, better in at least 5 of 7 seasons, and no season worse than -5. Leave-one-season-out over 2019 and 2021-26. The control must reproduce 335 326 347 344 329 363 356. Running several tests on the same seven seasons raises the chance that one passes by luck. So anything that passes goes to shadow tracking in 2027 first, and nothing replaces v2.0 without the owner's decision. Games count only through Selection Sunday, and opponents count only if they are D-I.

## Test 1: selection, conference record
docs/11 found that the committee and all nine consistent bracketologists rejected every one of v2.0's 14 wrong teams, mostly power-conference teams with NET 33-56. Conference record is printed on the committee's team sheets, and v2.0 doesn't use it.
- **`conf_wpct`:** win share in games against same-conference opponents, conference tournament included. A team with no conference games gets its overall win share.
- Added to the **field (selection) model only.**

## Test 2: seeding non-power teams, non-conference schedule
Small-conference champions and non-power at-large teams were v2.0's largest seed misses. Non-conference strength of schedule is on the team sheets, and it is the part of a non-power team's schedule the team chooses.
- **`nc_sos_np`:** the mean of log NET over non-conference opponents for non-power teams, 0 for power-conference teams. This mirrors v2.0's existing `net_nonpower`.
- Added to the **seed model only.**

## Part 3: a confidence for every team
For each held-out season, the model's predicted overall position becomes a probability that its line is exact:
- **Spread:** the actual position is treated as normally distributed around the prediction. The spread comes from held-out residuals on the other six seasons only, using models that never saw the target season (nested). It is estimated separately for predicted positions 1-16, 17-32, 33-48 and 49-68.
- **Exact line:** P(exact) is the probability mass on the predicted line's positions.
- **Confidence** = P(exact) times P(in the field), where P(in the field) is the model's selection probability and is 1 for automatic bids.

Reported:
- Calibration by confidence bin: predicted versus actual exact rate, plus selection Brier.
- For each bin: wrong-team rate, mean seed error, share off by 2+ lines.
- Among confidence under 0.5, the mean signed error (actual seed minus line) for four fixed groups: power at-large, non-power at-large, power automatic bid, non-power automatic bid.

**Predictable error, fixed rule:** a group under 0.5 confidence counts as predictable only if its signed error has the same sign in at least 6 of 7 seasons and averages at least 0.5 lines.

**Adjustment test (Test 3), run only if some group qualifies:**
- For each held-out season, shift that group's predicted overall position by its mean signed error in positions. The shift is estimated from the other six seasons' held-out residuals only. Then reassign lines.
- The same bar applies. If no group qualifies, Test 3 isn't run and that is reported.

## Part 4: the consistent group's strengths
For each of the nine (docs/11), per season entered:
- exact rate on lines 5-8,
- mean absolute seed error for non-power automatic bids and for non-power at-large teams,
- wrong teams.

**Strong in an area** means better than v2.0 in at least 75% of the seasons they entered, with the best average among the nine.

**What they weight:** pooled over seasons, a regression of each bracketologist's line on standardized team-sheet numbers: log NET, WAB, SOR, our rating, Q1 wins, Q1 losses, conference record, non-conference schedule, power conference, automatic bid. The same regression is run for the committee and for v2.0. The output shows where a strong bracketologist weights things more like the committee than v2.0 does, and where the group is weak and v2.0 is not.

This part is descriptive. The group's brackets are never a model input or weight. Any idea it suggests needs its own committed test.
