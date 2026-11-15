# Automatic-bid test, random line shifts, and the daily review list

Committed before running.

## Test 4: automatic-bid status in the seed model
docs/12 found that, holding stats equal, the committee places automatic bids about 0.2 lines worse, and so do the consistent nine. v2.0's seed model can't do this.
- Add `champ` (1 for an automatic bid) to the **seed model only.**
- Leave-one-season-out, control must reproduce 335 326 347 344 329 363 356, usual bar: +3 mean, better in 5 of 7, no season worse than -5.
- This is the fourth feature test on these seven seasons. A pass goes to shadow tracking in 2027 and replaces nothing without the owner's decision.

## Random line shifts (owner's question)
Starting from v2.0's held-out bracket each season, 2,000 random draws:
- **A, all teams:** 5% of the field moves 2 lines and another 25% moves 1 line. Direction is random, within lines 1-16, with no line-size limits. Bracket Matrix scores lines only, so this shows the pure scoring effect.
- **B, low confidence only:** the same 5% and 25%, taken from teams with confidence under 0.5 (docs/12 method, nested spreads).
- **C, legal bracket:** like B, but each move is a swap with a random team on the target line, so every line keeps its size. The partner's move counts too.

Reported per season and overall:
- mean change in score, chance of beating v2.0, chance of +3 or more, and the 5th and 95th percentile of the change,
- change in exact seeds on lines 5-8,
- the chance of reaching that season's 90th-percentile Matrix score, with and without shifts.

There's no pass bar, because nothing is fitted. A version would only be worth a test if its mean change were +3 or more.

## Daily review list
Production gets the docs/12 confidence for every projected team. Spreads by predicted position band are fixed from the pooled held-out residuals of all seven seasons. Snapshots record each team's confidence and the list of teams under 0.5. This changes no line and no model weight. The public page doesn't show it.

## Results (2026-11-14)
Output: `research/tests13_output.txt`. The control reproduced.

**Test 4, automatic-bid status, failed:** 334 326 353 340 323 357 368. Mean +0.1, better in 2 of 7, worst -6. The committee's discount of automatic bids, seen in docs/12, doesn't turn into points when added to the seed model.

**Random shifts hurt every season, every version:**

| Version | Mean change per season | Seasons with any real chance of gain | Exact seeds on lines 5-8 |
|---|---|---|---|
| A, all teams | -23.2 | none (better in 0-1% of draws) | -1.2 per season |
| B, low confidence only | -8.4 | 2024 only (better 17%, +3 or more 9%) | -1.4 |
| C, legal swaps, low confidence | -14.8 | 2024 only (better 8%) | -2.1 |

- Not one draw out of 14,000 per version lifted v2.0 to a season's 90th-percentile Matrix score.
- **Why it hurts:** even low-confidence teams are on the exact line 46% of the time, and within one line about 85%. A random move breaks a correct line much more often than it fixes a wrong one. Low-confidence misses go both ways, so a direction picked at random is right only half the time on the teams that were actually off.
- **Conclusion:** random variation lowers both the average and the chance of a top finish. What could gain points is moving low-confidence teams in the right direction, which needs real information about each team. That's the job of the owner's reviewed adjustments, graded after each Selection Sunday.

**Daily review list:** live from commit 12d4f31. Snapshot field `review` lists teams under 0.5, lowest first, and `model_bracket` carries each team's `confidence`. Spreads are [2.22, 5.17, 3.97, 1.71] positions for predicted bands 1-16, 17-32, 33-48, 49-68. The first live run (November 15) listed 39 teams.
