/**
 * Live-bet alert: checks a Google Sheet every minute and pushes new "live" bets to your phone.
 *
 * Runs in YOUR Google account (script.google.com), so it is fast (1-minute checks) and private.
 * Alerts are emailed to your own Gmail (the Gmail app pushes them to your phone), and also sent to
 * ntfy (https://ntfy.sh) when Google can reach it.
 *
 * SETUP (about 5 minutes)
 *  1. On your phone, install the "ntfy" app and subscribe to a topic name only you know, e.g.
 *     "live-alerts-7f3k9q2m" (random letters: anyone who knows the name can read it).
 *  2. Go to script.google.com -> New project. Paste this whole file. Fill in CONFIG below.
 *     SHEET_ID is the long id in the sheet's URL: docs.google.com/spreadsheets/d/<SHEET_ID>/edit
 *     GIDS are the tab ids: the number after "gid=" in the URL when that tab is open (CBK tab, etc.).
 *  3. Run "setup" once (Run button). Approve the permissions it asks for. It records the live bets
 *     already on the sheet (no alerts for those) and installs a trigger that runs checkLive every minute.
 *  4. Test: run "testAlert". Your phone should buzz.
 *  To stop: run "stop".
 *
 * The sheet must be viewable by you (shared with your Google account, or "anyone with the link").
 */
const CONFIG = {
  SHEET_ID: 'PASTE_SHEET_ID_HERE',
  GIDS: ['0'],                       // tab ids to watch, e.g. ['0', '123456789']
  NTFY_TOPIC: 'PASTE_YOUR_SECRET_TOPIC',
  TO: '',                            // where alert emails go; empty = this Google account
  MATCH: /\blive\b/i,                // what marks a live bet in the bet description
  ROWS: 200,                         // read only the top rows: new bets go at the top of each tab
  HOURS: { from: 11, to: 2, tz: 'America/New_York' },   // only check 11 AM to 2 AM Eastern (games happen then)
};

function setup() {
  stop();
  checkLive(true);                   // remember current live rows without alerting
  ScriptApp.newTrigger('checkLive').timeBased().everyMinutes(1).create();
}

function stop() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    if (t.getHandlerFunction() === 'checkLive') ScriptApp.deleteTrigger(t);
  });
}

function testAlert() {
  push_('Test alert', 'Live-bet alerts are working.');
}

function inHours_() {
  const h = Number(Utilities.formatDate(new Date(), CONFIG.HOURS.tz, 'H'));
  const f = CONFIG.HOURS.from, t = CONFIG.HOURS.to;
  return f <= t ? (h >= f && h < t) : (h >= f || h < t);
}

function checkLive(silent) {
  if (silent !== true && !inHours_()) return;   // outside game hours: exit at once (keeps daily run time low)
  const props = PropertiesService.getScriptProperties();
  const seen = new Set(JSON.parse(props.getProperty('seen') || '[]'));
  const fresh = [];
  CONFIG.GIDS.forEach(function (gid) {
    readRows_(gid).forEach(function (row) {
      const desc = String(row[0] || '').trim();
      if (!desc || !CONFIG.MATCH.test(desc)) return;
      // Key on the bet itself (description + odds), not the result columns, so filling in
      // WIN/LOSS later does not trigger a second alert.
      const key = keyOf_(gid + '|' + desc + '|' + String(row[1] || '').trim());
      if (seen.has(key)) return;
      seen.add(key);
      fresh.push(row);
    });
  });
  // Triggers call this with an event object, so only an explicit true means silent (used by setup).
  if (silent !== true) fresh.forEach(function (row) {
    const odds = String(row[1] || '').trim(), units = String(row[2] || '').trim();
    push_('Live bet: ' + row[0], [odds && 'Odds ' + odds, units && units + 'u'].filter(String).join('  ·  ') ||
      'New live bet on the sheet');
  });
  props.setProperty('seen', JSON.stringify(Array.from(seen).slice(-400)));   // keep the store small
}

function readRows_(gid) {
  // Read through the Sheets service first (works for any sheet you can open); fall back to CSV export.
  try {
    const ss = SpreadsheetApp.openById(CONFIG.SHEET_ID);
    const sheet = ss.getSheets().filter(function (s) { return String(s.getSheetId()) === String(gid); })[0];
    if (sheet) return sheet.getRange(1, 1, Math.min(CONFIG.ROWS, sheet.getMaxRows()), 3).getDisplayValues();
  } catch (e) { /* not accessible this way; try CSV */ }
  const url = 'https://docs.google.com/spreadsheets/d/' + CONFIG.SHEET_ID + '/export?format=csv&gid=' + gid;
  const res = UrlFetchApp.fetch(url, { muteHttpExceptions: true, headers: { Authorization: 'Bearer ' + ScriptApp.getOAuthToken() } });
  if (res.getResponseCode() !== 200) throw new Error('Cannot read the sheet (HTTP ' + res.getResponseCode() + '). Check SHEET_ID, GIDS and sharing.');
  return Utilities.parseCsv(res.getContentText());
}

function keyOf_(s) {
  return Utilities.base64EncodeWebSafe(Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, s)).slice(0, 16);
}

function push_(title, body) {
  // Email to the script owner's Gmail: always works from Apps Script, and the Gmail app pushes it in seconds.
  MailApp.sendEmail(CONFIG.TO || Session.getEffectiveUser().getEmail(), title, body);
  // Also try ntfy; Google sometimes cannot reach it ("Address unavailable"), so failures are ignored.
  if (!CONFIG.NTFY_TOPIC || CONFIG.NTFY_TOPIC.indexOf('PASTE') === 0) return;
  try {
    UrlFetchApp.fetch('https://ntfy.sh/' + encodeURIComponent(CONFIG.NTFY_TOPIC), {
      method: 'post',
      payload: body,
      headers: { Title: title, Priority: 'urgent', Tags: 'basketball' },
      muteHttpExceptions: true,
    });
  } catch (e) { /* ntfy unreachable: the email already went out */ }
}
