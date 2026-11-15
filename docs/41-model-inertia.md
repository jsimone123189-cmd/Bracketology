# Why v2.0 misses elite championship-week moves: inertia or missing information?

Committed before the diagnostic was run. Seasons with elite D-7 snapshots: 2021, 2022, 2023, 2025, 2026 (docs/36). **Status: exploratory** (the direction came from these seasons).

## Setup (as in docs/39)
- **v2.0 at D-7:** NET from D-9 to D-7, games through D-7, champions decided by D-7, other leagues projected. Model trained on the other seasons' final data.
- **v2.0 at final:** held-out production run. The **same fitted model** scores both states, so scores are comparable.
- **Elite:** brackets fresh at D-7 (docs/36 rule), D-7 against final.

## Definitions, fixed before looking at correctness
- **Elite move:** a team in the actual field, in v2.0's D-7 and final brackets, and in at least half the fresh elite brackets at both times, whose **mean elite line changed by at least 0.5**. Direction d = sign of the mean change (negative = better line).
- **Missed move:** an elite move where v2.0's line is the same at D-7 and final.
- **Score unit u:** per season, the median score gap between consecutive teams in v2.0's final order (one position's worth of score).
- **Own change:** the team's v2.0 score change, D-7 to final, signed toward the elite direction (positive = the model moved its score the way the elite moved the team).
- **Others' effect:** final rank minus the rank the team would have had with its final score among the other teams' D-7 scores (positions, signed toward the elite direction).
- **Boundary distance:** the score gap, in units of u, from the team's final score to the nearest team on the adjacent line in the elite's direction.
- **Conference-tournament games in the week:** the team played a conference-tournament game after D-7.

## Categories, applied in this order
- **D, insufficient evidence:** the team's champion status changed between D-7 and final (auto-bid mechanics), or a needed value is missing.
- **A, inputs changed but the ranking didn't respond:** own change at least **2u** toward the elite direction.
- **C, caused by other teams:** not A, and others' effect at least **2 positions** toward the elite direction.
- **B, inputs barely changed:** everything else, meaning the model saw no meaningful change. That points to missing information or judgment.

## Reported
- Counts per category, per season, with team lists.
- **Paired moves:** a missed move whose opposite-direction partner crosses the same line boundary.
- Movement rates for teams with and without conference-tournament games in the week, elite against v2.0.
- **Exact-seed implication:** v2.0's line shifted by the rounded mean elite change, scored as exact gained minus lost against the committee seed. This is the only place the committee's seeds are used, after classification.

## Decision rule for an experiment, fixed now
An experiment is run only if Category A's exact-seed implication is at least **+1.5 a season** and positive in at least **4 of 5** seasons. Otherwise no experiment is run, and the recommendation follows the category split.
