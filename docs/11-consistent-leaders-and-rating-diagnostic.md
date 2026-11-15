# Two diagnostics: consistent leaders, and rating magnitude

Written and committed before either comparison with v2.0 was run. These are diagnostics, not model tests. Neither can change v2.0. Any idea that comes out of them needs its own rules committed first, and then has to clear the usual bar: +3 mean points, better in 5 of 7 seasons, no season worse than -5.

## 1. Who is consistently good (already computed, scores only)
Bracket Matrix final scores, 2019 and 2021-26, excluding the Matrix consensus. Percentile = share of that season's entries the bracket strictly beat. Top-20 by rank is too noisy, because ties are common and one point can move a bracket 50 places. Nobody was top 20 in more than 4 seasons.

**The consistent group** is every entry that:
- entered at least 5 of the 7 seasons,
- averaged the 75th percentile or better, and
- never fell below the 50th.

That is 9 entries: Dom, Bauer, BKS, Sluder, DII, HHD-JT, 801, Elam, T3. They beat the season median by 7.6-12.5 points a season. v2.0 held-out was at the 21st, 9th, 39th, 14th, 10th, 75th and 10th percentiles, 26th on average.

## 2. Where they beat v2.0
Using v2.0's leave-one-season-out brackets (the 342.9 run):
- Points gap split into teams picked, exact seeds, and within-one seeds, by season.
- Exact-seed rate by line band (1-4, 5-8, 9-12, 13-16).
- Selection: v2.0's wrong teams, and how many of the group got each one right.
- Mean signed seed error for power and non-power at-large teams, for v2.0 and the group.
- A list of teams that at least 7 of the 9 placed within one line, where v2.0 missed by 2 or more lines or picked the wrong team.

Use limits:
- The group's brackets are never a model input or a weight, and never decide a team's line.
- At most two hypotheses can come out of this. Each must use free, automatically collected data available by the Selection Sunday cutoff, and get its own committed test.
- These are the same seven seasons used for everything else, so a pattern found here is weak evidence until a test clears the bar.

## 3. Rating magnitude (plan item B)
v2.0 already uses our own margin-based rating as both a value and a rank. The open question is whether Torvik's predictive rating explains v2.0's misses where ours doesn't. Torvik history is held locally for 2019 and 2022-25 only. Torvik refuses GitHub, so he can never be a live input.

Measures, by season, over teams in the actual field:
- Residual = actual overall seed position minus v2.0's held-out overall position. Positive means the committee placed the team worse.
- Magnitude gap = Torvik AdjEM (AdjO minus AdjD), z-scored within that season's field, minus our rating z-scored the same way.
- Rank gap = log of our rating rank minus log of Torvik's rank.
- Spearman correlation of residual with each gap, and the magnitude coefficient in a per-season regression of residual on both gaps.
- v2.0's wrong teams: mean gaps for teams v2.0 had in but the committee left out, and the reverse.
- Each 2+ line miss, listed with its gaps.

**Decision rule, fixed now:** Torvik magnitude explains misses only if:
- the residual-vs-magnitude correlation is negative in at least 4 of 5 seasons,
- with a mean of -0.15 or lower, and
- the magnitude coefficient stays negative after rank in at least 4 of 5.

If it does, the next step is one committed test of a better rating of our own, built from free live data. Torvik would never be an input. If it doesn't, item B is closed.

## Results (2026-11-14)
Output: `research/leaders_and_magnitude_output.txt`. The control reproduced 335 326 347 344 329 363 356.

### Where the consistent group beats v2.0
They outscore v2.0 by about 20 points a season. Season by season, v2.0 then the group average: 335/356, 326/360, 347/363, 344/371, 329/345, 363/366, 356/382. Nearly all of the gap is seeding, not selection.
- **Exact seeds:** v2.0 averaged 41.6 a season, the group about 49. That's roughly 7 more teams on the exact line, worth about 21 points. Teams picked differs by about 1 a season, worth about 3 points.
- **Middle lines are the weakest spot.** Exact rate on lines 5-8 was 0.43 for v2.0 against 0.57 for the group. Lines 1-4 were 0.72 against 0.85.
- **Selection (corrected 2026-11-14, see below):** v2.0 had 14 wrong teams over seven seasons. The group shared 5 of them, mostly: TCU 2019, Louisville 2021, Texas A&M 2022, Oklahoma 2024, West Virginia 2025. It mostly avoided the other 9: Clemson, NC State, Oklahoma 2022, SMU, North Texas, Indiana State, Seton Hall, Auburn. The group averaged about 1.1 wrong teams a season, against 1.86 for v2.0.
- **Non-power at-large teams:** v2.0 put them too low (higher line numbers) by more than a line in 2019 (+1.14) and 2026 (+1.33), and by +0.56 in 2022. The group was within about 0.3 of zero in each. 2023 went the other way (-0.50).
- **Small-conference champions are v2.0's biggest single misses, in both directions:** Colgate 2021 (seed 14, v2.0 line 7, NET 9), Loyola Chicago 2021 (8 vs 6), Memphis 2023 (8 vs 5), Florida Atlantic 2023 (9 vs 6), Murray State 2022 (7 vs 10). The group got all of these within a line.
- 30 team-seasons fit the list rule (75%+ of the group within one line, v2.0 off by 2+ or missing). v2.0's line was too high for 9, too low for 13, and the team was missing for 8.

### Rating magnitude: closed
Torvik's rating gaps don't explain v2.0's misses. The correlation was negative in 2 of 5 seasons, mean -0.008, and the coefficient after rank was negative in 3 of 5. The rule needed 4 of 5, a mean of -0.15 or lower, and 4 of 5. Plan item B is closed.

**Correction made during the run:** the saved Torvik pages append text to team names, like next-game notes and, in 2023-24, the tournament seed. The first pass matched almost no 2022-24 teams. Names are now cleaned before matching. The seed notes also show that the 2023 and 2024 pages were saved after Selection Sunday. v2.0 never reads these files (checked: no Torvik field in features, metrics, model or project), so the baseline isn't affected. They should not be used as cutoff-time data without checking their dates.

### What could come next (not yet run)
At most two hypotheses, each needing its own committed test:
1. **Selection:** why v2.0 picks power-conference teams with NET 33-56 that the committee leaves out. The test would be one free-data feature for that profile.
2. **Seeding small-conference champions and non-power at-large teams.** These are the largest misses, and they go both ways.

### Correction (2026-11-14)
The first version of this section said all 9 left out every one of v2.0's wrong teams. That was wrong. `bracketmatrix.parse` only reads the rows for teams in the actual field, so a bracket's wrong teams were never visible, and every "group had it in 0/n" count was 0 by construction. `research/matrix_full.py` also reads the "other at-large" rows. Its pick counts match the Matrix's own reported numbers for every entry in every season. The corrected selection numbers are above. Everything else in this section used only teams in the actual field, so it isn't affected.
