# The review tool (built; production not yet wired)

Implements docs/37-38. v2.0 is unchanged. Nothing here runs in the daily workflow until the owner approves the steps at the end.

## What was reused
- **`project.live_rows`, `model`, `project.confidence`:** live data, the frozen v2.0, confidence.
- **`fieldformat`:** 68/76-team line sizes.
- **`report.team_points` and `bracketmatrix.score`:** the Bracket Matrix rubric.
- **The head-to-head/common-opponent method from `research/common_opponents.py`:** moved, unchanged, into `shadow_h2h.py`.
- **The production override ledger (`ledger.py`, `apply_overrides`):** left alone. Review edits use their own file, so the public bracket's rules don't change.

## New files
| File | What it does |
|---|---|
| `src/bracketology/review.py` | Builds a review: B1 frozen v2.0, B2 shadow, B3 v2.0 plus your edits. Per-team evidence and flags, change report, freeze, grade. CLI. |
| `src/bracketology/review_page.py` | Renders the owner-only page: one HTML file with no server. |
| `src/bracketology/shadow_h2h.py` | B2 shadow model (docs/23 method). |
| `src/bracketology/review_demo.py` | Historical walk-through (2026 a week out, then Selection Sunday). |
| `models/shadow_h2h.joblib` | Shadow weights trained on 2019 and 2021-26, so CI won't need the local Torvik history. |
| `private/reviews/2027.json` | Your edit log. Gitignored and never committed (owner decision 2). |
| `tests/test_review.py` | Edit engine, grading groups, freeze rules. |

## How it works
**Bracket structure:** the bracket is an ordered list. Lines come from the season's slot sizes, so line sizes can't break.
- **Move to line L:** the team goes to the top of L if moving up, or the bottom if moving down. Exactly one team shifts across each boundary passed.
- **Swap:** two teams trade places.
- **Add:** a team comes in; the lowest-P(in) at-large team goes out unless you name one. Automatic bids can't be removed.
- **Remove:** a team goes out; the best outside candidate comes in unless you name one. Automatic bids can't be removed.
- **Undo:** retracts an earlier edit.

**Each log entry records:**
- the time (UTC);
- line and overall position before and after;
- every team whose line changed;
- reason code (injury/availability, recent form, committee precedent, metric disagreement, head-to-head, schedule quality, conference tournament, bracketing rule, other with explanation);
- confidence 1-3;
- phase (pre-championship week or championship week).

**Page sections:**
- **Seed board** with confidence dots; edited teams are outlined.
- **Team panel:**
  - model line, overall rank, shadow line, your line, confidence and P(in);
  - distance to the next line in positions' worth of model score;
  - résumé (record, NET, WAB, SOR, rating ranks, Q1A/Q1/Q2, Q3/Q4 losses, road and neutral wins, last 10, conference-tournament record, plus KPI/BPI/KenPom/T-Rank/official WAB when the live table has them);
  - stronger/weaker than neighbours;
  - the 4 teams above and below, with score gap, head-to-head and common-opponent records;
  - **"why the model might be wrong" flags**, each tied to a measured pattern (docs/11, 12, 39-41).
- **Edit form** with a live preview.
- **Three-bracket comparison.**
- **Change report** against the previous review:
  - line changes, entries and exits;
  - new champions and bid thieves (an unlikely champion from a league that also has at-large teams in the field);
  - teams within half a position of a boundary;
  - confidence changes of 15 points or more;
  - score moves that didn't change a line, and line changes caused by other teams.
- **Edit log with export.**

**Persistence ($0, no server):** edits made on the page stay in that browser until exported. **Export → paste into `reviews/2027.json` → commit.** The next build recomputes everything from that file. The JavaScript engine is checked against the Python one: identical B3 on the demo.

**Freeze:** `python -m bracketology.review freeze 2027` writes `data/freeze/2027_freeze.json` with the three brackets, the edit log, the input timestamps (`games_through`, NET source and as-of) and a SHA-256.
- It refuses to overwrite.
- It refuses a review generated after **12:00 ET on Selection Sunday (16:00 UTC on March 14, 2027, EDT)**.

**Grade:** `python -m bracketology.review grade 2027` scores B1, B2 and B3 with the Matrix rubric and gives each one's 2027 Matrix percentile. Your contribution (B3 − B1) is split into **edit groups**: edits that changed any of the same teams are joined (union-find). Scoring is a sum over teams, so each group's points are exact and the groups add up to the total. Groups with more than one edit are marked as credited jointly, never as independent.

