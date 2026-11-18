/* "Brad Evans" tab: his public betting sheet (collection "brad", written daily by tools/brad/brad_sheet.py). */
(function () {
  'use strict';
  var START = '2026-11-18';                      // tracking began; bets first seen after this were posted live to us
  var SPORTS = [['NFL', 'NFL'], ['CBK', 'College basketball']];   // college football is stored but not shown
  var bets = [], loaded = false, el = null;

  function h(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function store(k, d) { try { var v = localStorage.getItem(k); return v == null ? d : v; } catch (_) { return d; } }
  function save(k, v) { try { localStorage.setItem(k, v); } catch (_) {} }
  function stake() { var v = Number(store('lab-unit', '30')); return v > 0 ? v : 30; }
  function money(x) { return (x < 0 ? '−$' : x > 0 ? '+$' : '$') + Math.abs(x).toFixed(0); }
  function units(x) { return (x > 0 ? '+' : x < 0 ? '−' : '') + Math.abs(x).toFixed(2) + 'u'; }
  function odds(o) { return (o > 0 ? '+' : '−') + Math.abs(o); }

  /** What kind of straight bet: spread, moneyline, total or prop (from the description). */
  function market(b) {
    if (b.k !== 'straight') return b.k;
    var d = b.d;
    if (/\bML\b/i.test(d)) return 'ml';
    if (/\d\s*(o|u)\b|\bover\b|\bunder\b|\d+\+?\s*(points|pts)\b/i.test(d) && !/(rec|rsh|rush|pass|yds|yards|TD|reb|ast|3PM|longest|most)/i.test(d)) return 'total';
    if (/(^|\s)[+-]\d+(\.5)?(\s|$)|\bPK\b/i.test(d) && !/(rec|rsh|rush|pass|yds|yards|TD)/i.test(d)) return 'spread';
    return 'prop';
  }

  /** Kind of player prop, from the description. */
  function propType(d) {
    var T = [['most', /\b(most|mst)\b/i], ['longest', /longest|\blng\b/i], ['td', /\bTD/], ['rec', /\d\+?\s*rec\b|\brec\b(?!.*yd)/i],
             ['recyds', /rec\.? ?(yds|yards)|rcv/i], ['rush', /rsh|rush/i], ['pass', /pass|cmp|\bint/i]];
    for (var i = 0; i < T.length; i++) if (T[i][1].test(d)) return T[i][0];
    return 'other';
  }
  function nflProp(b, full) { return b.sport === 'NFL' && !b.live && market(b) === 'prop' && (full ? b.u >= 1 : b.u < 1); }

  /** Betting styles found by sorting his last two seasons of bets (see footer); "tail" ones are the candidates,
   *  "avoid" ones have lost money in both seasons. Each keeps a separate record from the day tracking began. */
  var STYLES = [
    ['tail', 'NFL props he bets at a full unit (1u+)', function (b) { return nflProp(b, true); }],
    ['tail', '  · anytime TD, full unit', function (b) { return nflProp(b, true) && propType(b.d) === 'td'; }],
    ['tail', '  · most yards in the game, full unit', function (b) { return nflProp(b, true) && propType(b.d) === 'most'; }],
    ['tail', '  · receptions, full unit', function (b) { return nflProp(b, true) && propType(b.d) === 'rec'; }],
    ['watch', 'College basketball straight bets', function (b) { return b.sport === 'CBK' && !b.live && b.k === 'straight'; }],
    ['avoid', 'NFL props he bets at a half unit (his long shots)', function (b) { return nflProp(b, false); }],
    ['avoid', 'NFL rushing-yard props', function (b) { return b.sport === 'NFL' && !b.live && market(b) === 'prop' && propType(b.d) === 'rush'; }],
    ['avoid', 'Same-game parlays (both sports)', function (b) { return !b.live && b.k === 'sgp'; }],
  ];
  function styleOf(b) {
    for (var i = 0; i < STYLES.length; i++) if (STYLES[i][0] !== 'watch' && b.sport !== 'NCAAF' && STYLES[i][2](b)) return STYLES[i];
    return null;
  }

  function stylesSection(S) {
    var sec = h('section');
    sec.appendChild(h('h3', 'subh', 'Styles to tail'));
    sec.appendChild(h('p', 'muted lede', 'Groups of his non-live bets that have made or lost money in both of the last two seasons. ' +
      'Odds-boosted bets are left out. “Since 11/18” counts only bets that appeared on his sheet after tracking began, the real test.'));
    var wrap = h('div', 'scroll'), t = h('table'), hr = h('tr');
    ['Style', 'Last season', 'This season', 'Both: record', 'Both: you', 'Signal', 'Since 11/18', 'Call'].forEach(function (c) { hr.appendChild(h('th', null, c)); });
    var th = h('thead'); th.appendChild(hr); t.appendChild(th);
    var tb = h('tbody');
    STYLES.forEach(function (st) {
      var a = bets.filter(function (b) { return b.sport !== 'NCAAF' && !b.boost && b.k !== 'future' && st[2](b); });
      var curS = {}, prevS = {};
      SPORTS.forEach(function (sp) { var ss = seasonsOf(sp[0]); curS[sp[0]] = ss[0]; prevS[sp[0]] = ss[1]; });
      var c = sum(a.filter(function (b) { return b.season === curS[b.sport]; }), S);
      var p = sum(a.filter(function (b) { return b.season === prevS[b.sport]; }), S);
      var all = sum(a.filter(function (b) { return b.season === curS[b.sport] || b.season === prevS[b.sport]; }), S);
      var fw = sum(a.filter(function (b) { return b.fs > START; }), S);
      var tr = h('tr');
      tr.appendChild(h('td', null, st[1]));
      [p, c].forEach(function (x) { var td = h('td', null, x.n ? x.w + '–' + x.l + ' ' + money(x.pl) : '–'); if (x.n) td.className = x.pl > 0 ? 'pos' : 'neg'; tr.appendChild(td); });
      tr.appendChild(h('td', null, all.w + '–' + all.l));
      var tm = h('td', null, money(all.pl)); tm.className = all.pl > 0 ? 'pos' : 'neg'; tr.appendChild(tm);
      tr.appendChild(h('td', null, (all.z >= 0 ? '+' : '−') + Math.abs(all.z).toFixed(1) + 'σ'));
      tr.appendChild(h('td', null, fw.n ? fw.w + '–' + fw.l + ' ' + money(fw.pl) : 'none yet'));
      var call = st[0] === 'tail' ? (fw.n >= 30 && fw.pl < 0 ? ['Re-check', 'down'] : ['Tail', 'up']) : st[0] === 'avoid' ? ['Avoid', 'down'] : ['Watch', ''];
      var tdc = h('td'); tdc.appendChild(h('span', 'sig ' + call[1], call[0])); tr.appendChild(tdc);
      tb.appendChild(tr);
    });
    t.appendChild(tb); wrap.appendChild(t); sec.appendChild(wrap);
    sec.appendChild(h('p', 'muted lede', 'Signal is profit measured against luck at those prices: ±2σ is about what a 1-in-40 fluke looks like. ' +
      'These styles were picked out of about 150 groups I tested, so expect one or two to be flukes; that is why each keeps its own ' +
      'record from 11/18. A Tail style turns to Re-check if it loses money over its first 30 tracked bets.'));
    return sec;
  }

  /** Your result tailing the bet at a flat stake: risk S on plus money, to win S on minus money. */
  function flat(b, S) {
    var o = b.o, win = o > 0 ? S * o / 100 : S, lose = o > 0 ? S : S * -o / 100;
    var p0 = o > 0 ? 100 / (o + 100) : -o / (-o + 100);
    var pl = b.r === 'WIN' ? win : b.r === 'LOSS' ? -lose : 0;
    return { pl: pl, risk: lose, v: (b.r === 'WIN' || b.r === 'LOSS') ? p0 * (1 - p0) * Math.pow(win + lose, 2) : 0 };
  }

  function sum(list, S) {
    var x = { w: 0, l: 0, p: 0, u: 0, pl: 0, risk: 0, v: 0 };
    list.forEach(function (b) {
      if (!b.r) return;
      if (b.r === 'WIN') x.w++; else if (b.r === 'LOSS') x.l++; else x.p++;
      x.u += b.n || 0;
      var f = flat(b, S); x.pl += f.pl; x.risk += f.risk; x.v += f.v;
    });
    x.n = x.w + x.l;
    x.z = x.v > 0 ? x.pl / Math.sqrt(x.v) : 0;
    x.roi = x.risk > 0 ? x.pl / x.risk : null;
    return x;
  }

  function seasonsOf(sport) {
    var s = {};
    bets.forEach(function (b) { if (b.sport === sport) s[b.season] = 1; });
    return Object.keys(s).sort().reverse();
  }

  /** Tail / Skip / Not yet, from both seasons together: needs 100+ decided bets, profit beyond luck (z ≥ 1.28,
   *  about 90% one-sided) and a profit in each of the last two seasons, so one hot run can't carry it. */
  function verdict(cur, prev, all) {
    if (all.n < 100) return ['Too few', ''];
    if (all.z >= 1.28 && cur.pl > 0 && (prev.n < 30 || prev.pl > 0)) return ['Tail', 'up'];
    if (all.z <= -1.28) return ['Skip', 'down'];
    if (all.pl < 0) return ['Losing', 'down'];
    return ['Not yet', ''];
  }

  var SEGMENTS = [
    ['live', 'Live bets (alerts)', function (b) { return b.live; }],
    ['nonlive', 'Everything except live', function (b) { return !b.live && b.k !== 'future'; }],
    ['straight', '· Straight bets', function (b) { return !b.live && b.k === 'straight'; }],
    ['spread', '   – spreads', function (b) { return !b.live && market(b) === 'spread'; }],
    ['ml', '   – moneylines', function (b) { return !b.live && market(b) === 'ml'; }],
    ['total', '   – totals', function (b) { return !b.live && market(b) === 'total'; }],
    ['prop', '   – props', function (b) { return !b.live && market(b) === 'prop'; }],
    ['parlay', '· Parlays', function (b) { return !b.live && b.k === 'parlay'; }],
    ['sgp', '· Same-game parlays', function (b) { return !b.live && b.k === 'sgp'; }],
  ];

  function usable(b) { return store('brad-boost', '0') === '1' || !b.boost; }

  function render() {
    try { draw(); } catch (e) { if (el) { el.innerHTML = ''; el.appendChild(h('p', 'note', 'The Brad tab hit an error: ' + e.message)); } }
  }

  function draw() {
    if (!el || el.hidden) return;
    el.innerHTML = '';
    var S = stake();
    var sec = h('section');
    sec.appendChild(h('h2', null, 'Brad Evans'));
    sec.appendChild(h('p', 'muted lede', 'Brad’s NFL and college basketball bets from his public sheet, refreshed daily. ' +
      'The question this tab answers: is anything besides his live bets worth tailing? Dollar figures are what you would have made ' +
      'tailing each bet at your stake ($' + S + ': risk $' + S + ' on plus money, to win $' + S + ' on minus money), at his posted price. ' +
      'Units are Brad’s own sizing and results.'));
    if (failed) sec.appendChild(h('p', 'note', failed));
    if (!loaded) { if (!failed) sec.appendChild(h('p', 'muted', 'Loading Brad’s bets…')); el.appendChild(sec); return; }

    var opts = h('div', 'filters');
    var lab = h('label', 'flabel'); var cb = h('input'); cb.type = 'checkbox'; cb.checked = store('brad-boost', '0') === '1';
    cb.onchange = function () { save('brad-boost', cb.checked ? '1' : '0'); render(); };
    lab.appendChild(cb); lab.appendChild(document.createTextNode(' Count odds-boosted bets (you may not get the same boost)'));
    opts.appendChild(lab); sec.appendChild(opts);

    // Since tracking began: bets that appeared on the sheet after START.
    var fresh = bets.filter(function (b) { return b.fs > START && usable(b); });
    var fl = sum(fresh.filter(function (b) { return b.live; }), S), fn = sum(fresh.filter(function (b) { return !b.live && b.k !== 'future'; }), S);
    var strip = h('div', 'strip');
    [['Live since ' + START.slice(5).replace('-', '/'), fl], ['Non-live since ' + START.slice(5).replace('-', '/'), fn]].forEach(function (c) {
      var d = h('div'); d.appendChild(h('div', 'k', c[0]));
      d.appendChild(h('div', 'v num ' + (c[1].pl > 0 ? 'pos' : c[1].pl < 0 ? 'neg' : ''), c[1].n ? money(c[1].pl) : '–'));
      d.appendChild(h('div', 'muted', c[1].n ? c[1].w + '–' + c[1].l + ' · ' + units(c[1].u) : 'No graded bets yet'));
      strip.appendChild(d);
    });
    sec.appendChild(strip);
    el.appendChild(sec);
    el.appendChild(stylesSection(S));

    SPORTS.forEach(function (sp) {
      var ss = seasonsOf(sp[0]); if (!ss.length) return;
      var cur = ss[0], prev = ss[1];
      var mine = bets.filter(function (b) { return b.sport === sp[0] && usable(b); });
      var s2 = h('section');
      s2.appendChild(h('h3', 'subh', sp[1]));
      var wrap = h('div', 'scroll'), t = h('table'), hr = h('tr');
      ['Bets', cur + ' record', cur + ' units', cur + ' you', (prev || '–') + ' record', (prev || '–') + ' units', (prev || '–') + ' you', 'ROI (both)', 'Verdict'].forEach(function (c) { hr.appendChild(h('th', null, c)); });
      var th = h('thead'); th.appendChild(hr); t.appendChild(th);
      var tb = h('tbody');
      SEGMENTS.forEach(function (seg) {
        var a = mine.filter(seg[2]);
        var c = sum(a.filter(function (b) { return b.season === cur; }), S);
        var p = sum(a.filter(function (b) { return b.season === prev; }), S);
        var all = sum(a.filter(function (b) { return b.season === cur || b.season === prev; }), S);
        if (!all.n && seg[0] !== 'live') return;
        var tr = h('tr');
        tr.appendChild(h('td', null, seg[1]));
        [c, p].forEach(function (x) {
          tr.appendChild(h('td', null, x.n ? x.w + '–' + x.l : '–'));
          var tu = h('td', null, x.n ? units(x.u) : '–'); if (x.n) tu.className = x.u > 0 ? 'pos' : x.u < 0 ? 'neg' : ''; tr.appendChild(tu);
          var tm = h('td', null, x.n ? money(x.pl) : '–'); if (x.n) tm.className = x.pl > 0 ? 'pos' : x.pl < 0 ? 'neg' : ''; tr.appendChild(tm);
        });
        tr.appendChild(h('td', null, all.roi == null ? '–' : (all.roi < 0 ? '−' : '') + Math.abs(all.roi * 100).toFixed(1) + '%'));
        var v = verdict(c, p, all), tdv = h('td'); tdv.appendChild(h('span', 'sig ' + v[1], v[0])); tr.appendChild(tdv);
        tb.appendChild(tr);
      });
      t.appendChild(tb); wrap.appendChild(t); s2.appendChild(wrap);

      // Recent weeks of the current season.
      var weeks = [], seen = {};
      mine.forEach(function (b) { if (b.season === cur && !seen[b.w]) { seen[b.w] = 1; weeks.push(b.w); } });
      if (weeks.length) {
        var line = weeks.slice(0, 6).map(function (w) {
          var x = sum(mine.filter(function (b) { return b.w === w && !b.live && b.k !== 'future'; }), S);
          return w.replace(/'\d\d-'\d\d|\b20\d\d\b/g, '').replace(/\s+/g, ' ').trim() + ': ' + (x.n ? x.w + '–' + x.l + ' ' + money(x.pl) : 'pending');
        });
        s2.appendChild(h('p', 'muted lede', 'Non-live by week, newest first: ' + line.join(' · ')));
      }
      el.appendChild(s2);
    });

    // Open bets that can still be tailed.
    var open = bets.filter(function (b) { return b.sport !== 'NCAAF' && !b.r && !b.live && b.k !== 'future' && seasonsOf(b.sport)[0] === b.season; });
    open.sort(function (a, b) { var x = styleOf(a), y = styleOf(b); return (x && x[0] === 'tail' ? 0 : x ? 2 : 1) - (y && y[0] === 'tail' ? 0 : y ? 2 : 1); });
    var s3 = h('section');
    s3.appendChild(h('h3', 'subh', 'Open bets on his sheet (not live)'));
    if (!open.length) s3.appendChild(h('p', 'muted', 'None right now.'));
    open.slice(0, 40).forEach(function (b) {
      var s = h('div', 'slip');
      s.appendChild(h('span', 'grade C', b.sport === 'CBK' ? 'CBB' : b.sport === 'NFL' ? 'NFL' : 'CFB'));
      var mid = h('div'); mid.style.minWidth = '0';
      mid.appendChild(h('div', 'pick', b.d));
      mid.appendChild(h('div', 'meta', odds(b.o) + ' · ' + b.u + 'u · ' + (b.b || 'book ?') + ' · ' + b.w + (b.boost ? ' · boosted' : '')));
      s.appendChild(mid);
      var st = styleOf(b);
      if (st) { var r = h('div', 'res'); r.appendChild(h('span', 'tag rec-' + (st[0] === 'tail' ? 'follow' : 'avoid'), st[0] === 'tail' ? 'Tail style' : 'Avoid style')); s.appendChild(r); }
      s3.appendChild(s);
    });
    el.appendChild(s3);

    var f = h('footer');
    f.appendChild(h('p', null, 'Verdict uses this season and last season together. Tail needs 100+ decided bets, a profit beyond what luck at those ' +
      'prices would produce (about 90% confidence), and a profit this season and last, so one hot stretch can’t earn it. ' +
      'Losing and Skip mean tailing has cost money (Skip: clearly, not just bad luck). Parlays and same-game parlays carry big ' +
      'swings, so they need far more bets than straights to prove anything. Futures are left out. Records are Brad’s own entries ' +
      'on the sheet; voids and pushes count as $0.'));
    el.appendChild(f);
  }

  var failed = '';
  function start(db) {
    var timer = setTimeout(function () { if (!loaded) { failed = 'Still loading Brad’s bets… the store is slow to answer.'; render(); } }, 15000);
    db.collection('brad').onSnapshot(function (snap) {
      try {
        var list = [];
        snap.docs.forEach(function (d) {
          var doc = d.data(); if (!doc || !doc.bets) return;
          Object.keys(doc.bets).forEach(function (k) {
            // Copy: the store's documents are read-only.
            var b = Object.assign({}, doc.bets[k], { id: k, sport: doc.sport, season: doc.season });
            list.push(b);
          });
        });
        // Newest first: by season, then by position on the sheet.
        list.sort(function (a, b) { return a.season < b.season ? 1 : a.season > b.season ? -1 : (b.i || 0) - (a.i || 0); });
        bets = list; failed = '';
      } catch (e) { failed = 'Brad’s bets could not be read (' + e.message + ').'; }
      loaded = true; clearTimeout(timer);
      render();
    }, function (e) { loaded = true; clearTimeout(timer); failed = 'Brad’s bets could not be loaded' + (e && e.message ? ' (' + e.message + ')' : '') + '. Reload to try again.'; render(); });
  }

  window.BradTab = { start: start, render: function (node) { if (node) el = node; render(); }, market: market };
})();
