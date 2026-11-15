# Learning dRatings' seeding style from free stats

Committed before running. The owner asked to reproduce the consistent bracketologist who uses real data (dRatings, DII), then improve on its errors. dRatings publishes its inputs only in general terms. Its full brackets for 2019 and 2021-26 are on the Matrix pages. So v2.0's seed model is trained to reproduce its order from our free stats.

**What this is and isn't:**
- **Training:** dRatings' historical lines are used only as training labels.
- **Live:** the model sees only free, automatic stats, the same inputs as v2.0. No live dRatings data is ever read.
- **Backtest:** for each held-out season, the model trains only on the other seasons' labels.
- This is a change to the owner's no-other-bracketologists rule, made at the owner's request to reproduce one. It is labelled here so it can be reversed.

**Selection** stays v2.0's. Only seeding changes. Inputs are v2.0's seed features.

- **T8a, dRatings order:** ranking pairs from dRatings' lines for teams in both its field and the actual field, in pairs 1 to 4 lines apart (v2.0 uses pairs within 16 overall positions, about 4 lines). Same ranking model and settings as v2.0.
- **T8b, committee plus dRatings:** v2.0's committee pairs plus T8a's pairs, equal weight. dRatings' habits are kept where they agree with the committee and outvoted where they don't.

Usual bar against v2.0, and the owner's standard: 75th percentile or better in all seven seasons. Also reported for each season: exact seeds, exact on lines 1-4 and 5-8, and how often T8a matches dRatings' line, which shows how reproducible its style is from free stats.

## Results (2026-11-14): both failed
`research/learn_dratings_output.txt`. The control reproduced.
- **T8a, dRatings order:** 322 322 343 341 331 368 344. Mean -4.1, better in 2, worse in 5.
- **T8b, committee plus dRatings:** 332 326 343 344 328 363 351. Mean -1.9, better in 0.
- **Our free stats reproduce dRatings' exact line only 55-73% of the time** (59, 55, 59, 61, 70, 73, 64). Much of its bracket comes from information outside our stats: its own power rating, judgment, or the crowd.
- Archived copies of its ratings near Selection Sunday exist only for 2021, so its rating can't be studied over seven seasons.