## Demo (2026, local)
`python -m bracketology.review demo 2026`. Model and shadow trained without 2026, rebuilt a week out (archived NET) and on Selection Sunday. The demo edits replay five of the owner's actual 2026 Matrix-bracket moves.
- **B1 v2.0:** 356 (10th percentile). **B2 shadow:** 346 (6th). **B3 with the five replayed edits:** 377 (62nd).
- **Edit groups:** Saint Louis and Texas A&M jointly +7 (they interact through SMU and Iowa); BYU +4; Saint Mary's +4; Miami (OH) in for Auburn +6. The groups sum to +21, which equals B3 − B1.
- **Change report, D-7 → Selection Sunday:** 22 line changes, 12 teams in and out (mostly auto-bid winners), 26 new champions, 21 teams near a boundary.

This replays known-good moves to show the mechanics. It's not evidence that review helps. That's measured only by 2027 (docs/38).

## Remaining steps (each needs the owner's approval)
1. **Where the page lives.** The repo is public, so a GitHub Actions artifact or committed HTML would be visible to anyone. Options:
   - (a) build locally on demand;
   - (b) a private claude.ai artifact refreshed by me;
   - (c) an encrypted artifact.

   I recommend (a) now and (b) for championship week.
2. **Whether `reviews/2027.json` is committed publicly before Selection Sunday.** Public commits give tamper-evident timestamps but reveal your calls early. The alternative is keeping it local and committing it at the freeze.
3. **Freeze timing.** The Cloudflare timer's Selection Sunday crons run at 21:10 and 21:40 UTC, after the noon ET freeze. A 15:30 UTC run on March 14, 2027 is needed (a `trigger/wrangler.jsonc` change plus redeploy).
4. **Daily build in the workflow:** after the projection, run `review build 2027` and keep the JSON on the snapshots branch (no third-party r_* columns there, as now).
5. **Grade job** after the bracket show.
6. **2027 rule changes noted from the reviewed links** (bracketology.tv): the official WAB bubble moves from NET #45 to #55 for 2026-27, and the 76-team field already matches `fieldformat`. v2.0's own WAB stays as trained (frozen). The review page shows official WAB from Warren Nolan when available.

## Reviewed links (2026-11-15)
- **Miami (2019):** pick odds, generic ranking.
- **Illinois (2026):** seed-history win rates.
- **AP:** couldn't be fetched.
- **YouTube:** title only.
- **Instagram @bracketsscience:** login wall. Its bio claims 68/68 in the field and every team within one seed line; that's self-reported and unverified.
- **The Gaming Juice Big Board (Brad Evans):** explicitly a human estimate of "what I believe the Committee's is," using NET, Q1, SOS, WAB, KenPom and Torvik. It supports the docs/41 conclusion that the elite edge is human reading.
- **bracketology.tv:** 2027 format facts (above).

None of them describes a free, automatic seeding method not already tested here.

## Deployment readiness (2026-11-15), after the owner's decisions
**Decisions:** the editing interface and the edit ledger stay private. The public site shows only the resulting bracket. The freeze runs at 11:30 a.m. ET with a verified noon ET cutoff.

### Fixed in this round
- **Ledger privacy:**
  - `reviews/2027.json` (empty) was removed from the repo.
  - Edits, reviews and freezes now default to `private/`, which is gitignored.
  - `write()` refuses to write into the site output or snapshot folders.
  - A test confirms nothing under `private/` or `reviews/*.json` is tracked by git.
- **Shadow leakage guard:** saved shadow weights now record their training seasons (`train_years`) and are reused only if those exclude the evaluated season; otherwise the shadow is refit. The earlier 2026 demo was clean (its B2 equals a fresh fit without 2026), but the old code would have leaked on any later replay.
- **Review files** are named by collection time, so an 11:30 build no longer overwrites the morning one.
- **Freeze** (`review.freeze`):
  - Picks the **newest review whose data were collected at or before the cutoff and that passes every check**: all three brackets present, field size and line sizes match the season's format, B2 on the same field as B1, no data-check alerts, shadow not trained on the season.
  - Records full bracket contents (team, line, champion and projected-auto flags), input timestamps (`collected_at`, `games_through`, latest game used, NET source and as-of), model version, fingerprints of the models actually used, saved v2.0 file hash, code commit, the edit file's SHA-256, the edits as logged, the applied edits with line changes, edits not applied, and the reviews skipped and why.
  - Writes with an atomic create-only link, sets the file read-only, and writes a `.sha256`.
  - A second attempt verifies and returns `already_frozen` without rewriting.
  - A late run (missed schedule) can still freeze, but only a review collected before noon; `frozen_after_cutoff` is recorded.
