# Betalytics NCAAB tracker

- `capture.user.js` — browser script that saves the pick data Betalytics pages load.
- `tracker/` — source of the private "Betalytics NCAAB Ledger" artifact (upload captures, see record/units/ROI).
- `closing.py` — consensus closing lines from The Odds API (key injected by the environment's network proxy as `x-api-key`; never stored in code), run 3x daily by a scheduled task.
- `scores.py`, `update_scores.py` — match games to NCAA.com final scores (ESPN is not used: its robots.txt disallows Anthropic's crawler); run daily by a scheduled task that writes scores into the artifact.

## Capture

Pulls Betalytics NCAAB picks out of the site without screenshots or copying.
`capture.user.js` records the pick data Betalytics pages load and saves it as one file.

## Android (Firefox + Tampermonkey) — runs by itself

One-time setup:
1. Install **Firefox** from the Play Store.
2. In Firefox: menu (⋮) → **Extensions** → find **Tampermonkey** → **Add**.
3. In Firefox, open
   `https://raw.githubusercontent.com/jsimone123189-cmd/Bracketology/ccr-944a70b7-8zngb6/tools/betalytics/capture.user.js`
   Tampermonkey shows an install page → tap **Install**.
4. Open `betalytics.com` in Firefox and sign in (once; Firefox remembers you).

Each time you look at picks:
- Open Betalytics in Firefox (not the Betalytics app). A small black panel
  appears bottom-right and counts data as it loads.
- Tap through the dates / tabs / models you want included.
- Tap **Download** to save `betalytics-capture-YYYY-MM-DD.json`.
- If the counter stays at 0, tap **Grab page text** on each screen instead.

## Desktop, one-off (no install)

On the picks page, open DevTools (F12) → **Console**, paste the whole file,
press Enter (Chrome may first ask you to type `allow pasting`). Then as above.

## Privacy

The script records response data only — never cookies, passwords or login
tokens — and sends nothing anywhere. Captures hold your account's data and
paid content: save them under `data/betalytics/` (git-ignored) or upload them
in the Claude chat. This repo is public; don't commit captures to it.
