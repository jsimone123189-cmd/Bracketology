# Bradley-Terry results rating (dRatings' core method)

Committed before running. dRatings (DII, the most consistent model-based Matrix entry) says its ratings are "built around logistic regression, and more specifically, the Bradley-Terry model." v2.0's own rating is margin-based. A Bradley-Terry rating ranks teams by wins and losses against opponent strength, with home edge, and ignores margin.

**Test 7:**
- **`bt`** = Bradley-Terry strength from D-I games through Selection Sunday. Logistic regression on win or loss, with team indicators and a home/away term, an L2 penalty of C = 1.0 (fixed), and no game weighting, because dRatings doesn't publish its weights.
- Added as `z_bt` to both the field and seed models.
- Leave-one-season-out, control reproduces, usual bar. Percentile each season and the 75th-in-all-seven check are reported.
- **Sanity check, reported:** rank correlation of `bt` with NET among NET top 100.

## Result (2026-11-14): failed
`research/bradley_terry_output.txt`. The control reproduced.
- Scores: 329 333 332 330 328 368 364. Mean -2.3, better in 3, worse in 4, worst -15.
- Percentiles: 15, 17, 15, 6, 10, 87, 19.
- The Bradley-Terry rating's rank correlation with NET (top 100) was 0.70-0.83.

Like the nonlinear model, it gained mainly in 2025-26.