- **Independent noon verification** (`review verify`): recomputes the hash and re-checks the cutoff, completeness and, for live seasons, that the model used is exactly the saved v2.0. It writes a separate dated `{season}_verify_*.json` and never touches the freeze.

### Reconciliation of the 2026 demo
**The 377 is a replay, not your 2026 submission.** It applies five of your 2026 moves to v2.0. Your submitted bracket scored **370**. The two differ on 16 teams, net +7 for the replay:
- **Better in the replay:** Purdue, Michigan State, Virginia, Miami (FL), Utah State, Missouri, UCF, Miami (OH) and Siena.
- **Better in your submission:** Gonzaga, TCU, Santa Clara, Kennesaw State, Furman and UMBC.
- **Queens:** same points either way.

### Tested (47 tests pass)
- **Edit engine:** valid line sizes for 68 and 76 teams; one team shifted per boundary; automatic-bid guard; undo; invalid edits reported. The JavaScript engine matches the Python one exactly.
- **Grading:** groups are exactly additive; interacting edits are credited jointly. A perfect 76-team bracket scores 456 (= 76 × 6).
- **Cutoff:** the noon ET cutoff is 16:00 UTC on March 14, 2027 (EDT starts that morning). An 11:30 run freezes the 11:30 review. A 12:01 review is refused even when newer.
- **Recovery:** a missed run falls back to the morning review (flagged late). Incomplete reviews (no B2, broken line sizes, data alert, shadow trained on the season, half-written file) are skipped. No valid review fails loudly.
- **Duplicates and tampering:** duplicate freezes are idempotent. Tampering is caught by verify and blocks re-freezing. A substituted model fails verification for a live season.
- **Privacy:** no private file is tracked, and writes into public output are refused.
- **End-to-end 2026 demo:** freeze picked the 15:30Z review (cutoff 16:00Z); verify passed at 16:05Z; scores B1 356, B2 346, B3 377; groups sum to +21.

### Verified by construction
B1, B2 and B3 come from **one** `build()` call. They share the same rows, the same game list filtered at the same `games_through`, and the same field (B2 re-orders B1's field; B3 is B1 plus logged edits). The freeze records `consistency.one_cutoff_for_all_brackets` and checks `B2_same_field_as_B1`.

### Blocked: needs approval or decisions before deployment
1. **Private automation host.** The freeze must run automatically at 11:30 ET where the private ledger lives. GitHub Actions in the public repo can't hold it privately, and artifacts in public repos are downloadable. Recommended ($0): a free **private GitHub repo** holding `reviews/`, review outputs and freezes, with its own workflow that checks out the public code and runs `review build` → `freeze` at 15:30Z (retry 15:45Z) → `verify` at 16:05Z and 16:30Z. It's triggered by the existing Cloudflare timer (two new cron entries plus a dispatch to the private repo, which needs a fine-grained token scoped to that repo). Not created yet.
2. **Public site shows only the resulting bracket.** Today the template shows "Edited (model N)" tags and override reasons, and snapshots include the model bracket next to the adjusted one, which together would reveal the edits. Changing `sitebuild`, the template and the snapshot contents is a production change.
3. **How the resulting bracket reaches the public build without the ledger.** Options:
   - (a) the private workflow commits a lines-only bracket file to the public repo;
   - (b) an encrypted secret.

   I recommend (a): it reveals only what the site shows anyway.
4. **Trade-off of the noon freeze, for the owner to confirm.** Selection Sunday conference finals are usually played in the afternoon, and 7-9 field teams play that day (docs/35). An 11:30 freeze uses projected champions for those leagues and can't see a Sunday bid thief. The Matrix deadline is later in the day.
5. **Daily review build and grading job** wiring, after item 1.
6. **2027 official bracket parsing:** `bracketmatrix.collect` is verified on 68-team pages only. The rubric and formats handle 76, but the 2027 page parser can only be checked once the page exists. Fallback: `review grade 2027 official.json`.

**Update (2026-11-15):** docs/43 supersedes the private-repo plan above. It adds a second (final) snapshot, the Access/Worker/D1 recommendation with its threat model, and the approval list.
