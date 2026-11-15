# Private review interface: local build and test results

Built 2026-11-15 under the owner's approval for development (not production). It's local only:
- **Not done:** no credentials created, nothing deployed, Access not configured, no scheduled job changed, nothing merged.
- **Model:** unchanged, and no model experiments were run.

## What was built
**`review-worker/`** is a Cloudflare Worker with a D1 database. It runs locally with `wrangler dev` and a local database copy.

| Part | What it does |
|---|---|
| `src/auth.js` | Checks the Cloudflare Access token on **every** request: RS256 signature against the team's published keys, audience, issuer, expiry, and email equal to the owner's. A service token is accepted only for the two machine endpoints. Any missing setting, a missing or bad token, or an unavailable key list means **403**. |
| `src/index.js` | **Owner:** page, state, preview/save/undo edits, manual backup freeze, verify, export a snapshot, export an edit backup.<br>**Machine:** upload a public-data review; read the published lines (team and line only).<br>**Timer:** freeze/verify through an RPC entrypoint that the internet can't reach.<br>**All writes:** same-origin JSON plus a custom header (blocks cross-site posts).<br>**Headers:** strict CSP, no-store, noindex, no framing. |
| `src/engine.js` | Edit engine ported from Python. It gives **identical** results to `review.apply_edits` (tested on 400 random sequences). |
| `src/freeze.js` | Research and final snapshots with the same rules as Python. The stored text is exactly what was hashed, so an exported snapshot passes `python -m bracketology.review verify`. |
| `migrations/0001_init.sql` | **Reviews, edits and freezes are append-only.** UPDATE/DELETE abort at the database level. Each snapshot type exists once per season. An undo is a new row. |
| `src/page.html` | Phone-first page: seed board → tap a team → bottom sheet with model/shadow/your line, confidence, flags, résumé, neighbours → Move/Swap/Add/Remove, 1-16 line buttons, reason buttons, confidence 1-3, note → **Preview** (lists every team that shifts) → **Save**. Also History (server times, Undo, backup download), Brackets (B1/B2/B3 differences), Changes, Snapshots. Light and dark. |
| `wrangler.jsonc` | `workers_dev` and preview URLs off (they would skip Access). Access settings left **empty**, which refuses everything. The D1 id is a placeholder. |

**Server-side rules:**
- **Timestamps:** every edit is timestamped by the server; the phone's clock is kept only for reference.
- **When edits close:** at the final snapshot or its confirmed deadline. After noon, new edits count for the final only, and the page says so.
- **Early-tap guard:** a freeze is refused more than 30 minutes before its cutoff. A final freeze is allowed earlier only once every conference final is in.

**Python side (`review.py`):**
- The build records the model file fingerprints (`model_files`).
- `review upload` is prepared but not run or wired anywhere.
- `undo_of` names the retracted edit.
- **Bug fixed:** a failed "add" with an invalid line used to remove a team without restoring it, leaving 75. Tested now.

## Public-site privacy (branch `public-privacy`, not merged)
**Removed from live pages and snapshots:**
- `model_line`, `override_reason` and `p_in`;
- the "Edited (model N)" tag, the Model column and the at-large odds;
- the manual-edit notice;
- the low-confidence review list;
- the model bracket, the ranking, overrides and the ledger.

**The published bracket comes from the Worker** as lines only (`data/output/published_2027.json`, fetched by the workflow after approval C). It replaces the public `overrides/` file, which would expose reasons if used.

**What's unchanged:**
- **Historical demo page:** still shows the model's odds for past seasons. There are no edits there.
- **Public "About" page:** still says a person reviews and adjusts the model, without saying which teams.

## Test results
**Python: 55 pass on `master`, 59 on the branch.** That includes:
- the two-snapshot freeze tests;
- the failed-add and `undo_of` regressions;
- 4 public-privacy tests: no private fields in team records or snapshots, published lines rebuilt exactly, bad ones refused, the template never shows edits or odds in a live season.

**Worker: 18 pass** (`cd review-worker && npm test`). Everything runs on this machine.
- **Auth (7):**
  - owner accepted;
  - every missing setting refused;
  - missing, malformed, `alg: none`, HS256, unknown-key and forged-signature tokens refused;
  - wrong audience, wrong issuer, expired and not-yet-valid tokens refused;
  - non-owner email refused;
  - service token only when configured;
  - key source pinned to `*.cloudflareaccess.com`;
  - key server down → refused.
- **End to end, `wrangler dev` with local D1 and a simulated Selection Sunday (10):**
  - no token, bad token, intruder email and forged payload all get 403;
  - a cross-site, form-style or header-less write gets 403;
  - a machine token can't reach owner endpoints, and an owner token can't reach machine endpoints;
  - upload accepted; duplicate, edit-carrying, future-dated and wrong-format uploads refused;
  - preview stores nothing;
  - save uses server time, even when the client sends a fake `at` or `id`;
  - six kinds of invalid edit refused;
  - undo works; undo of nothing is refused;
  - **B1 and B2 unchanged by edits**, and line sizes are kept;
  - **research snapshot:**
    - a freeze at 11:00 ET is refused as too early;
    - at 12:35 it freezes the 10:00 review with only pre-noon edits (the undone swap excluded), and the 12:30 review is refused;
    - B1 and B2 equal the uploaded review;
    - B3 equals the Python engine's result;
    - a second freeze returns the same hash;
    - verify passes;
    - **the exported file passes the Python verifier**;
  - **final snapshot:**
    - refused at 4:45 ET while the Big Ten final is pending;
    - at 5:46 it freezes the 5:20 review (all finals in), including the afternoon edit; the 5:50 review is refused;
    - verify passes;
    - edits are refused afterwards;
    - the research snapshot is untouched;
  - published lines contain only key, team and line, from the final snapshot;
  - edit backup download is owner only;
  - direct SQL UPDATE, DELETE or duplicate INSERT on freezes and edits all fail.
