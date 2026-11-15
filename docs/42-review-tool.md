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
| `reviews/2027.json` | Your edit log (starts empty). |
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
