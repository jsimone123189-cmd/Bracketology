# Are the real team-sheet metrics what we're missing?

Committed before running.

## Why
The committee's sheets carry NET plus KPI, ESPN SOR, ESPN BPI and KenPom (Sagarin before 2024-25, T-Rank and WAB after). Bracketologists read all of them. v2.0 uses only NET plus its own rebuilt WAB, SOR and rating. The NCAA's public sheets dropped the other metrics after 2019-20, so the only as-of copies we hold are Torvik's team-sheet captures: 2021, 2022, 2023 (the Saturday before) and 2025. Warren Nolan publishes the same ranks daily, so a live version would be possible.

## Diagnostic (four seasons, seeding only)
The actual field is given, to isolate seeding. Each method ranks those teams, and lines are filled in that order using the season's line sizes. Measures: exact seeds and the Matrix score on that fixed field.
- **v2.0:** held-out `rank_score`.
- **Sheet average:** mean of NET, KPI, SOR, BPI and KenPom ranks, the five present in all four seasons.
- **Résumé only:** mean of KPI and SOR. **Predictive only:** mean of BPI and KenPom.
- **Blend:** half v2.0, half sheet average, each z-scored within the field. The weights are fixed now and won't be tuned.
- **Reference:** the consistent nine's mean exact seeds on the same teams.

**Decision rule, fixed:** the real sheet metrics are "the missing piece" only if the sheet average or the blend beats v2.0 by at least 2 exact seeds in at least 3 of the 4 seasons.

## If it passes
Four seasons can't meet the seven-season bar, so nothing goes into production on this alone. The step after would be:
- a committed test of v2.0 plus the sheet metrics, using the four seasons that have them,
- and shadow tracking the variant all through 2027 from Warren Nolan's daily columns, graded on Selection Sunday against v2.0.

## Results (2026-11-14)
`research/teamsheet_diag_output.txt`. Exact seeds on the actual field, four seasons:

| Method | Mean exact per season | Gap to v2.0 |
|---|---|---|
| v2.0 | 43.3 | |
| Sheet average | 34.5 | -8.8 |
| Résumé only | 32.8 | |
| Predictive only | 24.8 | |
| Blend | 40.5 | -2.8 |
| The nine | 49.9 | |

The sheet average beat v2.0 by 2+ in 0 of 4 seasons and the blend in 1 of 4, so the real team-sheet metrics are not the missing piece.
