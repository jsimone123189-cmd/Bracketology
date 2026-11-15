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
