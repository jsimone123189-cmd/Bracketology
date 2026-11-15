# 2027 prospective evaluation plan

Committed before the 2027 season. This plan, not any later choice, decides how 2027 is judged. Nothing deploys without the owner's approval.

## The three brackets
1. **Frozen v2.0 (B1).** The production model as of this commit (model code, features and training seasons 2019, 2021-26), with no edits. Daily, it's the `model_bracket` already saved in every snapshot.
2. **Experimental model (B2).** Nothing passed the replacement bar, so B2 is the strongest pre-registered candidate: v2.0 plus head-to-head and common-opponent pair features (docs/23, +1.6, better in 3 and worse in 1). Its code is frozen at this commit. It's computed in the same daily run, saved in the snapshot as `shadow_bracket`, and never published.
3. **Model plus the owner's documented adjustments (B3).** B1 with `overrides/2027.json` applied (docs/37). Only entries timestamped before the freeze count.

## Freeze
- **Freeze time:** 12:00 ET on Selection Sunday 2027 (before the 6 p.m. reveal). All three brackets are taken from the last scheduled run before the freeze. The Cloudflare timer's Selection Sunday crons run at 21:10 and 21:40 UTC. The freeze file is the snapshot with the latest `generated_at` before 16:00 UTC (12:00 ET).
- The freeze snapshot is committed to the repo with its git hash, and its SHA-256 is written in this doc's results section.
- **76-team format:** the 2027 field expands to 76 (fieldformat must be updated and tested before February; this is an open pre-launch task). All three brackets use the same format.

## Scoring
- Bracket Matrix rubric against the official 2027 bracket: 3 per team, plus 3 for the exact line or 1 for one line off.
- The 2027 Matrix percentile for each bracket comes from the Matrix's final page (the entry's score against all entries except MATRIX).
- **Reported:**
  - total, teams picked, exact lines, within one;
  - exact lines by bands 1-4, 5-8, 9-12, 13-16 (or the 2027 equivalents);
  - small-conference champions;
  - for B3, points by ledger reason code and confidence, and by v2.0 confidence band (docs/37).

## Decision rules, fixed now
- **B2 replaces B1 for 2028** only if B2 ≥ B1 + 3 in 2027, and the pooled eight-season leave-one-out score (2019, 2021-27) still meets the replacement bar.
- **Owner review is "validated for 2027"** if B3 > B1. It's **"worth continuing"** if the per-adjustment ledger shows positive net points in the reason codes with at least 5 entries. One season can't prove an edge. Two consecutive seasons with B3 > B1 by 5 or more is the bar for calling review a reliable part of the system.
- **The top-quartile goal** is checked per bracket against the 2027 Matrix's 75th percentile.

## Build tasks (each needs owner approval before production changes)
1. Add `shadow_bracket` (B2) to the daily snapshot. Research code is ready (`research/common_opponents.py`); it needs moving into `src/` with tests.
2. Ledger categories and reason codes (docs/37).
3. The review page builder (docs/37), as a private workflow artifact.
4. A grading report script: B1/B2/B3 scores and ledger outcomes.
5. 76-team `fieldformat` update and tests.
6. Freeze step: a workflow job on Selection Sunday that commits the freeze snapshot and hash.

**Status (2026-11-15):** B1/B2/B3 build, freeze (with SHA-256, no overwrite, noon-ET deadline) and grade (edit groups) are implemented in `review.py` (docs/42). Still needed: freeze-time cron, daily workflow step, page hosting decision.

**Update (2026-11-15, docs/43):** Selection Sunday now has two immutable snapshots. The noon-ET research snapshot (B1/B2/B3) is the one graded under these rules. A separate final competitive snapshot is taken after the Sunday conference finals and before a confirmed submission deadline. Scoring and decision rules here are unchanged.

**Update (2026-11-15, owner decision):** the research snapshot (graded under this plan) is frozen at 12:01 p.m. America/New_York, with a strict noon cutoff for collected data and logged edits (docs/45).
