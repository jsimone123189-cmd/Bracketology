# Adding 2014-18 to training, with the RPI in NET's place

Committed before running.

**Named flaw in the earlier test** (docs/06, -3 to -4): NET didn't exist before 2018-19, so those seasons used our own rating rank in NET's place. That also made the quadrant records use our rating. In those years the committee sorted and built quadrants by the RPI.

**Fix:**
- For 2014-18, compute the RPI from game results through Selection Sunday (docs/18 formula) and use its rank in NET's slot.
- Recompute every NET-based feature with it: quadrant records, NET-related features and the rest, using the same metrics code as 2019-26.
- Team matching as in `research/common.py`. The number of field teams matched each season is reported.

**Training:**
- **Seeding:** the committee's 1-68 order isn't held for 2014-18, so pairs come from seed lines: teams 1 to 4 lines apart, ranked by line. 2019-26 keep v2.0's 1-68 pairs.
- **Selection:** 2014-18 rows join the field model.

**Test 12:** 2014-18 added to both the field and seed training. Leave-one-season-out over 2019 and 2021-26 only, so 2014-18 is always training and never scored. Usual bar, percentile each season and the 75th-in-all-seven check.

**Reported, not judged:** 2014-18 added to seeding only.

## Result (2026-11-14): failed
`research/more_seasons_rpi_output.txt`. The control reproduced. 64-67 of 68 field teams were matched each season, 2014-18.
- **Test 12, both models:** 325 320 342 338 332 353 364. Mean -3.7, better in 2, worse in 5, worst -10.
- **Seeding only:** 330 320 342 338 328 359 364. Mean -2.7, better in 1.

Even with the RPI in NET's place, pre-NET seasons make the model worse. That supports the committee having changed with NET, and possibly again around 2025. Older seasons teach habits it no longer has.
