# Championship week: audit of docs/36, decomposition, and a surprise-based test

Committed before any of Parts 1-4 were run.

## Part 1: audit of docs/36
Known issues, stated before checking:
- **Timestamps.** Elite entries count at D-7 if their own column date is within 3 days before the snapshot (D-10 to D-7). v2.0 uses every game through D-7 and NET through D-9 to D-7. **No expert had games v2.0 lacked:** entry dates are at or before D-7, and v2.0 includes D-7. The reverse is true, so docs/36's D-7 gap is biased toward v2.0. Checked: the minimum and maximum entry dates per season are printed.
- **Different team sets.** docs/36 scored each bracket on the actual-field teams it included. At D-7, the brackets project different auto-bids. **Re-scored here on common teams:** actual-field teams that both v2.0 and that expert include, averaged over experts.
- **Training mismatch.** v2.0 at D-7 was trained on the other seasons' **final** features. That could depress its D-7 accuracy and inflate its final-week gain. **Re-run here** with v2.0 at D-7 trained on the other seasons' **D-7** features (seasons with D-7 NET: 2021-26) and final labels.
- **Scoring:** D-7 brackets were scored against the final committee bracket (verified in code: `off` is the final seeds).
- **The "67% game-information share" is descriptive, not causal.** It compares two improvements without holding anything fixed. It's corrected in Part 2 by a counterfactual decomposition.

## Part 2: decomposing v2.0's final-week change (seasons with D-7 NET: 2021-2026)
v2.0 is moved from its D-7 state to its final state one input at a time, in this fixed order. Exact seeds and Matrix score are reported after each step:
1. **Champions and bid thieves:** final champions replace D-7's (decided plus projected). Features stay at D-7.
2. **Opponent-quality and quadrant reclassification:** the final NET replaces D-7's, with games still through D-7. Quadrants and NET are recomputed.
3. **New games' résumé:** all features recomputed with games through Selection Sunday. This is the final v2.0 state.
4. **Unexplained by v2.0:** the elite's D-7 → final gain minus v2.0's, on common teams (docs/36 seasons).

Order matters, which is stated as a limitation.

**Category 4, a tournament-performance effect (diagnostic).** For every team, conference-tournament surprise:
- **CT surprise** = Σ over its conference-tournament games of (win − p). p = Φ((r_team − r_opp + loc·hca)/11) uses our margin rating fit on games **before that conference's tournament began** (sigma 11 = metrics.SIGMA, the WAB spread).
- **Rule:** the committee rewards CT surprise beyond what v2.0's résumé captures if the Spearman correlation between v2.0's held-out final residual (actual position minus predicted, positive = placed worse) and CT surprise is negative in at least 6 of 7 seasons, with a mean of -0.10 or lower. The same correlation with the elite's deviation from v2.0 (docs/36 seasons) is reported.

**Why this is a different mechanism from what failed:**
- last-10 is raw recent win share;
- docs/06 counted conference-tournament wins;
- docs/15 checked group deviations, not committee residuals.

CT surprise measures results **relative to what the ratings expected before the tournament**. It's the "new evidence" that changes a résumé, not the count of wins.

## Part 3: Test 26, CT surprise as committee evidence
- Add `ct_surprise` to both the selection and seed feature lists. It's z-scored among NET ≤ 120 like the BASE features. v2.0's settings are otherwise unchanged.
- Leave-one-season-out over 2019 and 2021-26. The feature uses only games through Selection Sunday and ratings from before each conference tournament, so it's timestamp-correct.
- **Judged:** both models. **Reported:** seed model only.
- **Bar:** +3 mean, better in at least 5 of 7, no season worse than -5. The control must reproduce 335 326 347 344 329 363 356.
- **Also reported:** exact seeds, lines 5-8 exact, and percentiles. For "closing the gap": the change in exact seeds against docs/36's final gap of +7.9.
- If it passes, it becomes the B2 shadow candidate in docs/38 (replacing head-to-head plus common opponents), pending owner approval. If it fails, no further championship-week variants are run on these seasons. What it rules out is reported.
