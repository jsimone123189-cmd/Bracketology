# 2027 review workflow: two snapshots, private saving, threat model, plan

Written 2026-11-15. Nothing here has been deployed, no tokens were created, and no crons were changed. No model tuning.

**The 2026 baseline:**
- **Use:** the owner's genuine 2026 submission scored **370**, against v2.0's **356**.
- **Don't use:** the 377 demo replay (hindsight-picked moves). It's not evidence of anything.

## 1. Two Selection Sunday snapshots (built and tested locally)
| | Research snapshot | Final competitive snapshot |
|---|---|---|
| Purpose | 2027 evaluation (docs/38) | The bracket actually submitted |
| Cutoff | Noon America/New_York (16:00 UTC on March 14, 2027) | `FINAL_DEADLINE_ET[2027]`. It's empty until the deadline is confirmed, and the freeze refuses to run while it's empty. |
| Which review | Newest valid review collected before noon | Newest valid review collected **after every Selection Sunday conference final ended**, and before the deadline. If none qualifies, the newest valid review is used and marked `final_results_complete: false`, with the games that were still pending. |
| Contents | B1, B2 and B3 in full, inputs, model fingerprints, edit history | The same |
| File | `2027_freeze.json` | `2027_final_freeze.json` |

**Shared rules:**
- **Immutable:** each file is created once, is read-only, and has a `.sha256` sidecar; re-running returns `already_frozen`.
- **Edit cutoff:** a review that applied an edit logged after its cutoff can't be frozen.
- **Verification:** `review verify 2027 research|final` re-checks the hash, the cutoff (which must equal the configured one), the kind, field size and line sizes, any late edits, and that the model is exactly the saved v2.0.

**How "finals over" is decided (never from a clock):**
1. Before collecting data, the build reads the scoreboard feed production already uses and lists that day's conference-tournament games that aren't final.
2. `[]` (complete) is recorded only if no game was pending **and** every one of those games is in the game list the model used.
3. If the feed can't be read, or a result is missing from the data, the status is recorded as unknown, which counts as not complete.

**Tests:** 53 pass. Six are new:
- the deadline refuses until it's set, and New York time converts correctly;
- the final freeze waits for the finals and refuses post-deadline data;
- the fallback is marked incomplete;
- the two files are independent and both read-only;
- a late edit blocks a review;
- the completeness cross-check works.

The 2026 demo is unchanged (356 / 346 / 377).

