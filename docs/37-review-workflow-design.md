# Path B: structured model-assisted review (design)

A design only. Nothing here changes production until the owner approves the build.

## What already exists (verified in code)
- `overrides/{season}.json` with `ledger.validate`: each adjustment needs a time, category, reason and evidence, and can't be dated in the future. Allowed categories today: availability, factual_correction, unusual_circumstance. Evidence from other bracketologists or the Matrix is refused.
- `project.apply_overrides`: moves a team to a line, optionally swapping with another team, and warns if line sizes break. `model_line` is kept on every team.
- `project.closest_calls`: the tightest line boundaries and the bubble. `project.confidence` and `review_list`: each team's chance of being on exactly its line (docs/12-13).
- `project.grade`: after Selection Sunday, model alone against model plus edits, using the Matrix rubric.

## What changes
**1. New ledger categories** for the owner's own judgment: `seeding_judgment` and `selection_judgment`. The rule against other bracketologists stays. Each entry also records the owner's **confidence (1-3)** and **one of the fixed reason codes** below, so later grading can show which kinds of call pay.

**Reason codes:** `injury_or_availability`, `recent_form`, `committee_precedent` (an earlier season's treatment of a similar résumé), `metric_disagreement`, `head_to_head`, `schedule_quality`, `conference_tournament`, `bracketing_rule`, `other` (free text required).

**2. Review page.** A private, static HTML file built from the daily projection JSON by a new script (`research/review/build_review.py`, later a workflow artifact). It isn't published on the public site. Sections:
- **Seed list board:** lines 1-16, with each team's model line, overall position, confidence (traffic-light) and p_in. Teams on the review list come first, in confidence order. Since docs/35 showed review pays across the whole bracket, every team stays visible.
- **Neighbours panel:** for a chosen team, the 4 teams above and 4 below in the order, with each gap in model score, so you can see how close the line boundary is.
- **Résumé comparison:** a side-by-side table against those neighbours. NET, our WAB/SOR/rating ranks, Q1A/Q1/Q2 records, Q3/Q4 losses, road and neutral wins, SOS, last-10. The two biggest advantages and disadvantages are highlighted automatically, by z-score difference.
- **Head-to-head and common opponents** against the neighbours (docs/22-23 code).
- **Metric disagreement:** where NET, WAB, SOR and rating rank the team furthest apart (largest spread of log ranks). A wide spread is a documented sign of a contested placement.
- **"Why this could be wrong":** generated flags, each tied to a measured pattern:
  - a small-conference champion (v2.0's weakest group, docs/11);
  - a non-power at-large team (bias flips by season, docs/11);
  - a power team with NET 33-56 near the cut line (docs/11);
  - a large residual band, lines 5-8 (docs/12);
  - a Sunday title game still to be played;
  - a head-to-head against a neighbour on the other side of the line.
- **Edit form:** choose a new line, or swap with a named team. Line sizes are checked live, the same check as `apply_overrides`. Picking a reason code and a confidence is required. Clicking the button produces the JSON entry to commit into `overrides/2027.json` (copy-and-commit, so it needs no server and costs $0).

**3. Grading report.** After Selection Sunday, `report.py` (planned) fills `final_outcome` and `score_impact` for every ledger entry. It totals by reason code, confidence and v2.0 confidence band, so we learn which kinds of call add points.

## Guardrails
- The public bracket shows model and adjusted lines separately, as now.
- An adjustment counts in the evaluation only if its timestamp is before the freeze (docs/38).
- No assumption that review helps. It's measured prospectively (docs/38).

**Status (2026-11-15):** built. See docs/42 for the tool, the demo and the remaining approval steps.
