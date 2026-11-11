# Betalytics pick capture

Pulls your Betalytics NCAAB picks out of the site without screenshots or copying.

## Use it (about 2 minutes, desktop Chrome / Edge / Firefox)

1. Sign in to Betalytics and open the page that lists the NCAAB picks.
2. Open DevTools (F12, or Cmd+Option+J on Mac) → **Console** tab.
3. Paste the entire contents of `capture.js` and press Enter.
   Chrome may ask you to type `allow pasting` first — do that, then paste again.
4. A small black panel appears at the bottom right. Click through every date,
   tab, filter or "load more" you want included. The counter goes up as data loads.
5. If the counter stays at 0, click **Grab page text** on each screen instead.
6. Click **Download**. You get `betalytics-capture-YYYY-MM-DD.json`.

The script records response data only — never your cookies, password or login
token — and sends nothing anywhere.

## Keep captures private

Captures hold your account's data. Save them under `data/betalytics/`
(git-ignored) or upload them in the Claude chat; don't commit them.
