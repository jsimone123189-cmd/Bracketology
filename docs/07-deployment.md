# Deployment plan ($0/month, not live)

- **Update:** GitHub Actions, daily November to April, plus a run at the deadline on Selection Sunday. Public repos get free Actions minutes.
- **Hosting:** Cloudflare Workers static assets, free tier, serving one static page (Cloudflare now routes new Pages projects here). No server, no accounts, no ads.
- **Model:** trained locally and saved to models/v2.joblib, which holds fitted weights only. Training data stays local until permissions are confirmed.
- **Failure handling:** retries and cached responses in http.py; if a run fails, nothing is deployed and yesterday's page stays up. GitHub emails the owner on a failed run.
- **Early season:** sitebuild refuses to publish below a median of 15 games per team.
- **History:** the schedule is on. Each run saves one timestamped JSON to the public `snapshots` branch, with a snapshot ID, model version, the untouched model bracket, all teams ranked, overrides, and source details. No third-party metric values. A later run never overwrites an earlier one.
- **Public switch:** the bracket deploys only when the repository variable `PUBLISH_BRACKET` is `true`. It is unset, so the page stays on Coming Soon even after the 15-game guard clears.

## To go live
1. Owner decided (2026-11-05) not to wait for Torvik: use only his public CSVs under robots.txt rules (10-second delay, no .json or time-machine pages), credit and link him, and do not republish his ratings. Warren Nolan email is drafted, unsent as far as known.
2. Owner approves the public page.
3. Domain jaysbracketplays.com (Cloudflare Registrar, paid by owner). Add CLOUDFLARE_API_TOKEN (the "Edit Cloudflare Workers" template, zone jaysbracketplays.com) and CLOUDFLARE_ACCOUNT_ID as repo secrets. Worker jays-bracket-plays already exists with a "Coming soon" placeholder.
4. Set the repository variable `PUBLISH_BRACKET` to `true` (Settings > Secrets and variables > Actions > Variables).
5. Add 2027 reclassifying teams to INELIGIBLE_CHAMPS.

## Data sources in production (updated)
Torvik returns HTTP 403 to GitHub Actions. Live runs use NCAA results and arenas (neutral games inferred from the home team's usual arenas), the NCAA NET, and Warren Nolan's table and auto-bids.
Tested on 2026 only: same score as Torvik's log (356), WAB/SOR/rating Spearman .999 for NET<=90; neutral games found 81% of the time, with 62 of about 9,900 non-neutral team-games wrongly marked neutral. The saved game file lives on the public `snapshots` branch.
