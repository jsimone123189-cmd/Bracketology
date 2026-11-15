# Different model types on the same inputs

Committed before running. docs/15 found that the consistent nine's line moves away from v2.0 match the committee's direction about 95% of the time. None of ten simple characteristics explained them. On the actual field, their average order gets about 50 exact seeds a season, v2.0 42, and NET, WAB or SOR alone 28-34. They seem to judge résumés against past comparables and against close rivals, not by one weighted sum. v2.0's seed model is one linear weighting. So this round changes the kind of model, not the inputs.

Field selection stays exactly v2.0's. Only the order within the field changes. Inputs are v2.0's seed features. Settings are fixed now with no tuning, and each run is leave-one-season-out with a control that reproduces.

- **M1, comparables:** for each team, find the 10 nearest teams in the other seasons (standardized seed features, Euclidean distance) and take the distance-weighted mean of their committee overall positions (1-68). Rank by it.
- **M2, nonlinear pairwise ranking:** pairs of teams within 16 overall positions, as in v2.0, but fitted with gradient boosting on feature differences (150 trees, depth 3, learning rate 0.05, subsample 0.8, seed 0). Each team scores its mean win chance against the rest of the field.
- **M3, blend:** half v2.0's rank score and half M1's predicted position, each z-scored within the field.

**Judged by:**
- the usual bar: +3 mean, better in 5 of 7, no season worse than -5;
- also reported, the owner's standard: each season's percentile against all Matrix entries, and whether it reaches the 75th percentile (the consistent nine's average) in all seven.

Anything that passes goes to 2027 shadow tracking first and doesn't replace v2.0 without the owner's decision.

## Results (2026-11-14)
`research/model_types_output.txt`. The control reproduced. All three failed:
- **M1, comparables:** mean -19.3, worse in 7 of 7.
- **M2, nonlinear pairs:** mean 0.0. Better only in 2025 (+7) and 2026 (+10), worse in five seasons, worst -10.
- **M3, blend:** mean -12.3.

None came close to the 75th percentile in every season. Percentiles for M2: 9, 7, 36, 13, 8, 93, 24.
