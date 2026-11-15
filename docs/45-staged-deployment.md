# Before deployment: backups, restore, CPU, the incomplete final, access, and the staged plan

Prepared 2026-11-15:
- **Not done:** nothing deployed, no secrets or tokens created, no Cloudflare settings changed, `public-privacy` not merged, production workflows unchanged.
- **Model:** v2.0 unchanged; no model experiments.

## 1. Automatic private backups (built, tested)
| Layer | What | Where | Kept |
|---|---|---|---|
| Backup database `jbp_backup` | A second D1 database with every record table (reviews, edits, snapshots, verifications, publications). Each run copies only new rows, then checks both copies match: row counts, a SHA-256 over the whole edit log, and every snapshot hash. The result is logged in `backup_runs`. | Your Cloudflare account | **Whole season.** Nothing in it can be updated or deleted (database triggers). A season is about 40 MB of the 500 MB free per database. |
| When it runs | Daily cron (09:23 UTC); after every freeze; whenever you open the page and the last backup is over a day old; and from the "Run the automatic backup now" button | — | — |
| Off-site bundle | "Download full backup" on the Snapshots page: every edit, snapshot, verification and publication as stored, plus the reviews needed to rebuild B3 and both snapshots. The page shows when you last downloaded one and turns red after 7 days. | Your phone/computer | As long as you keep the file |
| D1 Time Travel | Cloudflare's own point-in-time restore of both databases | Cloudflare | 7 days on the free plan |

**Never exposed:**
- Backups never touch GitHub, the public site or Actions logs: no workflow reads or writes them.
- The upload reply that can reach an Actions log is `{"stored": true, "season": 2027, "collected_at": ...}`.

## 2. Restore tested (built, tested)
`review-worker/scripts/restore.mjs` writes a `.sql` file for a new, empty D1 database, from either source:
- `--from-db jbp_backup --remote` (the backup database);
- `--from-bundle <file>` (your downloaded copy).

**Handling D1's limits:**
- D1 caps a statement at 100 KB, so long texts (about 220 KB reviews, large snapshots) are inserted in 20,000-character pieces.
- The append-only triggers are created after the data is loaded.
- The script refuses to write any statement of 100 KB or more.

**Test** (local, simulated season): 11 edits including an undo, a publication, both snapshots, backups. Restored both ways into fresh databases, then compared against the original:
- edits identical: ids, server times, phone times, undo entries;
- B3 identical;
- published lines identical;
- both snapshot hashes identical, and both snapshots verify;
- UPDATE/DELETE blocked again.

## 3. Worker CPU (Workers Free: 10 ms per request or cron run)
**Changes:**
- Engine about 3× faster, with identical results (Python parity on 400 random sequences; chunked = one pass on 150 more).
- Save applies one step instead of replaying twice.
- **Freeze replays in chunks:** each request does at most 150 edits and stores its progress. The timer and the page button repeat until frozen, and the result is identical (tested, including against Python).
- Backups copy at most 3 reviews per run.

**Measured in Node on this machine, real 2027 data (ms):**

| Edits logged | Page load | Save | Undo | Publish | Freeze chunk | Freeze write | Backup check | Bundle |
|---|---|---|---|---|---|---|---|---|
| 50 | 1.3 | 1.2 | 2.2 | 0.8 | 0.5 | 1.1 | 0.1 | 3.6 |
| 150 | 1.9 | 1.2 | 2.9 | 1.4 | 1.2 | 2.3 | 0.3 | 3.3 |
| 300 | 3.1 | 2.2 | 4.4 | 3.0 | 1.2 | 4.2 | 0.4 | 3.5 |
| 500 | 5.4 | 4.0 | 7.0 | 4.0 | 1.1 | 5.7 | 0.6 | 3.6 |

Your 2026 bracket had 23 changes from v2.0; even a heavy season is unlikely to log more than about 300 edits.

**Fallback ladder if Cloudflare's real figures exceed the limit** (measured from Workers Logs in stage 2, free: 0.5 GB/day, 7 days):
1. **Lower the freeze chunk size** (one constant). Freeze work per request has a fixed ceiling at any season length.
2. **B3 checkpoint** (designed, not built): save the bracket after each edit, so Page load, Save and Undo don't replay the log. That makes their work independent of the edit count.
3. **Last resort** if a snapshot still can't be written in time: freeze in Python on your computer from the downloaded bundle (`review freeze`, already tested). Same rules, verifiable hash, but manual.

None of these needs a paid plan.

## 4. Incomplete final: audited and fixed
**Before:** if a conference final wasn't over, the final snapshot fell back to the newest review, marked it incomplete, and the published lines didn't say so. The site would have shown it as final. **Fixed:**

