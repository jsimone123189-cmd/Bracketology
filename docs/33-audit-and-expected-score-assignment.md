# Feature audit, ranked hypotheses, and expected-score line assignment

## Part 1: feature audit (diagnostic, run before this doc was written)
Question: is v2.0's low in-sample ceiling (43.3 exact, docs/30) caused by rebuilt team-sheet numbers that differ from what the committee saw?
- **Quadrant records:** ours are rebuilt from game logs plus as-of NET. Compared with the official quadrant columns in the NET captures, for every field team, 2021-26: Q1 wins, Q1 losses, Q2 wins, Q3 losses and Q4 losses differ for 0-7% of teams, with mean absolute difference at most 0.07 games.
- **Rebuilt metrics against the real ones** (Spearman, field teams; Torvik team sheets 2021, 2022, 2023, 2025):

| | 2021 | 2022 | 2023 | 2025 |
|---|---|---|---|---|
| Our SOR vs ESPN SOR | .967 | .974 | .984 | .982 |
| Our rating vs KenPom | .952 | .992 | .988 | .991 |
| Our rating vs BPI | .960 | .976 | .959 | .978 |
| Our WAB vs real WAB | | | | .994 |

- NET is the Saturday-night capture, which is what the committee sees Sunday morning.

**Conclusion:** our team sheet reproduces the committee's numbers closely. Together with docs/14 and docs/29 (the real sheet metrics don't help), the ceiling isn't a data-construction problem.

## Part 2: three untested hypotheses, ranked
1. **Expected-score line assignment (this test).** v2.0 fills lines straight down its predicted order (S-curve). The rubric pays 3 for an exact line and 1 for one line off. With uneven uncertainty by part of the bracket, and skewed errors, the assignment that maximizes expected points can differ from a straight fill. No new features, and the distributions come from nested held-out residuals, so overfitting risk is low. Expected gain: small to moderate. Feasibility: high.
2. **Human review value (direction E).** The owner's 2026 bracket scored 370 against v2.0's 356. A diagnostic splits his gain by v2.0's confidence. If it sits in the low-confidence list, a review process is the scalable fix. Only one season, so it's evidence, not proof.
3. **Committee voting process (direction B).** A mixture of ranking styles, for example résumé-led against predictive-led voters, fit as a latent-class Plackett-Luce model. It's the riskiest for overfitting: about 7 x 68 labels per season would support only 2 classes. Docs/30's band split already showed that added flexibility fits noise.

## Part 3: Test 23, expected-score assignment
v2.0's field and predicted order are unchanged. Only the mapping of order to lines changes.
1. **Error distribution, nested.** For target season h, for each other season s: fit v2.0 on the remaining five, rank s's field, and record residual = actual position minus predicted position for correctly selected teams. Residuals are pooled by predicted band: 1-16, 17-32, 33-48, 49-68. Season h is never used.
2. **Line probabilities.** For each team in h at predicted position p, P(actual position = p + e) uses the band's empirical residuals, each smoothed with a normal kernel of width 1 position. The probability is clipped to 1-68 and converted to line probabilities with h's slot sizes.
3. **Expected points of putting team t on line l:** 3·P(line l) + 1·P(line l±1). Selection points are the same for any assignment, so they're left out.
4. **Assignment:** maximize total expected points subject to each line's exact capacity in h's format (the Hungarian algorithm, teams x slots).

**Judged:** Test 23 against v2.0's straight fill. Also reported, not judged: the same with a normal distribution using the band spreads (as docs/12), and the expected-score gain the model itself predicted against the realized gain.

Bar: +3 mean, better in at least 5 of 7, no season worse than -5. The control must reproduce 335 326 347 344 329 363 356. Also reported: exact seeds and Matrix percentiles. This is variant 83 or so on these seasons, so anything that passes goes to 2027 shadow tracking first.
