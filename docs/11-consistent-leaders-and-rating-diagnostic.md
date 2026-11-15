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
