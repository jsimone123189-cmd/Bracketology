# RPI (from dRatings' method) and dRatings' own errors

Committed before running.

## Why dRatings
Matrix entry DII is dRatings.com. It is the most consistent model-based entry: 7 of 7 seasons, averaging the 81st percentile, never below the 67th. Torvik's T-Rank averages the 42nd and TeamRankings the 3rd. Its page says the bracket comes from "a combination of variables including our own NCAA college basketball ratings, RPI, strength of schedule (SOS), and few other factors." v2.0 already has its own rating and SOS. The RPI is what's missing.

## Test 5: RPI
- **RPI,** computed by us from D-I game results through Selection Sunday, the NCAA's long-standing formula: 0.25 × weighted win share (home win 0.6, road win 1.4, home loss 1.4, road loss 0.6, neutral 1.0) + 0.50 × opponents' win share (each opponent's games against this team removed) + 0.25 × opponents' opponents' win share.
- Added as `z_rpi` (z-scored like v2.0's other features) to **both** the field and seed models. dRatings uses it for both.
- Leave-one-season-out, control reproduces, usual bar. Also reported: percentile each season and whether it reaches the 75th in all seven.
- **Sanity check, reported:** rank correlation of our RPI with NET among NET top 100.

## dRatings' errors (diagnostic)
From its Matrix brackets, over the actual field, by season: exact seeds, mean signed and absolute error for power at-large, non-power at-large and automatic bids, error by line band, and wrong teams (via `research/matrix_full.py`). The same measures are shown for v2.0. Also: the teams where v2.0 was exact and dRatings was not. Any improvement idea needs its own committed test. dRatings' brackets are never an input.

## Results (2026-11-14)
`research/rpi_dratings_output.txt`.
- **Test 5, RPI, failed:** 328 329 334 340 335 364 364. Mean -0.9, better in 4, worse in 3, worst -13. Our RPI's rank correlation with NET (top 100) was 0.71-0.85.
- **dRatings against v2.0, seven-season means:**
  - exact seeds 49.0 against 41.6,
  - wrong teams 1.14 against 1.86,
  - exact rate by line band: lines 1-4 0.89 against 0.72; 5-8 0.54 against 0.43; 9-12 0.71 against 0.60; 13-16 0.79 against 0.75,
  - non-power at-large error 0.43 against 0.78 (signed -0.05 against +0.38),
  - automatic bids 0.24 against 0.39.
- v2.0 was better than dRatings only in 2025, by 1 point.
