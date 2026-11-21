// Live Brad Checks, second file (Alerts2.gs). This is the version running now.
// It lives next to the original Code.gs in the same Apps Script project, so every name ends in 2.
// Live bets alert 11 AM-2 AM ET; every other new bet alerts 7:00-9:59 PM ET.
// To install: + next to Files -> Script, paste, set TO, Save, pick setup2 in the function list, Run.
// setup2 removes the old checkLive schedule and starts checkLive2 every minute.
// TO is left blank here because this repository is public: fill in the address alerts go to.
const CONFIG2 = {
  SHEET_ID: '1iSoCt8jYVcC0mye6pOQ57NVsxYzOBeKNEKRsnvgmGYk',
  GIDS: ['1337232798', '0'],
  NTFY_TOPIC: '',
  TO: '',
  MATCH: /\blive\b/i,
  ROWS: 200,
  HOURS: { from: 11, to: 2, tz: 'America/New_York' },
  ALL: { from: 19, to: 22 },
};

function setup2() {
  stop2();
  checkLive2(true);
  ScriptApp.newTrigger('checkLive2').timeBased().everyMinutes(1).create();
}

function stop2() {
  ScriptApp.getProjectTriggers().forEach(function (t) {
    const f = t.getHandlerFunction();
    if (f === 'checkLive' || f === 'checkLive2') ScriptApp.deleteTrigger(t);
  });
}

function testAlert2() {
  push2_('Test alert', 'Live-bet alerts are working.');
}

function inWindow2_(w) {
  const h = Number(Utilities.formatDate(new Date(), CONFIG2.HOURS.tz, 'H'));
  return w.from <= w.to ? (h >= w.from && h < w.to) : (h >= w.from || h < w.to);
}

function inHours2_() {
  return inWindow2_(CONFIG2.HOURS);
}

function checkLive2(silent) {
  if (silent !== true && !inHours2_()) return;
  const props = PropertiesService.getScriptProperties();
  const seen = new Set(JSON.parse(props.getProperty('seen') || '[]'));
  const prevRaw = props.getProperty('rows');
  const prev = new Set(JSON.parse(prevRaw || '[]'));
  const allOn = silent !== true && prevRaw !== null && inWindow2_(CONFIG2.ALL);
  const current = [], fresh = [];
  CONFIG2.GIDS.forEach(function (gid) {
    readRows2_(gid).forEach(function (row) {
      const desc = String(row[0] || '').trim(), odds = String(row[1] || '').trim();
      if (!desc) return;
      const key = keyOf2_(gid + '|' + desc + '|' + odds);
      const isBet = odds && odds !== 'Juice';
      const isNew = isBet && !prev.has(key.slice(0, 10));
      if (isBet) current.push(key.slice(0, 10));
      if (CONFIG2.MATCH.test(desc)) {
        if (seen.has(key)) return;
        seen.add(key);
        fresh.push({ row: row, live: true });
      } else if (isNew && allOn) {
        fresh.push({ row: row, live: false });
      }
    });
  });
  if (silent !== true) fresh.forEach(function (f) {
    const odds = String(f.row[1] || '').trim(), units = String(f.row[2] || '').trim();
    push2_((f.live ? 'Live bet: ' : 'New bet: ') + f.row[0],
      [odds && 'Odds ' + odds, units && units + 'u'].filter(String).join('  ·  ') ||
      (f.live ? 'New live bet on the sheet' : 'New bet on the sheet'));
  });
  props.setProperty('seen', JSON.stringify(Array.from(seen).slice(-400)));
  props.setProperty('rows', JSON.stringify(current));
}

function readRows2_(gid) {
  try {
    const ss = SpreadsheetApp.openById(CONFIG2.SHEET_ID);
    const sheet = ss.getSheets().filter(function (s) { return String(s.getSheetId()) === String(gid); })[0];
    if (sheet) return sheet.getRange(1, 1, Math.min(CONFIG2.ROWS, sheet.getMaxRows()), 3).getDisplayValues();
  } catch (e) { }
  const url = 'https://docs.google.com/spreadsheets/d/' + CONFIG2.SHEET_ID + '/export?format=csv&gid=' + gid;
  const res = UrlFetchApp.fetch(url, { muteHttpExceptions: true, headers: { Authorization: 'Bearer ' + ScriptApp.getOAuthToken() } });
  if (res.getResponseCode() !== 200) throw new Error('Cannot read the sheet (HTTP ' + res.getResponseCode() + ').');
  return Utilities.parseCsv(res.getContentText());
}

function keyOf2_(s) {
  return Utilities.base64EncodeWebSafe(Utilities.computeDigest(Utilities.DigestAlgorithm.MD5, s)).slice(0, 16);
}

function push2_(title, body) {
  MailApp.sendEmail(CONFIG2.TO || Session.getEffectiveUser().getEmail(), title, body);
}
