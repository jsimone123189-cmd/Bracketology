# The information gap: what elite bracketologists know, timing, and a review process

Committed before Test 25 and Diagnostic R were run.

## 1. What successful bracketologists use that v2.0 doesn't: evidence vs speculation
**Evidence (measured in this repo):**
- **Not the team sheet.** Our rebuilt sheet matches the committee's (docs/33). Adding the real KPI, SOR, BPI and KenPom doesn't help (docs/14, docs/29).
- **Each other.** The nine correlate .998 with the Bracket Matrix consensus and sit on its line 80-94% of the time. When one leaves it, the consensus is right 258 times against 162 (docs/15). Their agreement is mostly shared crowd information, not nine independent formulas.
- **Not a reproducible formula.** Free stats reproduce dRatings' lines 55-73% of the time and RFS's 68% (ceiling 70%) (docs/21, docs/32). Each has about 30% of placements from outside the free stats.
- **The best fully automated Matrix entry trails the median.** T-Rank averages 348.9 against the human median of 354.0 (docs/06). An automated system can beat v2.0 by about 6 but hasn't shown top-quartile results.
- **Expert-picked crowds do worse than the whole crowd** (all sites 372.7, top 5 362.7; docs/06). Averaging many brackets is the strongest signal measured.
- **The owner's 2026 gains:** +10 of +14 came from v2.0's low-confidence list (docs/33). He said the moves came from reading other bracketologists (docs/06).

**Speculation (not testable with history we hold):** inside information from committee contacts, the eye test, injury news (no free archive, docs/27), and knowledge of the current committee's members.

## 2. Why the nine agree, and the timing question
Their agreement is explained by convergence on shared public signals, including each other's brackets, plus the same team sheet. All nine submit after Saturday's games. A possible timing difference: the committee builds its seed list in batches during championship week and treats Sunday's title games with contingency plans and small adjustments. **v2.0 counts Sunday games fully.** 7-9 field teams a season play on Selection Sunday, often top seeds: 2019 Michigan State and Michigan, Tennessee and Auburn, Houston and Cincinnati; 2022-23 Purdue and Houston; 2024 Auburn and Florida; 2026 Michigan and Purdue.

## 3. Three untested experiments, ranked by plausibility
**E1. Saturday-night information cutoff (Test 25, run now).**
- *Hypothesis:* the committee's order reflects games through Saturday. Sunday results move teams little, so counting them adds noise for the teams the model ranks most precisely.
- *Why it could beat the ceiling:* it doesn't add capacity. It removes information the label didn't use, so it reduces noise in the features.
- *Data:* Torvik game logs and NET as already held. NET is already the Saturday capture.
- *Algorithm:* every feature (quadrants, WAB, SOR, rating, last-10, best-3, SOS, road and neutral wins) is recomputed with games through the Saturday before Selection Sunday. Automatic-bid status still uses Sunday's real champions, which is known at the cutoff. Training and test seasons both use the Saturday features. Model, settings and selection are v2.0's.
- *Leakage:* it only removes information, so there's no leakage path.
- *Failure modes:* the effect is small (about 8 teams a season). The committee may in fact react to Sunday, as when 2019 Michigan State won the Big Ten final and got a 2 seed.
- *Pass:* +3 mean, better in at least 5 of 7, no season worse than -5. The control must reproduce 335 326 347 344 329 363 356.

**E2. Uncertainty-based review (Diagnostic R, run now; the real test must be prospective).**
- *Hypothesis:* v2.0's low-confidence list (docs/12) is where informed human review adds value, not just in the owner's 2026 bracket.
- *Historical proxy:* each consistent bracketologist (docs/11's nine) and RFS act as a stand-in "reviewer." For each season, v2.0's line is replaced with the reviewer's line **only for v2.0's low-confidence teams** (confidence under 0.5) that the reviewer also has in the field. Compared with replacing every team. Diagnostic only: expert brackets are never a model input, and this measures where review pays, not a model.
- *Leakage:* confidence uses production's pooled spreads, which saw all seasons. That's a small optimism, stated here.
- *Rule:* the review list counts as **capturing where review pays** if, pooled over the reviewers, low-confidence-only review keeps at least 60% of the full-override gain while touching under half the teams, and the low-only review gains in at least 6 of 7 seasons. If it passes, the recommended path is prospective: a 2027 log of the owner's low-confidence calls, graded against v2.0. One season of his can't be tested historically.

**E3. Final-week anchoring (feasibility only).**
- *Hypothesis:* the committee's batches anchor on information from early in championship week. Features as of about 7 days before would then add signal.
- *Data needed:* as-of NET about 7 days before Selection Sunday for all 7 seasons, from Wayback captures, whose availability is unverified. It's left for a later round once captures are confirmed. Not run.
