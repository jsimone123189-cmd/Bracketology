# Habits the committee states in public

Committed before running. Source: ESPN, Jeff Borzello, "6 key takeaways from a mock Selection Sunday exercise," Feb. 24, 2026. Three statements are specific enough to test. Each test is judged separately against v2.0, usual bar, with percentile and the 75th-in-all-seven check reported.

**Test 14: head-to-head depends on location.** "It's still only one data point, and one has to consider other factors, such as the location of the game." docs/23's pair features (`h2h`, `common`) are rebuilt with each game weighted by venue, using the NCAA's own RPI weights: road win 1.4, neutral 1.0, home win 0.6, and the mirror image for losses. Same training and ordering as docs/23.

**Test 15: close losses to strong teams count.** Houston got the final 1-seed partly for losses to highly regarded teams "by a combined 10 points." **`q1_loss_margin`** = mean margin of the team's Quadrant 1 losses (0 if none). It goes into the seed model as `z_q1_loss_margin`, where a smaller margin is better.

**Test 16: double champions get deference.** The committee "has historically shown deference to teams that win both the regular-season and conference-tournament titles." **`double_champ`** = 1 if the team had the best regular-season conference record (ties included) and won its conference tournament. It goes into the seed model.
