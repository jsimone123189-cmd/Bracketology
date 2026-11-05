# Deployment plan ($0/month, not live)

- **Update:** GitHub Actions, daily November to April, plus a run at the deadline on Selection Sunday. Public repos get free Actions minutes.
- **Hosting:** Cloudflare Workers static assets, free tier, serving one static page (Cloudflare now routes new Pages projects here). No server, no accounts, no ads.
- **Model:** trained locally and saved to models/v2.joblib, which holds fitted weights only. Training data stays local until permissions are confirmed.
- **Failure handling:** retries and cached responses in http.py; if a run fails, nothing is deployed and yesterday's page stays up. GitHub emails the owner on a failed run.
- **Early season:** sitebuild refuses to publish below a median of 15 games per team.
- **History:** each run saves a dated JSON to the public `snapshots` branch, using the same fields as the public page (no third-party metric values). Free, and simpler than D1 for one file a day. The branch step has not run in Actions yet.

## To go live
1. Owner decided (2026-11-05) not to wait for Torvik: use only his public CSVs under robots.txt rules (10-second delay, no .json or time-machine pages), credit and link him, and do not republish his ratings. Warren Nolan email is drafted, unsent as far as known.
2. Owner approves the public page.
3. Add CLOUDFLARE_API_TOKEN (Account > Workers Scripts > Edit) and CLOUDFLARE_ACCOUNT_ID as repo secrets. Worker jays-bracket-plays already exists with a "Coming soon" placeholder.
4. Uncomment the schedule.
5. Add 2027 reclassifying teams to INELIGIBLE_CHAMPS.
