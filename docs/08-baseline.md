# Frozen baseline: model v2.0

This is the model the site runs. It stays in production until a challenger clears the bar below. Git tag: `model-v2.0`.

## What is frozen
- Weights: `models/v2.joblib`, sha256 `5b5ab24ad90cdedf858f6fea7d59e4e5aa9b402486922712e814c9ae46edde8c`. `tests/test_core.py` fails if the file changes without a version bump.
- Method: `src/bracketology/model.py`. Field: logistic regression (C=.3) averaged with gradient boosting (120 trees, depth 2, learning rate .05, subsample .8), fit on non-champions. Seeds: pairwise logistic regression (C=.1, no intercept, window 16) on the committee's 1-68 order.
- Inputs: NCAA results and arenas, NET, and known auto-bids. No other bracketologist's picks and no Bracket Matrix consensus.

## Reference results
Leave-one-season-out over 68-team seasons, Bracket Matrix scoring, 408 maximum.

| Season | 2019 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Mean |
|---|---|---|---|---|---|---|---|---|
| v2.0 | 335 | 326 | 347 | 344 | 329 | 363 | 356 | 342.9 |

Nested estimate: about 342. Comparison means: T-Rank 348.9, median entrant 354.0, best entrant 374.4. Reproduce with `research/verify_production.py`, which needs the local history files.

Points lost per season (65.1): wrong field 11.1, one line off 39.4, two or more lines off 14.6.

These settings were chosen on the same seasons, so the mean is slightly flattering, and the 76-team format has never been tested.

## Replacing it
Set the test list before running. A challenger needs all of these against v2.0, clustered by season:
- At least +3 mean points.
- Better in at least 5 of 7 seasons.
- No season worse by more than 5 points.

About 45 variants have been tried and none passed (`docs/06-corrections-and-real-benchmarks.md`). The best was +1.3, which chance alone could produce. Don't repeat them without naming a specific flaw in how they were run.

Also report selection Brier score and calibration, bubble ranking accuracy, how often a team misses by two or more lines, mean seed error beyond one line, and pairwise agreement near seed boundaries.

Any change to weights or method needs a new `MODEL_VERSION` and tag.
