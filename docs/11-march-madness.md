# March Madness bracket picker: groundwork (built Nov 2026)

Goal: pick a bracket for a ~120-entry pool scored 1-2-3-4-5-6 points per round (120 max).

## Data
- Tournament history: every NCAA bracket 2008-2026 (no 2020) from Wikipedia wikitext, 1,196 games with seeds and scores (`madness/wiki.py`). Checks: exactly two 16-over-1 upsets (2018, 2023); 2021 VCU-Oregon no-contest is the only missing game.
- Team ratings: fit from Torvik game logs using only games through each Selection Sunday (`madness/ratings.py`), so no tournament result leaks in. Torvik's own pre-tournament ratings would be better, but its time machine is disallowed and the Internet Archive was unreachable from this machine.
- ESPN is not used anywhere: espn.com's robots.txt disallows Anthropic's crawler.

## Win probabilities (`research/madness_backtest.py`, leave-one-season-out)
| Model | Log loss | Brier | Favorite won |
|---|---|---|---|
| Seed only | 0.572 | 0.196 | 69.8% |
| Ratings | **0.550** | **0.187** | 70.7% |
| Ratings + seed | 0.550 | 0.187 | 70.5% |

Ratings beat seed in 14 of 18 seasons and are well calibrated (predicted 77% → won 79%). Weighting recent games more (45-day half-life) was worse, so all pre-tournament games count equally. Seed adds nothing once ratings are known.

## Pool strategy (`research/madness_pool.py`)
Three brackets per season, scored on the real results against 119 simulated public entries:
- **chalk**: better seed every game
- **max points**: most expected points under the rating model (exact)
- **pool pick**: max-points bracket with the champion chosen for the best simulated chance to finish first

| vs public that picks… | Strategy | Avg points | Expected wins /18 | Actual wins /18 | Avg finish |
|---|---|---|---|---|---|
| like the model, favorite-heavy | chalk | 69.2 | 0.31 | 0.94 | 86% |
| | max points | 68.9 | 0.37 | 0.21 | 85% |
| | pool pick | 64.7 | 0.49 | 0.00 | 76% |
| by seed | chalk | 69.2 | 2.34 | 3.81 | 95% |
| | max points | 68.9 | 3.06 | 4.78 | 92% |
| | pool pick | 68.2 | 3.09 | 4.60 | 91% |

A random entry wins 0.15 of 18 pools. What this does and doesn't show:
- All three strategies score about the same (64-69 points). In this format, 64 of the 120 points come from the first two rounds, and the champion is worth 6 points plus its path. Accuracy in the first weekend matters more than the champion pick.
- On paper, a contrarian champion raises the chance of winning by about a third. In history it didn't: a win happens or it doesn't, and 18 pools are far too few to tell 0.4 wins from 0.5.
- The simulated public is a guess. "By seed" is clearly too weak an opponent (it makes every strategy look like it wins 1 pool in 4). Real pick percentages are the missing input.

## March checklist
1. Rebuild 2027 ratings through Selection Sunday (`research/madness_build.py`, then add 2027 to `wiki.SEASONS`).
2. Better probabilities: blend in betting lines for each first-round game (Betalytics captures), which typically beat ratings.
3. Real public picks: copy ESPN "Who Picked Whom" / Yahoo pick percentages by hand once brackets open (ESPN blocks bots); replace the simulated public with them.
4. Run the pool pick with those inputs; prefer contrarian choices only where the public is lopsided on a team the model rates no better.
