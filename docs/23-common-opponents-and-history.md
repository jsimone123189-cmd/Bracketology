# Common opponents, and recent tournament history

Committed before running. Both are judged separately against v2.0 with the usual bar. Also reported: percentile each season, whether it reaches the 75th in all seven, and exact seeds.

## Test 10: head-to-head plus common opponents (seeding)
The NCAA criteria list results against common opponents next to head-to-head.
- **`common`** for teams i and j: over D-I opponents both played through Selection Sunday (excluding each other), the mean of (i's win share against that opponent minus j's), 0 if none.
- Added as a second pair feature next to docs/22's `h2h`, with the same training, ordering and settings.
- Also reported, not judged: `common` alone, without `h2h`.

## Test 11: recent tournament history (field and seeding)
- **`recent_apps`** = how many of the previous three NCAA tournaments the team was in. The 2020 tournament wasn't held, so 2021 uses 2017, 2018 and 2019. Fields come from official Matrix pages for 2016-2025, all known before the season.
- Added as `z_recent_apps` to both the field and seed models.
- This tests whether the committee treats established programs differently when résumés are equal.
