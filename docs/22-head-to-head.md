# Head-to-head results in seeding

Committed before running. The NCAA's selection and seeding criteria name head-to-head results, and the committee builds its seed list by comparing small groups of nearby teams. v2.0 scores each team on its own numbers, so it can't use a result between two specific teams.

## Test 9
- **Pair feature `h2h`:** for teams i and j, i's wins over j minus j's wins over i, in D-I games through Selection Sunday (0 if they didn't play). It's added to each ranking pair next to v2.0's feature differences. The flipped pair gets the negative value.
- **Same training otherwise:** pairs within 16 overall positions, the same logistic ranking settings.
- **Ordering:** a pair feature means teams can't be scored one at a time. Each field team's score is its mean predicted chance of ranking above every other field team, then lines are filled in that order.
- **Reference, reported but not judged:** the same mean-chance ordering without `h2h`. It separates the ordering method from head-to-head.
- **Judged:** Test 9 against v2.0 with the usual bar. Also reported: percentile each season, whether it reaches the 75th in all seven, exact seeds, and how many pairs in each held-out field met during the season.
