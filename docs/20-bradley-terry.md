# Bradley-Terry results rating (dRatings' core method)

Committed before running. dRatings (DII, the most consistent model-based Matrix entry) says its ratings are "built around logistic regression, and more specifically, the Bradley-Terry model." v2.0's own rating is margin-based. A Bradley-Terry rating ranks teams by wins and losses against opponent strength, with home edge, and ignores margin.

**Test 7:**
- **`bt`** = Bradley-Terry strength from D-I games through Selection Sunday. Logistic regression on win or loss, with team indicators and a home/away term, an L2 penalty of C = 1.0 (fixed), and no game weighting, because dRatings doesn't publish its weights.
- Added as `z_bt` to both the field and seed models.
- Leave-one-season-out, control reproduces, usual bar. Percentile each season and the 75th-in-all-seven check are reported.
- **Sanity check, reported:** rank correlation of `bt` with NET among NET top 100.
