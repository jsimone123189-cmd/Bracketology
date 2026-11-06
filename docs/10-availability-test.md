# Player availability test: rules set before any results

Written and committed before the seven-season box scores were fetched. The rules below don't change after results are seen.

## Measure
For each team with Selection Sunday NET 100 or better, using only that team's games on or before Selection Sunday:
- **Last three:** its final 3 games.
- **Baseline:** 10 games evenly spaced among all earlier games, or all of them if fewer.
- **Top five:** the 5 players with the most baseline minutes.
- **`avail_missing`:** for each top-five player, their share of the five's baseline minutes times the share of the last three games they didn't play. Added up, this runs from 0 to 1. A player absent from the box score, or at 0 minutes, didn't play.

Teams outside NET 100 get 0. Scope uses NET only, never field membership, so having data can't reveal who got in. A team missing any last-three box score, or with fewer than 3 baseline games, also gets 0 and counts against coverage.

## The one test
Add `avail_missing` to both the field model and the seed model. Refit leave-one-season-out over 2019 and 2021-26, with all other settings unchanged. The control must reproduce 335 326 347 344 329 363 356 in the same run.

## Pass bar
All three, against v2.0: at least +3 mean points, better in at least 5 of 7 seasons, and no season worse by more than 5 points.

The test is invalid if the control doesn't reproduce, or if coverage is under 90% of in-scope teams in any season. An invalid test isn't a pass.

If it passes, it goes to shadow tracking for 2027 next to v2.0. It doesn't replace v2.0 without the owner's decision. If it fails, the feature stays out, and retesting needs a specifically named flaw in this run.

## First run and restart
Added after the first run and before the rerun. The measure, the one test and the pass bar above are unchanged.

**The first run was invalid.** Using NCAA box scores through the third-party wrapper, coverage was 0% in 2019, 2021 and 2022 (the wrapper returns 502 for those box scores on every try) and 55% in 2023 (empty box scores). The control reproduced. On those partial values, with four seasons effectively all zeros, the scores were 334 326 347 344 329 359 360, mean -0.1 against v2.0, which would not have cleared the bar. That result was seen before this restart and is kept in `research/availability_test_output_invalid_first_run.txt`. It is not the result of this test.

**A flaw in that run:** an empty or incomplete box score in a team's last three games counted players as missing, when the rule says it should count against coverage. Boise State 2024 showed 0.19 and Purdue 2026 showed 0.08 for this reason.

**What changes for the rerun:**
- **Source:** all seven seasons come from one source, the [hoopR-mbb-data](https://github.com/sportsdataverse/hoopR-mbb-data) archive of ESPN box scores, CC BY 4.0, by the hoopR.mbb authors, downloaded as public files. This is research only. The values are built locally and not committed. Any public use would need attribution, and a look at ESPN's terms for the underlying data.
- **Incomplete box scores:** a box score with under 190 team minutes counts as missing. In the last three it fails the team, which gets 0 and counts against coverage. In the baseline that game is dropped.
- **Players** are matched by ID rather than name.

**Source check, done before the rerun without looking at any bracket score:** on teams present in both sources in 2024-26, 289 of 298 values match within 0.005. The largest gaps trace to incomplete NCAA box scores or to source differences. Game counts match within 1 for 2021-26. In 2019 the archive has more games than our NCAA list (Auburn 35 vs 29), and 35 is Auburn's correct count. Coverage is 99-100% in every season.

Live 2027 would still read NCAA box scores, so if this passes, shadow tracking must first confirm those are complete as the games come in.

## Reported, can't change the result
Selection Brier score among non-champions with NET 100 or better, two-or-more-line misses, mean seed error beyond one line, boundary pair agreement, and the same test on seeds alone. Also how far the committee actually placed teams with `avail_missing` of at least 0.2 from v2.0's held-out line. None of these can be promoted on this data.

## Result: failed, the feature stays out
Valid run: the control reproduced 335 326 347 344 329 363 356, and coverage was 99-100% in every season.

| Season | 2019 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Mean |
|---|---|---|---|---|---|---|---|---|
| v2.0 | 335 | 326 | 347 | 344 | 329 | 363 | 356 | 342.9 |
| With `avail_missing` | 335 | 326 | 345 | 344 | 325 | 359 | 360 | 342.0 |
| Change | 0 | 0 | -2 | 0 | -4 | -4 | +4 | -0.9 |

Against the bar: mean -0.9 (needed +3), better in 1 of 7 seasons (needed 5), worst season -4 (limit -5). The first two parts failed.

Reported only: Brier 0.0378 vs 0.0377, two-or-more-line misses unchanged at 4.86 a season, boundary pair agreement 0.849 vs 0.851. Seeds-alone scored the same as the full test. Seven teams at 0.2 or higher were in both fields, and the committee seeded six of them on exactly v2.0's line and the seventh one line worse (mean 0.14). Seven teams is too few to conclude much.

v2.0 is unchanged. A retest needs a specifically named flaw in this run. Output is in `research/availability_test_output.txt`.
