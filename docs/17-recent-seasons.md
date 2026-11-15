# Do recent seasons predict better? (committee change in 2024-25)

Committed before running. The 2024-25 team sheets added WAB and T-Rank. docs/16's nonlinear model gained only in 2025 and 2026, which hints the committee's habits may have shifted. Leave-one-season-out lets later seasons train earlier ones, which can hide a shift. So this test uses the honest 2027 setting: **train only on earlier seasons.** It's scored on 2022-26, with 2019 and 2021 as the first training seasons.

**Control:** v2.0's method, trained on earlier seasons only, all equal weight.

**R1, recency weighting:** same method, with each training season weighted 0.5^((target - season - 1)/2). That gives a half-life of two seasons: the most recent season counts 1, two back counts about 0.71, four back 0.5. The weight applies to the field model rows and to every ranking pair.

**R2, nonlinear pairs:** docs/16's M2, trained on earlier seasons only, equal weights.

**R3:** R2 with R1's weights.

**Bar for five seasons, fixed now:** +3 mean against the control, better in at least 4 of 5, no season worse than -5. Also reported: percentile against all Matrix entries each season. Settings above are final, with no tuning.
