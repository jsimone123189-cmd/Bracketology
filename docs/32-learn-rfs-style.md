# Can free stats reproduce RFS Bracket Science?

Committed before running. The owner asked whether RFS is a computer-generated bracket we can crack. RFS's full brackets for 2019 and 2021-26 are on the Matrix pages. As in docs/21 (dRatings), RFS's lines are used **only as training labels**, never as a live input. This is a change to the owner's no-other-bracketologists rule, made at the owner's request. It is labelled here so it can be reversed.

## Part 1: how reproducible is RFS? (diagnostic)
Given RFS's own 68 teams each season, order them with a model trained on RFS's lines from the other six seasons, fill lines with the season's slot sizes, and compare with RFS's lines. Reported per season: share of RFS's exact lines reproduced.
- **Linear:** v2.0's pairwise logistic model and features, with pairs 1-4 lines apart in RFS's bracket.
- **Nonlinear:** the docs/16 boosted pairwise model on the same pairs.
- **Ceiling:** the linear model fit on all seven seasons, graded on the same seasons.
- **Reference:** v2.0 reproduces the committee's exact line about 61% of the time held out (41.6 of 68).

**Decision rule, fixed now:** RFS counts as cracked (a formula our free stats capture) if either held-out model reproduces at least 85% of RFS's exact lines on average, with no season below 75%.

## Part 2: does RFS's style beat v2.0 on the real seeds? (Test 22)
Seed v2.0's field with the linear RFS-trained model (T22a), and with RFS pairs plus committee pairs at equal weight (T22b), as in docs/21. Usual bar: +3 mean, better in at least 5 of 7, no season worse than -5. The control must reproduce 335 326 347 344 329 363 356.

## Results (2026-11-15)
`research/learn_rfs_output.txt`. All 68 RFS teams were found every season, and the control reproduced.
- **Not cracked.** Free stats reproduce RFS's exact line 68% of the time held out (linear; 56-81% by season), 66% nonlinear. Even fit on all seasons with the answers, the ceiling is 70%. The rule needed 85%, with no season under 75%. About a third of RFS's lines come from something outside our free stats.
- **Test 22a, RFS order:** 327 331 343 337 328 368 352. Mean -2.0, better in 2. Failed.
- **Test 22b, committee plus RFS:** 331 329 347 344 329 359 352. Mean -1.3, better in 1. Failed.
