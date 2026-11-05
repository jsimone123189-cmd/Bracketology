# Deployment plan ($0/month, not live)

- **Update:** GitHub Actions, daily November to April, plus a run at the deadline on Selection Sunday. Public repos get free Actions minutes.
- **Hosting:** Cloudflare Pages free tier serving one static page. No server, no accounts, no ads.
- **Model:** trained locally and saved to models/v2.joblib, which holds fitted weights only. Training data stays local until permissions are confirmed.
- **Failure handling:** retries and cached responses in http.py; if a run fails, nothing is deployed and yesterday's page stays up. GitHub emails the owner on a failed run.
- **Early season:** sitebuild refuses to publish below a median of 15 games per team.
- **Not built:** daily snapshot history (D1 or similar). Today each run's data is lost in CI.

## To go live
1. Torvik and Warren Nolan reply.
2. Owner approves the public page.
3. Add CLOUDFLARE_API_TOKEN and CLOUDFLARE_ACCOUNT_ID as repo secrets; create the Pages project.
4. Uncomment the schedule.
5. Add 2027 reclassifying teams to INELIGIBLE_CHAMPS.
