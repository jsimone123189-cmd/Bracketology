# Habits the committee states in public

Committed before running. Source: ESPN, Jeff Borzello, "6 key takeaways from a mock Selection Sunday exercise," Feb. 24, 2026. Three statements are specific enough to test. Each test is judged separately against v2.0, usual bar, with percentile and the 75th-in-all-seven check reported.

**Test 14: head-to-head depends on location.** "It's still only one data point, and one has to consider other factors, such as the location of the game." docs/23's pair features (`h2h`, `common`) are rebuilt with each game weighted by venue, using the NCAA's own RPI weights: road win 1.4, neutral 1.0, home win 0.6, and the mirror image for losses. Same training and ordering as docs/23.

**Test 15: close losses to strong teams count.** Houston got the final 1-seed partly for losses to highly regarded teams "by a combined 10 points." **`q1_loss_margin`** = mean margin of the team's Quadrant 1 losses (0 if none). It goes into the seed model as `z_q1_loss_margin`, where a smaller margin is better.

**Test 16: double champions get deference.** The committee "has historically shown deference to teams that win both the regular-season and conference-tournament titles." **`double_champ`** = 1 if the team had the best regular-season conference record (ties included) and won its conference tournament. It goes into the seed model.

## Results (2026-11-14): none passed
The control reproduced in each run.
- **Test 14, location-weighted head-to-head and common opponents:** 335 330 347 348 325 363 359. Mean +1.0, better in 3, worse in 1, worst -4. About the same as unweighted (docs/23, +1.6). `research/weighted_h2h_output.txt`.
- **Test 15, Q1 loss margin:** 335 326 343 348 329 359 356. Mean -0.6. `research/committee_habits_output.txt`.
- **Test 16, double champion:** 335 324 347 344 329 357 352. Mean -1.7, better in 0. 10-20 double champions per field.

## Injury and availability news
No free, automatic source with history turned up:
- The open NCAA wrapper has no injury route.
- The free API tiers found either list no injury data or need keys.
- The injury report pages found (e.g. Rotogrinders) are web pages with unconfirmed terms and no archive.

The box-score availability measure (docs/10) remains the only legal automatic proxy, and it failed. A prospective injury feed would need a source the owner approves.
