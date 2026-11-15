# What the consistent nine see that v2.0 doesn't

Committed before running. A diagnostic, then at most one feature test.

## Step 1: do their disagreements with v2.0 point toward the committee?
For each team in the actual field, using v2.0's held-out line:
- **Group deviation** = the nine's mean line minus v2.0's line, over members who had the team in their field.
- **Committee deviation** = actual seed minus v2.0's line.

Reported: by season, the correlation between the two, and how often the group's direction matches the committee's when the group moves a team half a line or more.

## Step 2: what explains their deviations?
Spearman correlation of the group deviation with each of these, by season. All are free and known by Selection Sunday.
1. Conference regular-season champion (best conference record, ties included).
2. Conference tournament wins.
3. Lost its first conference tournament game.
4. Total losses.
5. Q3 plus Q4 losses.
6. Power conference.
7. Automatic bid.
8. NET rank minus our rating rank (log).
9. Mean of real KPI and SOR minus NET (log ranks, 2021, 2022, 2023, 2025 only).
10. Last-10 win share.

A characteristic counts as **something they see** only if its correlation with the group deviation has the same sign in at least 6 of 7 seasons (3 of 4 for item 9) and averages at least 0.15 in size, and its correlation with the committee deviation has the same sign on average.

## Step 3: one test
If any characteristic qualifies, the single strongest one (largest mean absolute correlation with the group deviation) gets added to the seed model, with the usual bar and a control that reproduces. Item 9 can't be tested over seven seasons, so it would go to 2027 shadow tracking instead. If nothing qualifies, no test is run and that is reported.