## 2. Deadlines and schedule: what's known and what isn't
- **Selection Sunday 2027:** March 14. 76-team brackets are revealed that day ([NCAA.com](https://www.ncaa.com/news/basketball-men/article/2026-08-12/2027-selection-sunday-date-schedule-tv-times-march-madness)). The 2027 show time isn't announced; in 2026 it was 6 p.m. ET.
- **Sunday conference finals (actual scoreboard data):**
  - **2025 and 2026:** five each: Ivy (12:00), A-10 (1:00), SEC (1:00), American (3:15) and Big Ten (3:30 p.m. ET). The last one ends around 5:30 p.m. ET, about 30 minutes before a 6 p.m. reveal.
  - **2027:** the schedules aren't published yet.
- **Bracket Matrix deadline:** not documented. The 2027 Matrix page states no submission rule, and I found none published. The only certain hard stop is the bracket reveal; the Matrix's final collection time is unknown.
  - **Action:** you ask the Matrix maintainer when they take final brackets. I can draft that email for you.
- **Rule:** `FINAL_DEADLINE_ET[2027]` is set only from confirmed times. It must be early enough that build, freeze and publish (about 10 minutes) finish before the Matrix's final collection.

## 3. Easier private editing
**Today:** Copy JSON → paste into a file → commit. That's unusable on a phone.

**Proposed:** open `review.jaysbracketplays.com` on the phone, enter the emailed PIN, tap a team, pick a line, reason and confidence, then tap **Save**. The edit is stored at once, with a timestamp set by the server (not the phone). The page reloads B3. There's no JSON handling.

## 4. Threat model
**What needs protecting:**
- the edit ledger (reasons, confidence, notes);
- B2 and B3 before publication;
- integrity of both freezes (no backdating, no post-cutoff data).

**Attackers:**
- the public (they can read the public repo, the snapshots branch, Actions logs and the site);
- a stolen device or session;
- a leaked secret;
- the owner's own misclicks.

**Facts checked against official docs (2026-11-15):**
- **Cloudflare Zero Trust Free plan:** $0 for up to 50 users, with 24-hour logs ([plans](https://www.cloudflare.com/plans/sase-zero-trust.md)). **However, Cloudflare's setup guide says onboarding asks for a plan selection and "payment details" even on Free.** A card on file is likely, at $0 charge.
- **One-time PIN login:** built in. Codes expire after 10 minutes.
- **Access JWT:** Access adds a `Cf-Access-Jwt-Assertion` header. Cloudflare recommends that the app validate it.
- **Workers Free:**
  - 5 cron triggers per account; the local configs for this account use 3 (`trigger`: 2, `running`: 1), not checked against the dashboard;
  - 10 ms CPU per invocation.
- **D1 Free:** 100,000 rows written and 5 million read per day, 5 GB storage, Time Travel restore 7 days. Exceeding a limit fails the query; it never bills.
- **GitHub Free:**
  - private repos get $12 a month of Actions compute (about 2,000 Linux minutes; the daily build uses about 2 minutes);
  - **private GitHub Pages needs an organization account**, so A has no private page host.

| Threat | A: private GitHub repo plus manually saved edits | B: Cloudflare Access + Worker + D1 |
|---|---|---|
| Ledger read by the public | Safe while the repo stays private. Risk: someone flips the repo to public, or a fork. | Never leaves Cloudflare. The Worker returns it only after Access login **and** its own check of the JWT and your email. |
| Where the page lives | Nowhere private and free (no private Pages). Download the HTML or use a claude.ai artifact. | `review.` subdomain behind Access |
| Mobile saving | Edit JSON on github.com, or put a GitHub token in the phone browser (long-lived token on the device) | Save button. No token on the device; the session expires. |
| Backdating or post-cutoff edits | Commit time is trustworthy, but the timestamp inside the JSON is typed by you | Server-set timestamps. The Worker refuses edits after each cutoff. |
| Freeze immutability | File permissions plus a hash in a private repo (you could rewrite git history) | Insert-only table (update/delete triggers abort), plus the hash **published** at freeze time |
| Credentials to manage | Token A (Cloudflare → private repo Actions) plus token B (private repo → public repo contents). Two GitHub tokens with write access. | One random shared secret, scoped to "upload public-data review" and "read published lines". It's not a GitHub token. The existing `DISPATCH_TOKEN` is reused through a service binding, not copied. |
| Leaked secret | Token B could write to the public repo, including the site | Shared secret: could upload a fake review (caught by fingerprint checks and visible to you) or read lines that are public anyway. No ledger access. |
| Misconfiguration bypass | n/a | Real risk: a `workers.dev` or preview URL would skip Access. Mitigations: both disabled, plus JWT validation inside the Worker so it fails closed. |
| Account takeover | GitHub account | Cloudflare account, plus your email for PINs. Use 2FA on both. |
| Cost or limits | $0 within Actions minutes | $0 within the free limits above. Card possibly required at Zero Trust signup. |
| Moving parts | Second repo, two tokens, cross-repo pushes | One new Worker, one D1 database, one Access app |

**Recommendation: B.** It's the only option that gives you a private, phone-friendly page with no GitHub token on your phone. It also has fewer write-capable credentials than A, and it adds server timestamps and a public hash commitment, which A lacks.
- **Condition:** you accept Cloudflare's payment-details step for the $0 Zero Trust plan.
- **If you won't add a card:** fall back to A, with editing on github.com.

**Limit for both options:** v2.0's code, weights and data sources are public. Someone determined could rerun v2.0 and compare it with your published bracket to infer where you edited. Only making the main repo private prevents that. Reasons, confidence, notes and B2 stay private either way.

## 5. Public site shows only the published bracket (needs approval)
**Leaks found today:**
- each team's public JSON carries `model_line` and `override_reason`;
- the template shows an "Edited (model N)" tag;
- `p_in` (the model's odds) on an edited team reveals the disagreement;
- the low-confidence "review" list is published;
- the public `snapshots` branch stores `model_bracket`, `overrides`, the ledger and `ranked`.

Nothing has leaked yet: `overrides/` is empty.

**Change:**
- Public JSON and snapshots keep: team, line, overall, region, play-in, champion/auto flag, and record/NET/WAB/SOR/SOS/last-10.
- Drop: `model_line`, `override_reason`, `p_in`, the review list, the model bracket, the ledger and the ranking.
- Bubble lists are computed from the published order.
- Model-only data moves to D1.
- Public snapshots also carry the two freeze hashes.

## 6. Three tracks preserved
- **B1 (frozen v2.0)** and **B2 (shadow)** are built daily from public data.
- **B3** is B1 plus your edits as of each cutoff.
- Both freezes hold all three. Grading is unchanged (docs/38 rules).

## 7. 2027 format and scoring
- **Format:** `FORMAT_76`: lines of 4 × 10, then 6, 8, 4, 4, 6, 8 (76 teams, 32 automatic, 44 at-large; extra play-in teams on lines 11, 12, 15 and 16).
- **Checks:** both freezes reject any bracket whose size or line sizes differ. A test covers it.
- **Scoring:** the Matrix rubric is 3 per team, plus 3 for the exact line or 1 for one off. The maximum is 456.
- **Not yet confirmed:** the Matrix hasn't posted 2027 scoring rules. If it changes the rubric for 76 teams, only `bm.score` changes; the rubric is parameterized and the freeze isn't affected.

## 8. Implementation plan
| # | Step | Production? | Needs |
|---|---|---|---|
| 1 | Two-snapshot freeze, completeness check, edit-cutoff check (done, local) | No | — |
| 2 | Build the review Worker locally: Access JWT check, D1 schema (append-only edits, insert-only freezes), Save API, the page served from D1, JavaScript freeze with a test that it matches Python; tested with `wrangler dev` | No | Nothing. I can start now. |
| 3 | Public-site privacy change on a branch, with a diff for you to review | No (branch) | Nothing to build. Approval to merge. |
| 4 | Create the Zero Trust org (Free) and an Access app for `review.jaysbracketplays.com`: one-time PIN, allow only your email, 24-hour session | Yes | **You**, in the dashboard (it asks for payment details) |
| 5 | Create the D1 database `jbp_private` and deploy the review Worker (`workers_dev` and previews off) through a workflow, not by hand | Yes | **Approval A** |
| 6 | Generate the shared secret and store it as a Worker secret plus a public-repo Actions secret | Yes | **Approval B** |
| 7 | Daily workflow: upload the review to the Worker; the site build pulls the published lines | Yes (workflow) | **Approval C** |
| 8 | Merge the public-site privacy change | Yes | **Approval D** |
| 9 | Trigger Worker: replace the Selection Sunday cron with one expression, `*/5 15-22 14 3 *` (still 3 of 5 crons), and add a service binding to the review Worker. It runs build at 15:30 UTC; research freeze at 15:40 (retry 15:55); verify at 16:05; then polls finals and runs the final build, freeze and publish. | Yes | **Approval E** |
| 10 | Set `FINAL_DEADLINE_ET[2027]` from the confirmed show time and the Matrix's answer | Config | **You**: confirm the Matrix collection time |
| 11 | Dress rehearsal in mid-December: a fake Selection Sunday with a test season, both freezes, verify, publish, then a restore test | No | — |
| 12 | Replace `DISPATCH_TOKEN` before 2027-04-30; add 2027 `INELIGIBLE_CHAMPS` | Yes | Later |

**Timeline:**
- Steps 2-3 by early December.
- Steps 4-9 after your approvals.
- Rehearsal mid-December.
- January to Selection Sunday: daily use.

Sources:
- [Cloudflare Zero Trust plans](https://www.cloudflare.com/plans/sase-zero-trust.md)
- [Workers limits](https://developers.cloudflare.com/workers/platform/limits/)
- [D1 pricing](https://developers.cloudflare.com/d1/platform/pricing/)
- [D1 limits](https://developers.cloudflare.com/d1/platform/limits/)
- [Access JWT validation](https://developers.cloudflare.com/cloudflare-one/identity/authorization-cookie/validating-json/)
- [One-time PIN](https://developers.cloudflare.com/cloudflare-one/integrations/identity-providers/one-time-pin/)
- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- [GitHub plans](https://docs.github.com/en/get-started/learning-about-github/githubs-plans)
- [NCAA 2027 Selection Sunday](https://www.ncaa.com/news/basketball-men/article/2026-08-12/2027-selection-sunday-date-schedule-tv-times-march-madness)
