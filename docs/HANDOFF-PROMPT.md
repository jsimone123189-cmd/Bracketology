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
- **Bar to replace v2.0:** +3 mean points, better in at least 5 of 7 seasons, and no season worse than -5. About 92 variants have been tried, so a single pass could be luck. Anything that passes goes to 2027 shadow tracking first.

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

## Owner's original spreadsheet formula (V1), docs/01 and docs/34
- **Formula:** 0.15·Q1A wins + 0.13·Q1 wins + 0.12·Q2 wins − 0.5·Q3 losses − 1.5·Q4 losses + 0.24·s(WAB rank) + 0.19·s(SOR rank) + 0.17·s(NET rank) + 0.10·s(Torvik rank), where s(x) = 100·(1−(x−1)/199)², unclamped. There's also a column G term (0.06 x unknown count) that can't be rebuilt.
- **Quirks:** the R10 reference shifts 8 rows down and points at empty cells (adds 0). Columns L-N are blank, so column P = O + 8.08 and orders teams the same.
- **Scored on all 7 seasons with rebuilt inputs (nothing fit):** 309 335 314 317 308 350 348 = 325.9 (-17.0 vs v2.0, better only in 2021). Clamping ranks at 200: 329.1. V1 ordering v2.0's field: 327.6.
- **Situations:** V1 is worse than v2.0 on lines 1-4, 5-8, 9-12 and 13-16, on small-conference champions, and on power at-large. It's better in at most 2 of 7 seasons on any of them, so no hybrid qualified. V1 holds no information v2.0 lacks.

