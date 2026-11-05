# Backtest results (leave-one-season-out, seasons 2019, 2021-2026; 2020 had no tournament)

Scored with the real Bracket Matrix rubric (3*picked + 3*exact + 1*within-one, 68 teams, max 408; verified to
reproduce every site's published score for 2019-2026). Every feature is computed as of Selection Sunday from
games on/before that date; each season is predicted by a model trained only on the other six.

| Method | 2019 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Mean | Picked | Exact |
|---|---|---|---|---|---|---|---|---|---|---|
| V1-proxy (V1 weights, own SOR/Torvik-style ranks) | 296 | 287 | 260 | 260 | 294 | 315 | 294 | 286.6 | 64.0 | 24.6 |
| NET only | 300 | 301 | 275 | 271 | 287 | 314 | 322 | 295.7 | 63.3 | 27.9 |
| WAB only | 265 | 258 | 242 | 247 | 272 | 280 | 266 | 261.4 | 62.0 | 19.3 |
| LogReg + Ridge | 325 | 318 | 315 | 306 | 312 | 324 | 358 | 322.6 | 65.3 | 35.1 |
| GBM + GBM | 318 | 314 | 311 | 301 | 320 | 334 | 341 | 319.9 | 65.0 | 33.7 |
| Ensemble | 323 | 310 | 311 | 311 | 323 | 338 | 364 | **325.7** | 65.4 | 35.9 |

Human reference (Bracket Matrix, same seasons): median site ~341-373, consensus 342-388, winner 355-393.

## What this says (and doesn't)
- The models beat the V1 formula and NET-only out of sample by ~30-40 points. That is a real, out-of-sample gain
  (7 held-out seasons, every season's model never saw it). It is NOT a claim of beating human bracketologists.
- **We are still ~35-60 points below the human median/consensus.** Isolating the problem: with the true 68-team
  field handed to the model, seeding alone tops out near 333 (exact seed ~35/68). The human consensus gets ~50+ exact.
  Field selection (~65.4/68 correct) is close to good; **seeding is the gap**.
- Extra features (SOS, road/neutral wins, last-10, best-win quality) added ~0-4 points: within noise. Stat-only
  features are saturating around ~320-325.
- "V1-proxy" is the V1 formula, not your submitted bracket. Your actual 2026 submission scored 370 while the
  formula-only proxy scores 294 that year, so the 76-pt difference is your manual judgment on top of the sheet.
- Small sample (7 seasons, ~470 at-large decisions/season-pool); all differences of a few points are noise.

## What the missing ~40-60 points likely is (hypotheses, not yet tested)
1. Committee-specific information we don't have: the NCAA's published mid-season "Top 16" reveal (official, free).
2. Committee S-curve/bracketing rules (conference separation, geography) that nudge lines.
3. Crowd information: the Bracket Matrix consensus itself (see decision needed below).
