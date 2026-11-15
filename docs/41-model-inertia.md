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

## Results (2026-11-15), exploratory
`research/model_inertia_output.txt`, plus a descriptive addendum in `research/gap_teams_output.txt`.

### v2.0 isn't inert
Of 260 field teams tracked across the five seasons, the elite mean line moved for **48%** and v2.0's line moved for **42%**. That's 55% against 45% for teams without conference-tournament games in the week, and 48% against 42% with them. **Correction to docs/40 and the handoff:** "about 6 v2.0 moves against about 24 per elite bracket" compared v2.0's résumé-only moves with all elite moves. Counting all moves, v2.0 changes about 22 lines a season and the elite consensus about 25.

### Missed elite moves (elite moved at least 0.5 lines, v2.0 unchanged): 63 over five seasons
| Category | Count | Exact seeds if v2.0 had copied the elite's move | Median own score change | Paired |
|---|---|---|---|---|
| A: inputs changed (2u or more), ranking didn't respond | 7 (11%) | **+0** (0.0 a season) | +2.7u | 3 |
| B: inputs barely changed | **42 (67%)** | **-17** (-3.4 a season) | +0.6u | 21 |
| C: caused by other teams | 8 (13%) | -1 | -0.3u | 3 |
| D: champion status changed | 6 (10%) | +1 | +2.0u | 3 |

- **The experiment trigger (A at least +1.5 a season, positive in 4 of 5) isn't met.** Category A is small and worth nothing in exact seeds, so **no experiment is run.**
- **Copying elite moves on teams v2.0 didn't move would cost v2.0 17 exact seeds.** Many elite week moves correct the elite's own D-7 errors toward where v2.0 already was. Examples: Tennessee and Missouri 2026, Iowa State 2025, Colgate 2023.
- In two-thirds of missed moves, v2.0's own inputs barely changed (median 0.6 of a position's worth of score). When the elite move these teams, they act on something the model's inputs don't carry.

### Where the final gap actually comes from (descriptive)
Final-gap teams are those where most elite brackets are exact and v2.0 isn't: **69** over five seasons. The reverse happens 30 times. The net 39 (7.8 a season) matches docs/39.

| v2.0 | Elite | Teams |
|---|---|---|
| Wrong at D-7, unchanged | Fixed it during the week | 18 |
| Wrong at D-7, moved but still wrong | Fixed it during the week | 16 |
| Wrong at D-7, unchanged | Already right at D-7 | 13 |
| Moved away from exact | Fixed during the week (8) or right at D-7 (8) | 16 |
| Missed the team (selection) | | 3 |

- The elite's week gain is a mix: they fix errors that v2.0 keeps (34), and they correct their own D-7 errors (many toward v2.0's line).
- **16 harmful v2.0 moves** match docs/40's harmful-move count. Freezing them isn't selectively possible (docs/40: freezing all moves costs points).
- **13 errors predate the week entirely.**

## Decision
**B, prioritize structured human review.** Of the elite's moves that v2.0 misses, 67% happen with no meaningful change in the model's inputs. The few where inputs did change (A) carry no exact-seed value, and copying elite moves wholesale loses points. There's no demonstrated recoverable information for the automated model in championship week.

**The model's role stays essential and distinct:**
- It's the frozen base.
- It handles the mechanical automatic-bid updates, the largest single week effect (+9.3 exact, docs/39).
- It flags candidates for review.

**The human role:** the roughly 34 team-seasons a year where the elite fix a model error during the week (about 7 a season). The review page (docs/37) should show, for each team, the model's score change over the week and its distance to the next line boundary. A team whose inputs barely moved but whose situation changed (injury, the eye test, bracketing) is exactly where review can add what the model lacks.

**Automated development continues only through 2027 shadow tracking** (docs/38), not more retrospective variants on these seasons.