- **Parity (2):** JS = Python on 400 random edit sequences over the real 2027 field (more than 500 applied, more than 50 rejected). The season config matches Python: noon cutoff 16:00 UTC, 76-team lines, final deadline unset.

**Public site, same live data, model-only:** the branch and `master` give the **same 76 teams, lines, overall ranks, regions, bubble, first-out list and warnings**.
- **Private fields:** before, `model_line`, `override_reason`, `p_in`, `model_bracket`, `ranked`, `review`, `overrides` and `ledger` were all present. On the branch, none are.
- **With an owner-adjusted bracket** (Duke moved from 7 to 2, Baylor added): the page reproduces the published lines exactly. No reason, confidence, model line, odds or ledger appears in the page or snapshot, and Duke shows as a plain 2 seed.

**Free-plan CPU** (Workers Free allows 10 ms; measured in Node on this machine, real data, 25 edits):
- **Loading state:** 2.3 ms.
- **Freeze:** 5-6 ms, even with 40 stored reviews. Each review keeps a small (20 KB) "core" copy and its hash, and the freeze stops at the first usable review.
- **Before that fix:** 24-190 ms.
- **Caveat:** Cloudflare's own CPU figure can only be confirmed after deployment.

**Phone screenshots and preview:**
- `private/screens/` holds screenshots at 390×844 (iPhone size), light and dark, plus the public page.
- `private/review_preview.html` is a one-file offline preview: the real page, with the server replaced by an in-memory copy of the engine. Nothing is saved or sent.

## Remaining risks
1. **Cloudflare Zero Trust signup asks for payment details** even on the $0 plan.
2. **CPU on Cloudflare** isn't measured until deployed. If the dashboard shows overruns, the next step is splitting the freeze work; there is no paid plan.
3. **Access misconfiguration:** a route outside Access, or `workers.dev` turned on. The Worker still refuses without a valid token for your email, so the risk is limited.
4. **Your email inbox is the login factor** (emailed PIN). Use two-factor sign-in on the email account and on Cloudflare.
5. **v2.0 is public.** Someone could rerun it and compare with your bracket to infer where you edited. Reasons, confidence, notes and B2 stay private.
6. **A leaked service token** lets someone upload a bogus review (visible to you; uploads with edits or the wrong format are refused) or read the published lines. It gives no access to edits.
7. **Uploads can't be deleted** (immutable). A bad upload is skipped by the checks or simply replaced by a newer one.
8. **D1 Free restore covers 7 days.** Download the edit backup before Selection Sunday.
9. **Conference-final detection** depends on the scoreboard feed production already uses. If it's down, the final snapshot is marked incomplete and falls back to the newest valid review.
10. **Still unconfirmed:** the final deadline (Matrix collection time) and the Matrix's 2027 scoring rules.
11. **`report.py` ledger grading** reads `model_bracket` from public snapshots, which the branch removes. `review.grade` on the private snapshot replaces it.
12. **Not built yet** (needs approval first): the daily workflow upload and published-lines steps, and the timer's Selection Sunday schedule and service binding.

## Production approvals required, in order
| # | What | Who | Credential? |
|---|---|---|---|
| 1 | Create the Zero Trust org (Free plan; asks for payment details). Add an Access application for `review.jaysbracketplays.com` with the emailed-PIN login, a policy allowing only your email, and a 24-hour session. Create one **service token** (for the daily upload). | **You**, in the dashboard | Service token |
| A | Create the D1 database `jbp_private`, apply the migration, and deploy `jbp-review` with the route `review.jaysbracketplays.com` and the Access team domain, AUD, your email and the service-token client ID filled in. Done through a deploy workflow, not by hand. | Approval | none new |
| B | Store the service token as GitHub Actions secrets (`CF_ACCESS_CLIENT_ID`, `CF_ACCESS_CLIENT_SECRET`) | Approval | stores #1 |
| C | Daily workflow: after the projection, `review build` → `review upload`; before the site build, fetch the published lines | Approval (workflow change) | uses B |
| D | Merge branch `public-privacy` | Approval | — |
| E | Timer Worker: a service binding to `jbp-review`, and the Selection Sunday cron replaced by `*/5 15-22 14 3 *` (still 3 of 5) to run build, research freeze and verify, then poll the finals, run the final build and freeze, and publish | Approval (scheduled job) | none new (reuses `DISPATCH_TOKEN`) |
| F | Set the final deadline in `config.js` and `FINAL_DEADLINE_ET` once you confirm the Matrix's final collection time | You confirm | — |
| G | Mid-December dress rehearsal on the deployed system, using a test season | After A-E | — |
