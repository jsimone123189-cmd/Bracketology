# Bottom of the bracket by NET alone

Committed before running.

## Why
Following the owner's pointer to RFS Bracket Science: over seven seasons, RFS put 84 teams on the exact line where v2.0 missed, and v2.0 had 44 the other way (`research/rfs_vs_v2_output.txt`). About 20 of RFS's 84 are small-conference champions on lines 12-16 where v2.0 is off by one line, usually swapping neighbors (13 vs 14, 15 vs 16). Examples: Vermont, Northeastern, Old Dominion, Georgia State, Bradley and Gardner-Webb in 2019; UCSB, UNCG, Abilene Christian, Eastern Washington, Grand Canyon, Iona and Hartford in 2021.

v2.0's seed formula is trained on the whole field. At the bottom, where teams have few Q1 games, its résumé terms may add noise. The committee's bottom lines may follow NET closely.

## Test 21
- v2.0 as is (field and order).
- Teams in predicted positions 49 through the end of the list are re-ordered by NET rank, best first, among themselves. Ties keep v2.0's order. Lines are refilled in that order.
- Nothing is trained, so there's nothing to overfit.

Bar: +3 mean, better in at least 5 of 7, no season worse than -5. The control must reproduce 335 326 347 344 329 363 356. Also reported (not judged): the same with the cutoff at 45 and at 53, and exact seeds and percentiles.

## Results (2026-11-14)
`research/bottom_net_output.txt`. The control reproduced.
- **Test 21 (cut 49):** 339 331 339 344 326 359 356. Mean -0.9, better in 2, worse in 3, worst -8. Failed.
- Cut 45: -3.0. Cut 53: -0.6.
- NET ordering fixed the 2019 and 2021 low lines (+4, +5) and broke 2022 and 2025 (-8, -4). RFS's edge at the bottom isn't plain NET order.
