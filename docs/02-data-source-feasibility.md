> **Superseded in part by docs/06-corrections-and-real-benchmarks.md.**

# Phase 2 — Data-source feasibility (probed 2026-11-05)

Method: fetched each site's robots.txt and live-tested the endpoint from this machine. "Verified" = I got real data back. Terms-of-service pages were NOT read for every site; where only robots.txt was checked, that is stated. Nothing here bypasses a login or paywall.

| Need | Source | Status | Notes |
|---|---|---|---|
| NET rank, record, **combined** Quad 1/2/3/4 W-L, road/neutral/home | NCAA NET page on ncaa.com, via the open-source `ncaa-api` (henrygd) wrapper | **Verified** (returned 2026 NET through Apr 6) | ncaa.com robots.txt does not block /rankings. Public wrapper: 5 req/s/IP, self-hostable. Unofficial wrapper → can break; we'll cache raw responses and fall back to parsing ncaa.com directly. |
| **Quad 1A** and Q1/Q2 "n/a" splits | **Computed by us** from game results + NET + location | Feasible | NET feed gives only Q1–Q4 totals. Q1A (home 1-15, neutral 1-25, away 1-40) must be derived from per-game data. |
| WAB, SOS, NCSOS, Barthag, adj. efficiency (Torvik) | barttorvik.com `{year}_team_results.csv` | **Verified**, 2019 & 2025 & 2026 return 200 | robots.txt: `Crawl-Delay: 10`; disallows `/*.json`, time-machine, box pages — we use only the CSV, one request per run, 10 s spacing, descriptive User-Agent, cache. No explicit license found: attribute Torvik on the site; consider emailing him for permission (recommended before launch). |
| Game results, locations, opponents | Torvik `getgamestats.php?year=Y&csv=1` | **Verified** 200 | Same politeness rules. Alternative: Kaggle MMLM results (1985+), free but needs a Kaggle login/terms acceptance. |
| **SOR** (ESPN) | ESPN | **Not available legitimately** | espn.com/robots.txt blocks AI crawlers; no public API. **Alternative:** compute our own SOR-style metric (win prob. of a reference "average bubble team" over this team's schedule, using Torvik ratings). Not identical to ESPN's SOR; V2 uses ours. |
| **KPI** | kpiratings.com | Not verified / no API | Proprietary; skip. Our résumé metric above replaces it. |
| **KenPom** | kenpom.com | **Paid** ($95/yr API; robots.txt asserts content-signal restrictions) | Excluded per your rule. Torvik adj. efficiency is the free substitute (≈0.98 correlated). |
| NET team sheets (full) | NCAA | Public sheets are reduced since 2020-21 | We rebuild the same content from the data above. |
| Conference standings / tourney results | Torvik games CSV, NCAA | Feasible | Auto-bid winners derived from conference-tournament final results. |
| **Historical NET at each Selection Sunday** (needed for honest backtests) | Internet Archive Wayback snapshots of the ncaa.com NET page (CDX index lists captures from 2019) | Feasible, **needs validation** | NET exists only since 2018-19 → at most ~7 training seasons (2019, 2021–2025 + 2026; 2020 had no tournament). Small sample: must use heavy regularization and report wide uncertainty. |
| Historical Torvik at the cutoff | Torvik time-machine pages | **Disallowed by robots.txt** | Do not scrape. Alternative: reconstruct as-of ratings ourselves from game results through the cutoff date (leak-free by construction) or use only the final-season CSV with games truncated at Selection Sunday. |
| **Truth labels**: actual field, seeds 1–68 | Kaggle MMLM seeds (free, login) / Wikipedia season pages (CC BY-SA) | Feasible | Wikipedia is the no-login route. |
| **Bracket Matrix scoring rules and historical submissions** | bracketmatrix.com | **Unreachable from here** (no HTTP response, possibly blocks this host) | Need exact scoring rules from you or the site's FAQ; I won't guess. Please paste the scoring rules (and the 393 winner's points breakdown if you have it). |

## Key consequences
1. Fully automated, $0, permitted-access collection is feasible for NET + quad totals + Torvik metrics + games.
2. SOR, KPI, KenPom cannot be pulled legitimately for free → V2 uses computed substitutes and says so on the methodology page.
3. The biggest accuracy risk is **sample size**: ~6–7 seasons of NET-era data. A model with 20+ features will overfit. Plan: tiny feature set, regularized logistic for selection, ordinal/ridge for seed, compared against your V1 weights under leave-one-season-out. No improvement claimed without out-of-sample evidence.
4. Your V1 inputs (WAB, SOR, NET, Torvik, Q-records) are re-creatable except SOR.

## Needed from you (essential only)
- Bracket Matrix scoring formula (and ideally last year's final-field/seed list you submitted so I can score V1 for real).
- OK to email Bart Torvik asking permission/attribution terms? (I'll draft it; you send it.)
