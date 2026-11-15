# Handoff prompt: beat the top bracketologists

Copy everything below the line into another AI. The code and every test write-up are in the public repo.

---

You're picking up a research problem. **Goal:** make a free, automated NCAA men's basketball bracket projection that consistently scores like the top bracketologists on the Bracket Matrix (bracketmatrix.com). That means the 75th percentile or better in every season tested, not one lucky year.

**Repo (public):** https://github.com/jsimone123189-cmd/Bracketology. Code is in `src/bracketology/`. Experiments are in `research/`, each with an `_output.txt`. Every test has a write-up in `docs/NN-*.md`, with its rules committed before it ran and the results appended after. Read docs/08, docs/11-15 and docs/28-32 first.

## Hard rules from the owner (don't break them)
- $0 a month to run, using only free, legally accessible data that's collected automatically. No paid APIs, no paywall bypassing, no getting around sites that block bots (for example, don't reach Torvik through blocked routes; ESPN's robots.txt blocks AI crawlers).
- No manual entry of statistics. The owner's own documented manual adjustments are allowed.
- No inputs from other bracketologists or the Bracket Matrix consensus at prediction time. Exception, approved by the owner: another bracketologist's past brackets may be used as training labels only (docs/21, docs/32).
- Backtests use no future information. Every feature must exist by the Selection Sunday cutoff.
- No claiming an improvement without out-of-sample evidence. No made-up or stale statistics shown as current.

## How results are judged
- **Seasons:** 2019 and 2021-2026 (2020 had no tournament; NET began in 2018-19). Evaluation is leave-one-season-out: train on six seasons, score the seventh.
- **Scoring (Bracket Matrix):** 3 points for each correct team in the field, plus 3 for the exact seed line or 1 for one line off. The maximum is 408.
- **Baseline v2.0 held-out scores:** 335 326 347 344 329 363 356 (mean 342.9). Matrix percentiles 21, 9, 39, 14, 10, 75, 10. Any new test must reproduce these exactly as its control.
- **Bar to replace v2.0:** +3 mean points, better in at least 5 of 7 seasons, and no season worse than -5. About 83 variants have been tried, so a single pass could be luck. Anything that passes goes to 2027 shadow tracking first.

