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

## Results (2026-11-15)
`research/championship_week_output.txt`; exploratory follow-up `research/cw_moves_output.txt`.

### Part 1, the audit: the finding holds, with corrections
- **Timestamps:** every elite entry used at D-7 was dated at or before D-7 (per season: 3/6-3/7, 3/4-3/6, 3/4-3/5, 3/5-3/7, 3/7-3/8). No expert had games v2.0 lacked.
- **Same teams:** on common teams (about 52 at D-7, about 66 at the final), the gap is **+1.3 at D-7 and +7.8 at the final**, growing by +6.5, positive in 5 of 5.
- **Training mismatch:** v2.0 trained on other seasons' D-7 data narrows the D-7 gap to +0.2 (it beats the final-trained version in 2021-22, loses in 2024-25). The near-tie a week out is robust.
- **Correction to docs/36:** the "67% game-information share" is descriptive and mostly isn't game information. Part 2 shows most of v2.0's final-week gain is auto-bid resolution.

### Part 2, decomposition of v2.0's final-week change (2021-26, mean exact seeds)
| Step | Exact seeds | Matrix score |
|---|---|---|
| D-7 | 28.5 | 274.5 |
| + final champions and bid thieves | **+9.3** | **+59.3** |
| + final NET (quadrant and opponent-quality reclassification) | -1.0 | -1.2 |
| + new games' résumé | +5.0 | +11.5 |
| Final | 41.8 | 344.2 |

- **Most of v2.0's championship-week gain is mechanical:** knowing who won the automatic bids.
- **Final NET reclassification slightly hurts.**
- **New games add only about 5 exact seeds.** The elite gain about 22 over the same week. Assuming they get a similar champion effect, they extract roughly **13 exact seeds from the week's games and news, against v2.0's 5**.

### Category 4, the CT-surprise diagnostic: a consistent pattern, the opposite of the hypothesis
Correlation between v2.0's held-out residual and conference-tournament surprise: **positive in 7 of 7 seasons** (+0.32, +0.10, +0.18, +0.21, +0.18, +0.14, +0.09; mean +0.17). The pre-registered "rewards surprise" rule needed negative, so it fails.

The positive sign means **teams that out-performed expectations in their conference tournament were placed worse by the committee than v2.0 predicted, and under-performers better.** v2.0 over-reacts to championship-week results compared with the committee. The elite's deviations from v2.0 lean the same way (positive in 5 of 7).

### Part 3, Test 26: failed
- **Result:** 323 323 339 344 331 348 357. Mean -5.0, better in 2, worse in 4, worst -15 (2025). Exact seeds -2.4, lines 5-8 exact 6.6 against 6.9.
- **Why the signal doesn't carry over:** the correlation is weak (about 3% of rank variance), and a learned linear weight on it doesn't transfer across seasons.

### Exploratory (not pre-registered): direction of championship-week line moves
Teams moved between D-7 and final, counted as toward or away from the committee's seed:
| | Toward | Away | Share toward |
|---|---|---|---|
| v2.0, game-driven moves (champions fixed) | 82 | 59 | **58%** |
| v2.0, all moves | 85 | 54 | 61% |
| Elite brackets, all moves (29 bracket-seasons) | 554 | 162 | **77%** |

Per bracket, the elite make about 19 correct and 5 wrong moves a season. v2.0's game-driven moves are close to a coin flip.

### What this rules out, and what's left
- **Ruled out:**
  - The edge isn't held all season (near-tie at D-7, robust to the audit).
  - It isn't auto-bid resolution (both get that).
  - It isn't a reward for beating tournament expectations (the sign is reversed).
  - A linear CT-surprise feature can't recover it (-5.0).
- **What the evidence points to:** in championship week the committee and the elite **move teams less on conference-tournament results than v2.0's season-long features imply**, and choose which teams to move far more accurately (77% against 58%). The remaining unknown is what informs that choice: committee knowledge about how Sunday finals are handled, injuries, the bubble, and convergence on each other. History can't separate these.
- **Per this doc's rule, no further championship-week variants are run on these seasons.** A natural next model is a "pre-tournament résumé plus champion status" variant, which discounts conference-tournament games. It was suggested by these same seasons, so it can only be validated prospectively (2027 shadow), if the owner approves.
