# The rest of the official team sheet

Committed before running. The owner's point: the top bracketologists have data the model is missing. Their agreement with each other doesn't prove copying. It could mean they read the same sheet. The NCAA team sheet (Warren Nolan reproduces it daily) prints these for every team, and v2.0 has never had them:
- **avg_net_w:** average NET rank of the teams it beat, D-I wins only.
- **avg_net_l:** average NET rank of the teams it lost to, D-I losses only.
- **net_sos:** average NET rank of all D-I opponents. v2.0's `sos` is built from our own rating, not NET.
- **net_ncsos:** average NET rank of non-conference D-I opponents, for every team. docs/12 tested a log version for non-power teams only.

All use Selection Sunday NET and games through Selection Sunday. All are computable live from NCAA results and the official NET.

## Test 13
- Add all four (z-scored like v2.0's other features) to both the field and seed models, as one block: the parts of the sheet the model doesn't see.
- Leave-one-season-out, control reproduces, usual bar. Also the owner's standard: 75th percentile or better in all seven.
- **Reported only:** each feature's own effect when added alone to the seed model.

## Result (2026-11-14): failed
`research/team_sheet_rest_output.txt`. The control reproduced.
- **Test 13, all four, both models:** 320 330 340 343 336 362 361. Mean -1.1, better in 3, worse in 4, worst -15.
- **Each alone in seeding:** average NET of wins -1.4; average NET of losses -0.4; NET SOS -2.7; non-conference NET SOS -0.7.

Every number on the official team sheet has now been tested in some form:
- NET and quadrant records with game detail,
- overall, conference, non-conference, road and neutral records,
- KPI, SOR, BPI, KenPom and T-Rank (real values, four seasons),
- WAB,
- average NET of wins and losses,
- NET SOS and non-conference SOS.

None adds points to v2.0.

v2.0 already holds the sheet's core, yet the nine differ from v2.0 by about 8 exact seeds a season while agreeing with each other at 0.998. So whatever they share beyond v2.0 isn't on the team sheet. Possibilities: reporting on committee thinking (chair interviews, the NCAA's media mock selection), injury and availability news, precedent memory, or each other's brackets. None of these can be measured from the data held here.