## Information-gap round (docs/35)
- **Saturday-night cutoff** (every feature recomputed without Selection Sunday's games; 7-9 field teams play that day): 334 332 339 349 330 359 356, -0.1, better in 3, worse in 3. Failed.
- **Review-process diagnostic** (the nine plus RFS as proxy reviewers, substituting their lines into v2.0's bracket; diagnostic only): low-confidence teams only +568 pooled, high-confidence only +493, all teams +1061. That's about +8.4 a season from low-only review, gaining in 6 of 7 seasons. **Expert review pays across the whole bracket. The low-confidence list is about 1.5 times denser in gains, but it isn't a sharp filter.**
- **Evidence summary:** elite agreement comes from shared crowd information (.998 with the consensus). The best automated Matrix entry, T-Rank, averages 348.9, below the human median of 354.0.

## KEY NEW FINDING: the elite edge is built in championship week (docs/36)
- **Method:** Internet Archive snapshots of bracketmatrix.com one week before Selection Sunday (D-7), for 2021, 2022, 2023, 2025 and 2026 (no usable capture for 2019 or 2024). Elite brackets counted only if updated within 3 days. v2.0 was rebuilt as of D-7 with timestamp-correct NET (Wayback ncaa.com), games through D-7, and only the conference champions decided by then. Retrospective only; never a model input.
- **Exact seed lines against the final committee bracket:** v2.0 went from 28.0 a week out to 42.8 at the end (mean), the elite from 28.5 to 50.7.
- **The gap a week out is +0.5 (tied). On Selection Sunday it's +7.9.** It grew in 5 of 5 seasons.
- (The earlier "67% game-information share" was descriptive only; corrected in docs/39.)

## Championship-week deep dive (docs/39)
- **Audit:** the finding holds on common teams (gap +1.3 at D-7, +7.8 at the final, growing in 5 of 5) and with v2.0 trained on D-7 data (D-7 gap +0.2). No expert used games v2.0 lacked.
- **Decomposition of v2.0's D-7 → final change** (2021-26, exact seeds): champions and bid thieves **+9.3**, final-NET quadrant reclassification -1.0, new games' résumé **+5.0**. The elite gain about 22 over the week, so they extract roughly 13 exact seeds from the week's games and news against v2.0's 5.
- **Conference-tournament surprise** (wins minus expected wins, using pre-tournament ratings): its correlation with v2.0's held-out residual is **positive in 7 of 7 seasons** (mean +0.17). Teams that beat tournament expectations get placed worse by the committee than v2.0 predicts. **v2.0 over-reacts to championship-week results.** The elite lean the same way.
- **Test 26** (CT surprise as a learned feature): -5.0, better in 2, worse in 4. Failed. The signal is too weak for a linear weight.
- **Line moves D-7 → final** (exploratory): elite moves go toward the committee's seed **77%** of the time (554/716). v2.0's game-driven moves go toward it 58% (82/141), close to a coin flip.
- **Open:** what tells the elite which teams to move, and how far? A "pre-tournament résumé plus champion status" model (discounting conference-tournament games) was suggested by these same seasons, so it can only be validated prospectively.

## Anchoring round (docs/40, exploratory: hypothesis came from the same seasons)
- **Overreaction audit:** survives. At-large-only correlation positive in 6 of 7, partial correlation controlling for predicted position positive in 7 of 7 (about +0.2). Not driven by champions (4 of 7). No sign error.
- **Actual v2.0 line moves D-7 → final (2021-26):** auto-bid-driven 63 beneficial / 41 harmful (net +71 exact). **Résumé-driven only about 6 a season: 22 beneficial / 13 harmful (net +9 exact).**
- **Maximum opportunity from limiting v2.0's movement:** freezing all résumé moves = -1.5 exact a season. A perfect selective freeze is at most +1.8 exact a season (about 5 points). **Anchoring can't close the roughly 8-exact gap.**
- **Anchor-CT rule** (seed on each team's pre-conference-tournament résumé; final NET, champions and selection kept current; no parameters): 337 327 334 342 316 350 358 = -5.1, better in 3, worse in 4, exact -3.0. Not shadowed.
- **Corrected interpretation:** the elite gain isn't model restraint. It's moves v2.0 never makes: elite championship-week moves are 77% correct (v2.0's own moves 58-61%), but see docs/41: v2.0 moves about as many teams. That's information or judgment outside the free stats.

## Model-inertia diagnosis (docs/41, exploratory)
- **v2.0 isn't inert:** over championship week it changes 42% of field teams' lines, against 48% for the elite consensus. (The earlier "6 vs 24" compared unlike counts; corrected.)
- **63 elite moves v2.0 missed** (elite moved at least 0.5 lines, v2.0 unchanged): A (model inputs changed by 2+ positions' worth, ranking didn't respond) 7, worth **0** exact. **B (inputs barely changed) 42 (67%)**. C (other teams) 8. D (champion status) 6. **Copying the elite's moves on those teams would cost v2.0 17 exact seeds.** Many elite moves fix the elite's own week-out errors toward v2.0's line.
- **Final-gap teams** (elite majority exact, v2.0 not): 69 against 30 reverse. 34 the elite fixed during the week while v2.0 stayed wrong. 13 errors predate the week. 16 are v2.0 moving away from exact.
- **Decision:** no recoverable information for automation shown. Prioritize structured human review. The model remains the base and handles the auto-bid mechanics (+9.3 exact in the week).

## Path B and 2027 plan (docs/37, docs/38)
- **Review page design:** neighbours panel, résumé comparison, head-to-head, metric disagreement, "why this could be wrong" flags, and an edit form that preserves line sizes.
- **Ledger:** reason codes and confidence on every adjustment, graded per entry after the bracket.
- **2027 tracking:** frozen v2.0, the shadow candidate (v2.0 plus head-to-head and common opponents), and model plus owner edits, all frozen at 12:00 ET on Selection Sunday.

## Review tool built (docs/42)
- `src/bracketology/review.py`, `review_page.py`, `shadow_h2h.py`: B1 frozen v2.0, B2 head-to-head/common-opponent shadow, B3 v2.0 plus owner edits.
- **Edits keep line sizes valid by construction.** Logged with time, line/position before and after, reason code, confidence and phase.
- **Freeze:** at noon ET on Selection Sunday, with SHA-256 and no overwrite.
- **Grading:** Matrix scores and percentiles. The owner's contribution is split into exactly additive edit groups (edits sharing teams are credited jointly).
- **2026 demo** (trained without 2026): B1 356, B2 346, B3 with five replayed owner moves 377.
- **Owner decisions:** private interface and ledger; public site shows only the resulting bracket; freeze at 11:30 ET with a verified noon cutoff. Implemented and tested locally: private storage, a leakage guard, a cutoff-checked idempotent freeze, an independent verify, and recovery. Blocked on approval: private automation host (free private repo plus Cloudflare cron), public-site changes, publishing lines only.

## Pre-approval check (2026-11-15)
- **Live 2027 build works locally:** `python -m bracketology.review build 2027` → `private/review/2027_<time>.html`. It produced a 76-team field, with B1, B2 and B3 on one cutoff and the same field. Early season (median 3 games) gives rough seeds; the shadow is especially unstable this early.
- **How saving works:** edit on the page → Edit log → Copy JSON → paste into `private/reviews/2027.json`. Later that file lives in the private repo, editable on github.com from a phone. The next build applies it. No server, $0.
- **The 377 replay is not the owner's submission.** The five replayed moves are in his submitted 2026 bracket, but their reason codes, confidence and timestamps were invented for the demo. They were also picked with hindsight (all five scored). His real 23 changes from v2.0 netted +14 (370 vs 356). The replay and his bracket differ on 16 teams, net +7 to the replay.
- **Schedule:** Selection Sunday is March 14, 2027, and daylight saving starts at 2 a.m. that day. The cutoff is computed as noon America/New_York with zoneinfo, which comes to 16:00 UTC. The freeze runs at 15:30 UTC with a retry at 15:45; verification at 16:05 and 16:30. Cloudflare crons are UTC-only, so they must be updated each year. The freeze rejects data collected after noon New York time regardless of when it runs.
- **Field size:** configurable through `fieldformat.format_for` (68 through 2026, 76 from 2027). The scoring rubric has no team count; the maximum is size × 6. Leftover hard-coded 68s exist only in unused research modules (`backtest.py`, `picker.py`).
- **Proposed automation (not built):** a free private GitHub repo that runs build, freeze and verify. Token A (private repo Actions) is stored as a Cloudflare Worker secret; token B (public repo Contents) is used only to push a lines-only public bracket. Exposure risks: making the repo public later, or the public site's "Edited (model N)" tags plus the public model bracket revealing edits. That needs a site change.
- **Owner approval needed for:** the private repo, both tokens, the Cloudflare crons and dispatch, the public site/snapshot change, and whether to keep the noon freeze (most Sunday conference finals are played after noon).

## 2027 workflow finalized (2026-11-15, docs/43)
- **2026 baseline:** the owner's genuine 2026 submission scored 370 vs v2.0's 356. The 377 demo replay is not evidence.
- **Two immutable Selection Sunday snapshots (built, tested, 53 tests pass):**
  - **research:** noon America/New_York, B1/B2/B3, graded under docs/38;
  - **final competitive:** newest review taken after every Sunday conference final is over (scoreboard read before collection and cross-checked against the games used), before `FINAL_DEADLINE_ET`.
  - The final deadline stays empty, and the freeze refuses, until the 2027 show time and the Matrix's final collection time are confirmed.
- **2025 and 2026 Sunday finals:** five each, the last tipping at 3:30 p.m. ET (ending about 5:30 p.m.), against a 6 p.m. reveal. The 2027 schedules aren't published.
- **Recommended private editing:** a Cloudflare Access (one-time PIN, owner's email only) + Worker + D1 page with a Save button and server timestamps, preferred over a private GitHub repo.
  - **Checked:** Zero Trust Free is $0 for up to 50 users, but signup asks for payment details. Workers Free allows 5 crons per account and 10 ms CPU. D1 Free allows 100k writes a day. Private GitHub Pages needs an organization.
- **Public site leaks to remove (approval needed):** `model_line`, `override_reason` and `p_in` per team, the review list, and `model_bracket`/ledger on the public snapshots branch.
- **Status:** awaiting owner approvals A-E in docs/43. No tokens, deploys or cron changes made.

## Private review interface built locally (2026-11-15, docs/44)
- **`review-worker/`:** a Cloudflare Worker with D1, tested with `wrangler dev` and a local database. Not deployed, no credentials, Access not configured.
- **Login:** Access token checked on every request (signature, audience, issuer, expiry, owner email). Fails closed. A service token is accepted only for upload and published-lines.
- **Storage:** edits, reviews and snapshots are append-only at the database level. Edits get server timestamps.
- **Both snapshots** are built in the Worker. The exported research snapshot passes the Python verifier.
- **Engine:** the JS edit engine is identical to Python on 400 random sequences.
- **Phone page:** board → team sheet → line buttons, reason, confidence → Preview → Save; history with undo and backup download.
- **Tests:** Worker 18 pass. Python 55 on master, 59 on branch `public-privacy`.
- **Free-plan CPU:** freeze 5-6 ms in Node (10 ms limit), after storing a 20 KB core per review.
- **Public privacy (branch, not merged):** removes `model_line`, `override_reason`, `p_in`, the review list, model bracket, ranking, overrides and ledger. The published bracket arrives as lines only from the Worker. In model-only mode the page is unchanged.
- **Bug fixed:** a failed "add" with a bad line removed a team without restoring it.
- **Awaiting owner approvals 1, A-G in docs/44.** No model experiments.

## Pre-deployment hardening (2026-11-15, docs/45)
- **Backups:**
  - an append-only second D1 database, filled daily by cron, after each freeze and when the page opens with a stale backup; each run cross-checks counts, an edit-log hash and snapshot hashes;
  - an off-site bundle download with a staleness reminder;
  - D1 Time Travel, 7 days.
- **Restore** (`scripts/restore.mjs`, handles D1's 100 KB statement limit): tested from the backup database and from the bundle into fresh databases. Edits, timestamps, undo, B3, publications and both snapshot hashes are identical, and the snapshots verify.
- **CPU:** engine about 3× faster (parity kept), freeze replayed in chunks of 150 edits. At 500 edits every request measures 7 ms or less in Node. Fallback ladder: smaller chunks → B3 checkpoint → manual Python freeze. No paid plan.
- **Incomplete final:** a freeze waits while any conference final is in progress and is taken incomplete only in the last 10 minutes. The review page shows a red banner, the public page a label, and the stage-3 workflow sends an email alert.
- **Access:** route matrix tested. The service token reaches only upload and published lines. New Publish step: drafts never leave the Worker.
- **Staged plan:** 1 Access+Worker+D1, 2 phone acceptance, 3 daily upload + merge branch, 4 Selection Sunday timer + rehearsal. Inactive drafts are in `review-worker/deploy/`. The stage-4 timer is simulated in tests.
- **Tests:** Worker 29. Python 55 on master, 60 on the branch. Nothing deployed.

## Stage 1 started (2026-11-15)
- **Owner approved Stage 1 only:** the private Access + Worker + D1 review interface.
- **Research freeze:** moved to 12:01 p.m. America/New_York, strict noon cutoff for data and edits; refused earlier (Worker and Python, tested). Final snapshot unchanged.
- **Dashboard setup done by the owner (2026-11-15):**
  - the account is on Workers Paid ($5/month, already paid for other projects), and Zero Trust "Teams Free Base" already existed; bracketology adds $0;
  - Access: team domain `shiny-shadow-97c9.cloudflareaccess.com`; One-time PIN added; app "JBP Review" on `review.jaysbracketplays.com` with policy "Owner only" (Allow, owner's email, 24 h); the existing "Running Analytics" app is untouched;
  - D1 `jbp_private` and `jbp_backup` created (ids in `review-worker/wrangler.jsonc`);
  - a dedicated token "JBP review deploy" (Edit Cloudflare Workers template + D1 Write, zone jaysbracketplays.com, 1 year), rolled once after being pasted in chat; the site's `CLOUDFLARE_API_TOKEN` is untouched;
  - GitHub secrets `REVIEW_CF_API_TOKEN`, `REVIEW_ACCESS_TEAM_DOMAIN`, `REVIEW_ACCESS_AUD`, `REVIEW_OWNER_EMAIL`.
- **Deploy prepared and approved:** `.github/workflows/review-deploy.yml` (manual only) applies both migrations, deploys with `--secrets-file` so code and secrets arrive in one upload, then checks an anonymous request is refused (retries up to 10 min for the certificate). Dry run, 29 Worker tests and 56 Python tests pass. The owner starts it with Run workflow.
- **Stage 1 deployed (2026-11-16 01:08 UTC, run #1 success):** the owner logged in on his phone with the email code and saw the empty "Review 2027" page. Anonymous requests to `/`, `/api/state`, `/api/export` and `/api/machine/published` all get a 302 to the Access login. The public site is unchanged.
- **Not done:** daily upload, `public-privacy` merge, Selection Sunday timers, stages 2-4. Next is stage 2 (service token, one upload, phone checklist, CPU from logs), awaiting approval.

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