| Rule | Where |
|---|---|
| While any Selection Sunday conference final is in progress (or the scoreboard can't be read), a final freeze returns **"Waiting for conference finals (Purdue vs Michigan)…"**. It's taken incomplete only in the **last 10 minutes before the deadline**. | Worker and Python (same rule; tests) |
| Review page: a red **FINAL SNAPSHOT IS INCOMPLETE** banner on the board and snapshots, naming the games | Page (screenshot 11-12) |
| Published lines carry `complete: false` and the pending games. The public page shows **"Final bracket, frozen before every conference final ended. Still in progress then: … Those automatic bids are projected, not known."** | Worker; branch `public-privacy` |
| The stage-3 workflow publishes the labelled bracket, then **fails a final "alert" step**, so GitHub emails you | `deploy/daily-update.stage3.md` |
| After the final freeze, Publish is refused and the public site shows the final snapshot. Its completeness is always stated. | Worker |

## 5. Access audit (tested)
**Route matrix:** every route × {no token, garbage token, intruder email, service token, owner}. The test reads the route list from the source, so a new route can't be skipped.
- **No token, garbage token, intruder email:** 403 everywhere.
- **Service token:** reaches only `POST /api/machine/review` (upload) and `GET /api/machine/published`. Every owner route returns 403, including state, edits, export, backups, freeze and verify.
- **Owner token:** can't use the machine routes.

**What each public surface can reveal:**

| Surface | The ledger | B2 | Unpublished B3 |
|---|---|---|---|
| Review Worker without your Access login | No (403 on every route; no `workers.dev` or preview URL) | No | No |
| `/api/machine/published` (service token) | No: team and line only (tested for reason, confidence, explanation, shadow, `p_in`, `model_line`) | No | **No: only what you published** (a draft after publishing stays private, tested); after Selection Sunday, the final snapshot's B3 |
| Public site and snapshots (branch) | No (tests) | No | No: built from the published lines only |
| Actions logs | No: only "review built", the upload status and the HTTP code | No | No |

**New this round, Publish:** edits are private drafts until you tap **Publish this bracket**. Before your first publish, the site shows the model.

## 6. Staged deployment
| Stage | What happens | Who | Approvals needed | Done when |
|---|---|---|---|---|
| **1. Private Access + Worker + D1** | You set up Zero Trust (Free), the emailed-code login and the Access app; create two D1 databases; add D1 permission to the existing GitHub deploy token; add three GitHub secrets. I put the database ids into `wrangler.jsonc`, activate `review-deploy.yml`, and it deploys. | You (dashboard, about 20 minutes), then me | **Approval 1:** activate and run `review-deploy.yml` (deploys `jbp-review` and both databases). You create the secrets and edit the token. | `review.jaysbracketplays.com` asks for your email code, then loads; another email is refused; unauthenticated smoke test passes |
| **2. Acceptance on your phone** | You create one Access service token (dashboard) and add three GitHub secrets (`REVIEW_URL`, `CF_ACCESS_CLIENT_ID`, `CF_ACCESS_CLIENT_SECRET`); `MACHINE_CLIENT_ID` is added to the Worker. `review-upload-once.yml` uploads today's review. You try every action on the checklist below. I read CPU times in Workers Logs. | You, then me | **Approval 2:** activate `review-upload-once.yml`; redeploy with `MACHINE_CLIENT_ID` | Checklist passes; maximum CPU per request recorded and under about 8 ms |
| **3. Daily upload + public publishing** | Add the two steps in `deploy/daily-update.stage3.md` to the daily workflow; merge `public-privacy` | Me | **Approval 3:** change `daily-update.yml`; merge the branch | Daily run uploads the review; the site shows your published lines with no private fields; with nothing published, it shows the model |
| **4. Selection Sunday automation + rehearsal** | Timer Worker: service binding to `jbp-review` and the Selection Sunday cron replaced by one line (`deploy/trigger.stage4.js`, simulated in tests); a rehearsal season with dates in December runs the whole day: build → research freeze → verify → waiting for finals → final → publish → incomplete-final case → backup → restore drill | Me, you watch | **Approval 4:** deploy the timer change; add a rehearsal season to `config.js` | Rehearsal passes end to end; you've seen the incomplete-final warning and email |
| Before March | Set the final deadline once you confirm the Matrix collection time; replace `DISPATCH_TOKEN` before 2027-04-30 | You confirm | — | — |

**Stage-2 phone checklist:**
1. Sign in with the emailed code.
2. A second email address is refused.
3. Move, Swap, Add and Remove a team; each preview shows the teams that shift.
4. Save, then Undo.
5. History shows server times.
6. Publish; the site shows it after the next daily build.
7. Download a full backup.
8. "Run the automatic backup now" says the copies match.
9. Sign out (close the browser, or wait 24 h) and you're asked again.
10. Light and dark mode both readable.

**Timing (owner decision, updated 2026-11-15):** the research snapshot is frozen at **12:01 p.m. America/New_York**, never earlier: the Worker and Python both refuse a research freeze before 12:01. The cutoff is a **strict noon** for both collected data and logged edits: an edit logged at 12:00:30 counts only for the final snapshot (tested). Pre-noon reviews are built at 11:01 and 11:41 a.m. ET. `frozen_after_cutoff` is therefore always true for the research snapshot; that's expected. The final competitive snapshot is unchanged.

## 7. Stage 1, step by step in the Cloudflare dashboard (beginner level)
Read-only first: nothing below changes anything until you press a Create, Save or Update button.

**0. Check the cron count (2 minutes).** The free plan allows 5 cron triggers per account, and the review Worker adds 1.
- Go to [dash.cloudflare.com](https://dash.cloudflare.com) → **Workers & Pages**.
- Open each Worker → **Settings** → **Trigger events** and count the cron lines. Today's local configs suggest 3: `jays-bracket-plays-trigger` 2, `running` 1.
- If the total is already 5, tell me. I'll drop the review Worker's own cron; backups still run after freezes, when you open the page, and from the button.

**1. Turn on Zero Trust (Free plan).**
1. In the dashboard sidebar, select **Zero Trust**.
2. Choose a **team name**, for example `jaysbracketplays`. Your login domain becomes `jaysbracketplays.cloudflareaccess.com`.
3. Pick the **Free** plan ($0, up to 50 users).
4. **Cloudflare asks for payment details even on the Free plan.** Its docs say: "If you chose the Zero Trust Free plan, this step is still needed but you will not be charged."
5. Before confirming, check that the summary says **$0**. If any amount other than $0 appears, stop and tell me.

**2. Turn on the emailed-code login.**
- **Zero Trust** → **Integrations** → **Identity providers** → **Add new identity provider** → **One-time PIN** → Save.
- Codes are emailed and expire after 10 minutes.

**3. Protect the review address.**
1. **Zero Trust** → **Access controls** → **Applications** → **Create new application** → **Self-hosted and private** → **Add public hostname**.
2. Subdomain: `review`. Domain: `jaysbracketplays.com`. Leave the path empty.
3. **Access policies** → create a policy:
   - name `Owner only`;
   - action **Allow**;
   - include → **Emails** → your email address.
4. **Login methods:** select **One-time PIN**, and only that.
5. **Session duration:** 24 hours.
6. **Create.**

All Access applications deny everyone not matched by an Allow policy. The Worker also checks your email itself.

**4. Copy two values.** Neither is a password.
- **Team domain:** **Zero Trust** → **Settings** shows the team name; the team domain is `<team name>.cloudflareaccess.com`.
- **AUD tag:** **Zero Trust** → **Access controls** → **Applications** → **Edit** on the review app → **Additional settings** → **Application Audience (AUD) Tag**.

**5. Create the two databases.**
1. In the dashboard sidebar, open **Storage & databases** → **D1 SQL database** (in some layouts it's under **Workers & Pages**) → **Create database**.
2. Name `jbp_private`, location automatic → Create.
3. Repeat with `jbp_backup`.
4. Copy each **Database ID** (not secret; it goes into `wrangler.jsonc`).

Free plan: 10 databases, 5 GB in all.

**6. Let the existing GitHub deploy token manage D1.**
1. Top right → **My Profile** → **API Tokens**.
2. Find the token GitHub uses (stored as `CLOUDFLARE_API_TOKEN`) → **Edit**.
3. Add a permission: **Account · D1 · Edit** → **Continue to summary** → **Update token**.

The token's value doesn't change, so the GitHub secret stays as it is.

**7. Add three GitHub secrets.**
1. github.com → the repo → **Settings** → **Secrets and variables** → **Actions** → **New repository secret**.
2. Add:
   - `REVIEW_ACCESS_TEAM_DOMAIN` (from step 4);
   - `REVIEW_ACCESS_AUD` (from step 4);
   - `REVIEW_OWNER_EMAIL` (your email).

They become Worker secrets at deploy, so your email never appears in the public repo.

**8. Tell me:** the two database ids and "Stage 1 approved." I commit the ids and the `review.jaysbracketplays.com` route, move `review-deploy.yml` into `.github/workflows`, and you press **Run workflow** in the Actions tab (or approve me to). Its last step checks that an unauthenticated request is refused.

**9. Check on your phone.** Open `https://review.jaysbracketplays.com`:
- you should get Cloudflare's sign-in page;
- enter your email, then the code from your inbox;
- the page should load and say "No review uploaded yet" (stage 2 adds one);
- a different email gets "That account does not have access."

**Expected cost: $0 a month.**

| Item | Free allowance | Our use |
|---|---|---|
| Zero Trust (Access, one-time PIN, service token) | 50 users | 1 user, 1 token |
| Workers | 100,000 requests a day; 10 ms CPU per request; 5 cron triggers per account | Tens of requests a day; 1 cron (4 of 5) |
| D1 | 10 databases; 5 GB; 5 million rows read and 100,000 written a day | 2 databases, about 40 MB a season, a few hundred writes a day |
| Workers Logs | 0.5 GB a day, 7 days | Small |
| GitHub Actions | Free for public repos | Same daily run plus about 1 minute |

**On the free plans, exceeding an allowance makes the request fail or stops logging; it doesn't bill.**

## Test totals
- **Worker: 29 of 29 pass** (`cd review-worker && npm test`):
  - auth 7;
  - parity and chunks 3;
  - stage-4 timer simulation 3;
  - end to end 9;
  - pre-deployment suite 7 (route matrix, publish, chunked research freeze, incomplete final, backups, two restores).
- **Python:** 55 on `master`, 60 on `public-privacy`.
