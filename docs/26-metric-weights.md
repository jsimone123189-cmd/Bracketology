# Searching metric weights, honestly

Committed before running. The owner asked to try different weights on different metrics. A weight search scored on the same seasons it was tuned on would look good and fail in 2027. So every search here is **nested**: for each held-out season, weights are chosen using the other six seasons only, then scored on the held-out season.

v2.0 learns its seeding weights by predicting which of two teams the committee ranks higher. This search instead aims directly at what Bracket Matrix rewards: exact seed lines.

**Metrics,** z-scored within each season over teams with NET 120 or better, signed so higher is better:
- log NET, WAB, SOR, our rating,
- Q1 wins, Q1A wins, Q1 losses, Q3 plus Q4 losses,
- road plus neutral wins, win share, SOS,
- average NET of wins and of losses (docs/25),
- last-10 win share.

**Composite** = sum of weight × metric, weights 0 to 1. Teams in the field are ordered by the composite, and lines are filled in that order.

**Search,** for each held-out season, fixed now:
- 3,000 random weight sets (random seed 2027), each scored by total exact seeds over the six training seasons, with the actual field given.
- Then 200 rounds of local refinement on the best set: one weight at a time nudged up or down by 0.1, kept if training exact seeds don't drop.

**Scored** on the held-out season with v2.0's selected field:
- **W1:** the composite alone.
- **W2:** half v2.0's rank score, half the composite, each z-scored within the field.

Usual bar against v2.0, plus the owner's standard (75th percentile in all seven). Also reported: the weights chosen in each fold, to show whether they're stable or jump around.
