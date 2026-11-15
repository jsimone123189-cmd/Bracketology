# Championship-week anchoring: audit, movement analysis, one rule

Committed before Parts 1-4 were run. **Status: exploratory.** The hypothesis came from docs/39, which used all seven seasons. Nothing here on 2019 or 2021-26 counts as independent confirmation, even with leave-one-season-out. **The primary validation is 2027 prospective shadow tracking (docs/38).**

## Part 1: audit of docs/39's overreaction sign
- **Definitions (from code):** residual = `ov` − predicted position, where `ov` is the committee's 1-68 position (1 = best). **Positive residual = the committee placed the team worse than v2.0 did.** CT surprise = Σ(win − p) over conference-tournament games, with p from pre-tournament ratings. **Positive = out-performed.** A positive correlation therefore means out-performers were placed worse than v2.0 predicted: overreaction, if it survives the checks below.
- **Sign check:** printed examples of the 3 largest-surprise teams per season, with predicted position, committee position and residual.
- **Champion confound:** the correlation is computed separately for (a) at-large teams only and (b) automatic-bid winners only.
- **Position confound:** the partial Spearman correlation controlling for predicted position (rank-residualized). Residuals are bounded near positions 1 and 68.
- **Selection effect:** only correctly selected teams have residuals. The share of field teams excluded is reported.
- **Survives** if the at-large-only correlation and the partial correlation are each positive in at least 5 of 7 seasons.

## Part 2: the actual movements, D-7 to Selection Sunday (2021-26, seasons with D-7 NET)
v2.0 at D-7 versus final, as in docs/39. Each team whose line changed is classed:
- **Auto-bid effect:** the team's champion status changed between D-7 and final, or it entered or left the field.
- **Résumé change:** everything else.

Each is labeled **beneficial** (moved closer to the committee's seed), **harmful** (farther) or neutral, with exact-seed gained and lost counts.

**Maximum opportunity for any anchoring rule:** résumé-change moves that took a team off its exact line, minus those that put a team onto it. Freezing all résumé-change moves can at best recover this net figure. A perfect selective rule could recover at most the exact seeds lost.

## Part 3: the rule (Anchor-CT), every parameter fixed now
- **Reference:** each team's pre-tournament résumé. Every game-derived feature (quadrant records, WAB, SOR, rating, win %, SOS, road and neutral wins, last-10, best-3) uses only games **before the team's own conference tournament began** (the league's first conference-tournament game date). A league with no tournament games uses Selection Sunday.
- **Kept current:** NET is the final Saturday-night NET, the official sheet number the committee sees. Opponents' quadrant classification uses final NET. Champion status and automatic bids are final.
- **Selection:** unchanged v2.0 (final features). Only seeding is anchored, because selection isn't where the gap is.
- **Seed model:** v2.0's pairwise logistic regression, settings and features unchanged. It's trained on the other seasons' pre-tournament features against the committee's final order, so it learns how the committee maps pre-tournament résumés to seeds.
- **No other parameters, thresholds or exceptions.** The committee's seeds and expert brackets aren't used to choose anything.

## Part 4: exploratory retrospective diagnostic
- Seven seasons against the unchanged v2.0 baseline (335 326 347 344 329 363 356).
- **Reported:** scores, mean difference, exact seeds, lines 5-8 exact, better/worse counts, worst regression, and percentiles.
- The bar (+3, 5 of 7, no worse than -5) is reported **for information only**. Passing wouldn't be independent confirmation, and failing would argue against running it as a shadow.
- **Gap closure:** the change in exact seeds against docs/39's +7.8 common-team final gap.

## Part 5: 2027 shadow
If the rule is technically feasible, it's frozen as a research module (`src/bracketology/shadow_anchor.py`, unused by production) with a unit test, and listed in docs/38 as candidate B2b. Wiring it into the daily snapshot needs the owner's approval. A poor exploratory result (worse than -5 mean) is reported, and then the shadow isn't recommended.
