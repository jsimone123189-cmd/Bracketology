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

## Reported, can't change the result
Selection Brier score among non-champions with NET 100 or better, two-or-more-line misses, mean seed error beyond one line, boundary pair agreement, and the same test on seeds alone. Also how far the committee actually placed teams with `avail_missing` of at least 0.2 from v2.0's held-out line. None of these can be promoted on this data.
