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

---
# Update: Bracket Matrix consensus as an input (pre-selection, public)

Consensus = average seed and number of brackets listing each team on the final Matrix page (includes "Other At-Larges").
Training/evaluation unchanged (LOSO, same rubric).

| Method | 2019 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 | Mean | Picked | Exact |
|---|---|---|---|---|---|---|---|---|---|---|
| Stats-only ensemble (independent) | 323 | 310 | 311 | 311 | 323 | 338 | 364 | 325.7 | 65.4 | 35.9 |
| Consensus only, capacity-slotted | 342 | 358 | 357 | 366 | 339 | 355 | 384 | 357.3 | 66.7 | 46.7 |
| **Consensus only, rounded avg seed** | 359 | 367 | 362 | 369 | 346 | 366 | 388 | **365.3** | 66.7 | 50.3 |
| Stats + consensus ensemble (slotted) | 363 | 363 | 370 | 356 | 337 | 362 | 392 | 363.3 | 66.7 | 49.7 |
| Stats + consensus ensemble (rounded) | 359 | 342 | 352 | 346 | 347 | 358 | 381 | 355.0 | 66.7 | 45.3 |

Findings
1. Consensus is worth ~+40 points over stats-only (326 -> 365): the crowd carries committee knowledge our stats lack.
2. **Stats add nothing on top of the consensus.** A ridge on stats predicting (true seed - consensus avg), swept over
   alpha {30,100,300} and shrink {0,.5,1}, scored 363-366 in every setting vs 365.3 for pure rounding. No evidence the
   stats model improves on the consensus; do not claim it does.
3. The best honest configuration is therefore ~ the consensus (~365 mean; Matrix human median ~360). That is roughly
   the 50th-85th percentile depending on the year, NOT a top-ranked finish. Winners (355-393) are the luckiest of
   ~250 brackets, so a consensus-level bracket should typically land in the top ~15-30% and only sometimes top 5.
4. Where points are lost (consensus-rounded, 7 seasons, ~43 pts/season): seed lines 8-11 = 48% (the 11-line alone 16%,
   First Four teams); lines 1-4 = 9% (~4 pts/season).

## Decision: NCAA Top-16 reveal NOT built
Lines 1-4 account for only ~4 points/season of consensus error, and the reveal is a month stale (and published only
as prose articles, one per year, so extraction is brittle). Upper bound on benefit <= ~4 pts/yr, likely ~1. Not worth it.

## Caveats
- Independence: Matrix sites (including ours, once submitted) feed the consensus; a model that leans on it is partly
  a copy of the crowd and cannot beat it by construction on information alone.
- The consensus is only available from the live Matrix page in-season; the daily pipeline would need to fetch it
  (http://bracketmatrix.com/ only; https fails). Confirm the site is OK with automated reads before relying on it.