## What v2.0 is
- **Features**, from game logs (Torvik's free game logs, held locally) plus NET from Wayback captures (as of Saturday night before Selection Sunday): log NET, our own WAB, our own SOR-style metric, our own margin rating, Q1A/Q1/Q2 wins, Q1 losses, Q3/Q4 losses, win %, SOS, road and neutral wins, last-10, best-3 wins, power conference, and auto-bid status. These are z-scored among NET ≤ 120.
- **Selection:** logistic regression plus gradient boosting averaged; auto-bids go in first.
- **Seeding:** a pairwise logistic regression (C=0.1) trained on the committee's published 1-68 overall seed list, using pairs within 16 positions. Lines are filled by S-curve slot sizes.

## Key facts found
- The top group beats v2.0 by about 20 points a season, almost all of it in seeding: about 7 more exact lines (about 49 against 41.6). Selection is about 1.1 wrong teams a season for them against 1.86 for v2.0.
- The 9 consistently good bracketologists (Dom, Bauer, BKS, Sluder, DII, HHD-JT, 801, Elam, T3) correlate .998 with the Matrix consensus. Each sits on the consensus line 80-94% of the time, and when one leaves it, the consensus is right 258 times against 162 (docs/15).
- **In-sample ceiling (docs/30):** fit on all 7 seasons with the answers in hand, v2.0's features with a linear seed formula get only 43.3 exact a season (held out: 41.6). So the committee's order isn't capturable from these features even in hindsight.
- **Free stats reproduce other bracketologists only partly:** dRatings' exact line 55-73% of the time (docs/21), and RFS Bracket Science's 68% held out, with a 70% ceiling in-sample (docs/32).
- The committee moves only 0-4 teams a season off the S-curve for bracketing rules.
- v2.0's misses go both ways at equal rates. No group (power/non-power, at-large/auto) has a consistent direction of error (docs/12). A model trained on its own residuals found no pattern that carries over (docs/28).
- **Lines where v2.0 is weakest:** 5-8 (43% exact against the group's 57%) and small-conference champions (v2.0 0.40 lines of error against the group's 0.19-0.26).

## Tried and failed (mean change vs v2.0; docs number)
- **Player availability** from box scores (hoopR/ESPN archive): -0.9 (10). Torvik rating magnitude: no signal (11).
- **Conference record** in selection: -0.1. Non-conference SOS for non-power teams: -2.1 (12).
- **Auto-bid/champ** in the seed model: +0.1. Random line shifts of any size: always lose (13).
- **Real KPI/SOR/BPI/KenPom ranks:** plain average -8.8 exact (14); learned weights over 4 seasons -2.8 (29).
- **Other model types:** kNN comparables -19.3, nonlinear (boosted) pairwise 0.0 (gains only 2025-26), blend -12.3 (16).
- **Training only on earlier seasons:** -2.6; nonlinear pairs +2.0 (17). RPI: -0.9 (18).
- **Committee's February top-16 reveal** as a lean: -1.3 (19). Bradley-Terry: -2.3 (20).
- **Learning dRatings' order:** -4.1; committee plus dRatings: -1.9 (21).
- **Head-to-head pair feature:** +1.0. Head-to-head plus common opponents: +1.6, better in 3, worse in 1 (22, 23). These are the best found, still under the bar. Recent tournament history: -2.0 (23).
- **2014-18 added with RPI in NET's place:** -3.7 (24). Rest of the team sheet (average NET of wins and losses, NET SOS, NC SOS): -1.1 (25).
- **Nested metric-weight search:** -12.6 alone, -4.3 blended, with weights unstable across folds (26).
- **Committee-stated habits** from ESPN's 2026 mock selection: location-weighted head-to-head +1.0, Q1 loss margin -0.6, double champion -1.7 (27).
- **Residual correction** learned from own held-out misses: -0.6. Ensemble of v2.0, head-to-head plus common opponents, and nonlinear pairs: +0.3, worst -7 (28).
- **Separate seed formulas** for positions 1-16, 17-40 and 41-68: -3.6 (30). Bottom positions 49-68 ordered by NET: -0.9 (31).
- **Learning RFS's order:** -2.0; committee plus RFS: -1.3 (32).
- **Expected-score line assignment** (each team's line probabilities from nested held-out errors, then the bracket with the most expected points under real line capacities, solved with the Hungarian algorithm): moved 0 teams in all 7 seasons. Straight S-curve fill is already optimal, so the whole gap is in the team order, not in turning it into lines (33).
- **Recurring pattern:** what helps 2019/2021 hurts 2022/2025, and the reverse.

## Data audit (docs/33): our inputs match the committee's
- Rebuilt quadrant records match the official NET-sheet records for 93-100% of field teams (mean absolute difference 0.07 games or less).
- Rebuilt SOR, WAB and rating correlate .95-.99 with the real ESPN SOR, WAB, KenPom and BPI.
- NET is the Saturday-night version, which is what the committee sees.

## Owner's 2026 bracket (370 against v2.0's held-out 356), docs/33
- He differed on 23 teams, net +14. **13 of those were on v2.0's low-confidence list (31 teams), worth +10.** The other +4 came from picking Miami (OH) over Auburn.
- He moved non-power at-large teams up and power-conference mid-seeds down. That was v2.0's 2026 bias, but the bias flips direction season to season (right in 4 of 7), so a fixed rule fails.

## Searched and not found
- No free, automatic injury or availability source with past seasons (docs/27).
- RFS Bracket Science (rfsbracketscience.blogspot.com) publishes no method.
- dRatings: its own Bradley-Terry ratings plus RPI plus SOS plus unnamed factors; archived ratings exist only for 2021.

## Open ideas not yet tested
- Ask RFS or dRatings directly how they seed.
- The timing of RFS's final-week brackets (3/11-3/15): does their edge come from conference-tournament results?
- A free source of past injury or availability news.
- The owner's own adjustments on the model's daily low-confidence list. The owner's own 2026 Matrix bracket scored 370, against v2.0's held-out 356.
- 2027 shadow tracking of head-to-head plus common opponents and nonlinear pairs.

## What I need back from you
You may not be able to run the code. If not, give me **one to three specific, untested experiments**, ranked. For each one:
- the hypothesis, and why it should beat the documented limits (in-sample linear ceiling 43 exact; the top bracketologists only 55-73% reproducible from free stats; misses not consistent in direction),
- the exact data, with a free, legal, automatic source that has seasons back to 2019 as of Selection Sunday,
- the exact algorithm, with settings fixed in advance,
- the pass/fail rule.

Don't propose anything in the "tried and failed" list or a reweighting of the same features. If you think the gap can't be closed with free data, say so and point to the specific evidence above.

## How to work
- Write each test's rules into a new `docs/NN-*.md`, commit it, then run.
- The control must reproduce 335 326 347 344 329 363 356.
- Report all seven seasons, the mean change, better/worse counts, the worst season, and Matrix percentiles. Append the results to the doc.
- Run with `PYTHONPATH=src .venv/bin/python research/<script>.py`.
- Don't run `wrangler deploy` by hand, and don't touch the production workflows.
