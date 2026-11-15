# The owner's original spreadsheet formula (V1) against v2.0

Committed before Parts 3-5 were run.

## 1. Reverse-engineering (from docs/01, re-verified 2026-11-15)
`v1/reproduce_v1.py` reproduces every cell of columns O and P, rows 2-79, to within 5e-9.

- **Rank transform:** s(x) = 100·(1 − (x−1)/199)². This is a convex quadratic, so rank 1 → 100, rank 50 → 56, rank 100 → 25, rank 200 → 0. It is **not clamped**: rank 300 → 25, so very bad teams regain credit.
- **Column O:** 0.15·Q1A wins + 0.13·Q1 wins + 0.12·Q2 wins + R(row+8) − 0.5·Q3 losses − 1.5·Q4 losses + 0.06·G + 0.24·s(WAB) + 0.19·s(SOR) + 0.17·s(NET) + 0.10·s(Torvik).
- **R10 (column O):** a relative reference that shifts 8 rows down (row 2 → R10, row 79 → R87). Column R is empty, so it adds 0 to every team today. It's a latent bug: anything typed in R10:R87 would silently change scores. It looks unintended.
- **Column P:** O + 0.03·s(L) + 0.025·s(M) + 0.025·s(N). L-N are blank, which is rank 0 → s = 101, so P = O + 8.08 for every team. P orders teams exactly as O does.
- **Column G ("Q1/2 n/a W"), weight 0.06:** the values (Duke 27, Michigan 15, ...) don't match total wins, Q3+Q4 wins, or a rank (there are repeats). Its meaning is unknown, so it can't be rebuilt for past seasons and is left out (weight 0). Max effect in the sheet: 0.06 × 52 ≈ 3 points.
- **Double counting:** a Q1A win counts in both Q1A and Q1 (0.28 total). Record terms are raw counts, so teams with deep résumés gain on count alone.

## 2. Structure against v2.0
| | V1 | v2.0 |
|---|---|---|
| Weights | Set by hand, never fit to committee seeds | Fit to the committee's 1-68 list (pairwise logistic) |
| Rank shape | Quadratic in rank: steep at the top, flat past 100 | log NET plus z-scored values plus ranks of WAB, SOR and rating |
| Q4 losses | −1.5 each, about 3 times the next-largest record weight | Z-scored count, learned weight |
| Information | Q1A/Q1/Q2 wins, Q3/Q4 losses, WAB, SOR, NET, Torvik (G unknown) | All of V1's except G, plus win %, SOS, road and neutral wins, last-10, best-3, Q1 losses, power flag, champion, and interactions |

V1 has **no information v2.0 lacks** (except the unknown G). The real differences are (a) the shape of the rank transform, (b) a very heavy Q4-loss penalty, and (c) weights from human judgment rather than fit to seven seasons, which means lower variance but also less adaptation. Fixed weights can't overfit the evaluation seasons, so V1 is a clean independent check.

## 3. Rebuilt for all seven seasons
- **Inputs:** our quadrant records (docs/33 audit: they match the official ones) and ranks of as-of NET, our WAB, our SOR, and our rating in Torvik's slot. Torvik refuses GitHub, so it can't be a live input; our rating correlates .95-.99 with KenPom and BPI. All are Selection Sunday-correct. G = 0, R = 0, L-N ignored, since they don't affect order.
- **Selection:** auto-bids, then the top at-large teams by V1 score.
- **Faithful:** s() unclamped. **Fixed (reported):** s() with ranks clamped at 200.
- Nothing is fit, so there's no leakage path.

## 4. V1 alone and the disagreement analysis
- **V1-full:** V1's own field and order.
- **V1-seed:** v2.0's field, ordered by V1.
- **Disagreements:** for every team in v2.0's field, the absolute seed error of v2.0 and of V1-seed. Situations are defined by information available before the bracket (v2.0's predicted line, champion status and conference): predicted lines 1-4, 5-8, 9-12, 13-16; small-conference champions (champion, not power); non-power at-large; power at-large.
- **A situation favors V1** if V1-seed has lower mean absolute seed error than v2.0 on those teams in at least 6 of 7 seasons.

## 5. Hybrid (Test 24), only if Part 4 qualifies a situation
If at least one situation favors V1: v2.0's order is kept, but the teams in every qualifying situation are re-ordered among their own slots by V1 score. Bar: +3 mean, better in at least 5 of 7, no season worse than -5. The control must reproduce 335 326 347 344 329 363 356. If no situation qualifies, no hybrid is run, and that is reported. A plain blend was already tested in docs/06 (75/25: +1.5 against the older base) and isn't repeated.

## Results (2026-11-15)
`research/v1_vs_v2_output.txt`. The control reproduced. V1-full faithful reproduced docs/06's independent figures exactly (309 335 314 317 308 350 348), a consistency check.

| | 2019 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Mean | Vs v2.0 | Exact |
|---|---|---|---|---|---|---|---|---|---|---|
| v2.0 | 335 | 326 | 347 | 344 | 329 | 363 | 356 | 342.9 | | 41.6 |
| V1-full, faithful | 309 | 335 | 314 | 317 | 308 | 350 | 348 | 325.9 | -17.0 (better 1, worse 6) | 36.0 |
| V1-full, rank clamp fixed | 309 | 335 | 318 | 317 | 320 | 354 | 351 | 329.1 | -13.7 | 37.6 |
| V1-seed (v2.0's field) | 315 | 339 | 313 | 319 | 309 | 350 | 348 | 327.6 | -15.3 | 36.0 |

**Disagreements.** Mean absolute seed error, v2.0 against V1, and the seasons V1 was better:
- Predicted lines 1-4: 0.30 against 0.38 (1 of 7).
- **Lines 5-8:** 0.85 against 1.04 (1 of 7).
- Lines 9-12: 0.54 against 0.78 (0 of 7).
- Lines 13-16: 0.25 against 0.43 (1 of 7).
- **Small-conference champions:** 0.40 against 0.63 (1 of 7).
- Non-power at-large: 0.79 against 0.75 (2 of 7).
- Power at-large: 0.50 against 0.69 (0 of 7).

No situation favors V1 in 6 or more seasons, so **Test 24 (hybrid) was not run**, per the rule.

**Findings.**
- V1 holds no information v2.0 lacks. Its distinct choices (quadratic rank shape, heavy Q4 penalty, hand weights) do worse than learned weights in every situation, including lines 5-8 and small-conference champions, where V1 is worse than v2.0.
- **The one exception is 2021,** where V1 beat v2.0 by 9-13 points and 8 exact seeds. 2021 was the COVID season: few non-conference games, and v2.0's worst year. Fixed hand weights didn't inherit the other seasons' patterns, which hurt v2.0 that year. It doesn't repeat.
- The rank-clamp fix helps V1 by +3.2 (2022, 2024-26). The R10 and L-N quirks have no effect on order.
- **Caveat:** docs/06's 2026 run of the owner's real sheet scored 362, against v2.0's 356, but it used his own field and his seeds for 7 teams missing from the sheet, so it carries his judgment. With rebuilt inputs and no manual pieces, V1 scores 348 in 2026. On the real archived metrics (docs/06: 2021 337, 2022 316, 2023 326, 2025 364), V1 still trails v2.0 in 2022 and 2023, so better inputs don't change the conclusion.
