/* "Brad Evans" tab: reads one small summary document (collection "bradsum", doc "latest") that the
 * daily job builds from his public sheet with tools/brad/brad_sheet.py. Every bet is stored in the
 * "brad" collection as the record; the page doesn't download them. */
(function () {
  'use strict';
  var sum = null, loaded = false, failed = '', el = null;
  var db = null, mine = {}, showAll = false;      // mine: {betId: {price}} from collection "mytails"

  function h(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function stake() { try { var v = Number(localStorage.getItem('lab-unit') || 30); return v > 0 ? v : 30; } catch (_) { return 30; } }
  function money(x) { return (x < 0 ? '−$' : x > 0 ? '+$' : '$') + Math.abs(x).toFixed(0); }
  function units(x) { return (x > 0 ? '+' : x < 0 ? '−' : '') + Math.abs(x).toFixed(1) + 'u'; }
  function odds(o) { return (o > 0 ? '+' : '−') + Math.abs(o); }
  function rec(x) { return x && x.w + x.l ? x.w + '–' + x.l : '–'; }
  function cls(x) { return x > 0 ? 'pos' : x < 0 ? 'neg' : ''; }
  function fairText(b) {
    var f = b.fair; if (!f) return '';
    var e = Math.round(Math.abs(f.edge) * 100);
    var lead = 'His ' + (b.sport === 'CBK' ? 'college' : 'NFL') + ' straights at ' + f.band + ' win about ' + e + '% ' + (f.edge >= 0 ? 'more' : 'less') + ' often than break-even. ';
    return f.ok ? lead + 'Worth it at ' + odds(f.min) + ' or better; ' + odds(b.o) + ' clears it.'
                : lead + 'Needs ' + odds(f.min) + ' or better; not worth it at ' + odds(b.o) + '.';
  }
  function day(s) { var p = s.split('-'); return Number(p[1]) + '/' + Number(p[2]); }

  function table(head, rows) {
    var wrap = h('div', 'scroll'), t = h('table'), tr = h('tr');
    head.forEach(function (c) { tr.appendChild(h('th', null, c)); });
    var th = h('thead'); th.appendChild(tr); t.appendChild(th);
    var tb = h('tbody');
    rows.forEach(function (r) {
      var row = h('tr');
      r.forEach(function (c) {
        var td = h('td');
        if (c && c.tag) td.appendChild(h('span', 'sig ' + c.cls, c.tag));
        else if (c && c.text != null) { td.textContent = c.text; td.className = c.cls || ''; }
        else td.textContent = c;
        row.appendChild(td);
      });
      tb.appendChild(row);
    });
    t.appendChild(tb); wrap.appendChild(t);
    return wrap;
  }

  function cash(x, S) { return x && x.w + x.l ? { text: money(x.pl * S), cls: cls(x.pl) } : '–'; }
  function both(x, S) { return x && x.w + x.l ? { text: rec(x) + ' ' + money(x.pl * S), cls: cls(x.pl) } : '–'; }
  var CALL = { tail: ['Tail', 'up'], avoid: ['Avoid', 'down'], watch: ['Watch', ''] };
  var VERD = { 'Tail': 'up', 'Skip': 'down', 'Losing': 'down', 'Not yet': '', 'Too few': '' };


  /** Your result on one bet at a price, with your stake rule (risk S on plus money, to win S on minus). */
  function pay(o, r, S) {
    if (r === 'WIN') return o > 0 ? S * o / 100 : S;
    if (r === 'LOSS') return o > 0 ? -S : -S * -o / 100;
    return 0;
  }

  function savePrice(id, v) {
    if (!db) return;
    var n = Number(v);
    var ref = db.doc('mytails/' + id);
    var ok = v && isFinite(n) && Math.abs(n) >= 100;
    var op = ref.set({ price: ok ? Math.round(n) : 0, at: new Date().toISOString() });   // 0 = cleared
    Promise.resolve(op).catch(function (e) { failed = 'Could not save your price (' + (e && e.message || e) + ').'; render(); });
  }

  function tailsSection(S) {
    var sec = h('section');
    sec.appendChild(h('h3', 'subh', 'Your tails'));
    var rec = sum.recent || [];
    var done = rec.filter(function (b) { return mine[b.id]; });
    var t = { w: 0, l: 0, you: 0, his: 0, gap: 0, n: 0 };
    done.forEach(function (b) {
      var p = mine[b.id].price;
      if (b.r === 'WIN' || b.r === 'LOSS') {
        if (b.r === 'WIN') t.w++; else t.l++;
        t.you += pay(p, b.r, S); t.his += pay(b.o, b.r, S);
      }
      t.gap += p - b.o; t.n++;
    });
    if (t.w + t.l) {
      var strip = h('div', 'strip');
      [['You', t.you, t.w + '–' + t.l + ' at your prices'], ['At his prices', t.his, 'same bets'],
       ['Price gap', null, 'yours vs his, on average']].forEach(function (c) {
        var d = h('div'); d.appendChild(h('div', 'k', c[0]));
        d.appendChild(h('div', 'v num ' + (c[1] == null ? '' : cls(c[1])), c[1] == null ? (t.n ? (t.gap / t.n > 0 ? '+' : t.gap / t.n < 0 ? '−' : '') + Math.abs(Math.round(t.gap / t.n)) : '–') : money(c[1])));
        d.appendChild(h('div', 'muted', c[2])); strip.appendChild(d);
      });
      sec.appendChild(strip);
    }
    sec.appendChild(h('p', 'muted lede', 'Enter the price you actually got on his live bets and Tail-style bets (like +135). It saves as you leave the box; ' +
      'clear it to remove. Your results use your $' + S + ' stake rule and his win/loss.'));
    var list = showAll ? rec : rec.filter(function (b, i) { return mine[b.id] || i < 12; });
    list.forEach(function (b) {
      var row = h('div', 'slip');
      row.appendChild(h('span', 'grade ' + (b.live ? 'A' : 'B'), b.live ? 'Live' : (b.sport === 'CBK' ? 'CBB' : 'NFL')));
      var mid = h('div'); mid.style.minWidth = '0';
      mid.appendChild(h('div', 'pick', b.d));
      var res = b.r === 'WIN' ? 'Won' : b.r === 'LOSS' ? 'Lost' : b.r ? b.r.charAt(0) + b.r.slice(1).toLowerCase() : 'Pending';
      var m = mine[b.id];
      var line = 'His ' + odds(b.o) + ' · ' + (b.b || 'book ?') + ' · ' + res;
      if (m && (b.r === 'WIN' || b.r === 'LOSS')) line += ' · you ' + money(pay(m.price, b.r, S)) + ' (his price ' + money(pay(b.o, b.r, S)) + ')';
      mid.appendChild(h('div', 'meta', line));
      row.appendChild(mid);
      var box = h('div', 'res');
      var inp = h('input'); inp.type = 'text'; inp.inputMode = 'numeric'; inp.className = 'pricein'; inp.placeholder = 'Your price';
      inp.setAttribute('aria-label', 'Your price for ' + b.d);
      if (m) inp.value = (m.price > 0 ? '+' : '') + m.price;
      inp.addEventListener('change', function () { savePrice(b.id, inp.value.replace(/[^\d+-]/g, '')); });
      box.appendChild(inp); row.appendChild(box);
      sec.appendChild(row);
    });
    if (!showAll && rec.length > list.length) {
      var more = h('button', 'btn-link', 'Show ' + (rec.length - list.length) + ' older bets');
      more.type = 'button'; more.onclick = function () { showAll = true; render(); };
      sec.appendChild(more);
    }
    return sec;
  }

  // ---------- Live read of his sheet (in your browser, no scheduled job) ----------
  // Open bets come straight from his public sheet each time the tab opens, so bets he posts during the day
  // show up at once. Records still come from the daily summary. Falls back to the summary if the read fails.
  var SHEET = 'https://docs.google.com/spreadsheets/d/1iSoCt8jYVcC0mye6pOQ57NVsxYzOBeKNEKRsnvgmGYk/export?format=csv&gid=';
  var TABS = { CBK: '1337232798', NFL: '0' };
  var liveOpen = null, liveAt = null, liveTried = false;

  function csv(text) {
    var rows = [], row = [], f = '', q = false;
    for (var i = 0; i < text.length; i++) {
      var c = text[i];
      if (q) { if (c === '"') { if (text[i + 1] === '"') { f += '"'; i++; } else q = false; } else f += c; }
      else if (c === '"') q = true;
      else if (c === ',') { row.push(f); f = ''; }
      else if (c === '\n' || c === '\r') { if (c === '\r' && text[i + 1] === '\n') i++; row.push(f); rows.push(row); row = []; f = ''; }
      else f += c;
    }
    if (f || row.length) { row.push(f); rows.push(row); }
    return rows;
  }
  function oddsOf(s) { var m = String(s).match(/[+-]?\d{3,5}/); if (!m) return null; var v = parseInt(m[0], 10); return Math.abs(v) >= 100 ? v : null; }
  var TWO = /(rec|rsh|rush|pass|yds|yards|TD|reb|ast|3PM|longest|most)/i;
  function kindOf(d) { return /^SGP/i.test(d) ? 'sgp' : /^\d+-leg/i.test(d) ? 'parlay' : 'straight'; }
  function marketOf(b) {
    if (b.k !== 'straight') return b.k;
    if (/\bML\b/i.test(b.d)) return 'ml';
    if (/\d\s*(o|u)\b|\bover\b|\bunder\b|\d+\+?\s*(points|pts)\b/i.test(b.d) && !TWO.test(b.d)) return 'total';
    if (/(^|\s)[+-]\d+(\.5)?(\s|$)|\bPK\b/i.test(b.d) && !TWO.test(b.d)) return 'spread';
    return 'prop';
  }
  function propType(d) {
    var T = [['most', /\b(most|mst)\b/i], ['longest', /longest|\blng\b/i], ['td', /\bTD/], ['rec', /\d\+?\s*rec\b|\brec\b(?!.*yd)/i],
             ['recyds', /rec\.? ?(yds|yards)|rcv/i], ['rush', /rsh|rush/i], ['pass', /pass|cmp|\bint/i]];
    for (var i = 0; i < T.length; i++) if (T[i][1].test(d)) return T[i][0];
    return 'other';
  }
  // Same styles, same order, as tools/brad/brad_sheet.py; the calls (tail/watch/avoid) come from the daily summary.
  function fullProp(b, full) { return b.sport === 'NFL' && marketOf(b) === 'prop' && (full ? b.u >= 1 : b.u < 1); }
  var STYLE_FN = {
    'NFL props he bets at a full unit (1u+)': function (b) { return fullProp(b, true); },
    '· anytime TD, full unit': function (b) { return fullProp(b, true) && propType(b.d) === 'td'; },
    '· most yards in the game, full unit': function (b) { return fullProp(b, true) && propType(b.d) === 'most'; },
    '· receptions, full unit': function (b) { return fullProp(b, true) && propType(b.d) === 'rec'; },
    'College basketball straight bets': function (b) { return b.sport === 'CBK' && b.k === 'straight'; },
    'NFL props at a half unit (his long shots)': function (b) { return fullProp(b, false); },
    'NFL rushing-yard props': function (b) { return b.sport === 'NFL' && marketOf(b) === 'prop' && propType(b.d) === 'rush'; },
    'Same-game parlays': function (b) { return b.k === 'sgp'; },
  };
  function styleOf(b) {
    var st = (sum && sum.styles) || [], i;
    for (i = 0; i < st.length; i++) if (st[i].call === 'avoid' && STYLE_FN[st[i].name] && STYLE_FN[st[i].name](b)) return 'avoid';
    for (i = 0; i < st.length; i++) if (st[i].call === 'tail' && STYLE_FN[st[i].name] && STYLE_FN[st[i].name](b)) return 'tail';
    return null;
  }
  function implied(o) { return o > 0 ? 100 / (o + 100) : -o / (-o + 100); }
  function american(p) { return p < 0.5 ? Math.round(100 * (1 - p) / p) : -Math.round(100 * p / (1 - p)); }
  function fairOf(b) {
    if (b.k !== 'straight' || !sum || !sum.sports) return null;
    var sp = sum.sports.filter(function (x) { return x.sport === b.sport; })[0];
    if (!sp || !sp.bands) return null;
    var lim = [[-1e6, -101], [100, 134], [135, 199], [200, 1e6]], i;
    for (i = 0; i < lim.length; i++) if (b.o >= lim[i][0] && b.o <= lim[i][1]) break;
    var bd = sp.bands[i];
    if (!bd || bd.ratio == null) return null;
    var p = Math.min(0.97, implied(b.o) * bd.ratio), mn = american(p);
    return { band: bd.name, p: p, min: mn, ok: b.o >= mn, edge: bd.ratio - 1 };
  }
  function parseOpen(sport, rows) {
    var out = [], headers = 0, header = '';
    for (var i = 0; i < rows.length; i++) {
      var r = rows[i], a = (r[0] || '').trim();
      if ((r[1] || '').trim() === 'Juice') { headers++; header = a; if (headers > 2) break; continue; }   // newest two weeks
      if (!headers) continue;
      var o = oddsOf(r[1] || ''), u = parseFloat(r[2]);
      if (!a || o == null || !(u > 0)) continue;
      if ((r[5] || '').trim()) continue;                       // already graded
      if (/\blive\b/i.test(a)) continue;                       // live bets alert you by email
      var b = { d: a, o: o, u: u, b: (r[4] || '').trim(), sport: sport, w: header, k: kindOf(a),
                boost: /boost/i.test((r[6] || '') + ' ' + (r[7] || '')) };
      b.style = styleOf(b); b.fair = fairOf(b);
      out.push(b);
    }
    return out;
  }
  function readLive() {
    if (liveTried) return; liveTried = true;
    Promise.all(Object.keys(TABS).map(function (sp) {
      return fetch(SHEET + TABS[sp], { credentials: 'omit' }).then(function (r) {
        if (!r.ok) throw new Error('HTTP ' + r.status);
        return r.text();
      }).then(function (t) { return parseOpen(sp, csv(t)); });
    })).then(function (lists) {
      var all = [].concat.apply([], lists), rank = { tail: 0, avoid: 2 };
      all.sort(function (x, y) { return (rank[x.style] == null ? 1 : rank[x.style]) - (rank[y.style] == null ? 1 : rank[y.style]); });
      liveOpen = all; liveAt = new Date(); render();
    }).catch(function () { liveOpen = null; render(); });     // blocked or offline: the daily summary's list stays
  }

  function render() { try { draw(); } catch (e) { if (el) { el.innerHTML = ''; el.appendChild(h('p', 'note', 'The Brad tab hit an error: ' + e.message)); } } }

  function draw() {
    if (!el || el.hidden) return;
    el.innerHTML = '';
    var S = stake(), sec = h('section');
    sec.appendChild(h('h2', null, 'Brad Evans'));
    sec.appendChild(h('p', 'muted lede', 'His NFL and college basketball bets, refreshed every morning. Dollar figures are what tailing would ' +
      'have made at your stake ($' + S + ': risk $' + S + ' on plus money, to win $' + S + ' on minus money) at his posted price. ' +
      'Odds-boosted bets count at their boosted price in their normal category; futures are left out.'));
    el.appendChild(sec);
    if (failed) { sec.appendChild(h('p', 'note', failed)); return; }
    if (!loaded) { sec.appendChild(h('p', 'muted', 'Loading Brad’s record…')); return; }
    if (!sum) { sec.appendChild(h('p', 'muted', 'Brad’s summary hasn’t been built yet. It appears after the next morning update.')); return; }

    var strip = h('div', 'strip');
    [['Live since ' + day(sum.start), sum.since.live], ['Non-live since ' + day(sum.start), sum.since.nonlive]].forEach(function (c) {
      var d = h('div'); d.appendChild(h('div', 'k', c[0]));
      var n = c[1].w + c[1].l;
      d.appendChild(h('div', 'v num ' + cls(c[1].pl), n ? money(c[1].pl * S) : '–'));
      d.appendChild(h('div', 'muted', n ? rec(c[1]) + ' · ' + units(c[1].u) : 'No graded bets yet'));
      strip.appendChild(d);
    });
    sec.appendChild(strip);
    if (sum.checked) sec.appendChild(h('p', 'muted', 'Last checked his sheet: ' + new Date(sum.checked).toLocaleString(undefined, { weekday: 'short', hour: 'numeric', minute: '2-digit' }) +
      ' · ' + (sum.open || []).length + ' open bet' + ((sum.open || []).length === 1 ? '' : 's') + ' (not live)'));

    var s1 = h('section');
    s1.appendChild(h('h3', 'subh', 'What to tail'));
    s1.appendChild(table(['Style', 'Last season', 'This season', 'Both seasons', 'Signal', 'Since ' + day(sum.start), 'Call'],
      sum.styles.map(function (st) {
        var fwN = st.fw.w + st.fw.l, call = st.call;
        if (call === 'tail' && fwN >= 30 && st.fw.pl < 0) call = 'recheck';
        var c = call === 'recheck' ? ['Re-check', 'down'] : CALL[call];
        return [st.name, both(st.prev, S), both(st.cur, S), both(st.both, S),
                (st.both.z >= 0 ? '+' : '−') + Math.abs(st.both.z).toFixed(1) + 'σ',
                fwN ? both(st.fw, S) : 'none yet', { tag: c[0], cls: c[1] }];
      })));
    s1.appendChild(h('p', 'muted lede', 'Tail: made money in both of his last two seasons, by more than luck explains. Avoid: lost in both. ' +
      'Signal is profit measured against luck at those prices (±2σ is about a 1-in-40 fluke). These were picked from about 150 groupings, ' +
      'so the “Since” column is the real test; a Tail style turns to Re-check if it loses over its first 30 tracked bets.'));
    el.appendChild(s1);

    if (sum.recent) el.appendChild(tailsSection(S));
    var s2 = h('section');
    s2.appendChild(h('h3', 'subh', 'Open bets on his sheet worth a look'));
    readLive();
    var openAll = liveOpen || sum.open || [];
    s2.appendChild(h('p', 'muted', liveOpen ? 'Live from his sheet, checked ' + liveAt.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }) + '. Reopen the tab to check again.'
      : 'As of the last refresh' + (sum.checked ? ', ' + new Date(sum.checked).toLocaleString(undefined, { weekday: 'short', hour: 'numeric', minute: '2-digit' }) : '') +
        '. It refreshes at 5:23 AM, 9:15 AM, 11 AM, 3 PM and 5:30 PM.'));
    var open = openAll.filter(function (b) { return b.style === 'tail'; });
    if (!open.length) s2.appendChild(h('p', 'muted', 'None of his open non-live bets fit a Tail style right now.'));
    open.forEach(function (b) {
      var s = h('div', 'slip');
      s.appendChild(h('span', 'grade A', b.sport === 'CBK' ? 'CBB' : 'NFL'));
      var mid = h('div'); mid.style.minWidth = '0';
      mid.appendChild(h('div', 'pick', b.d));
      mid.appendChild(h('div', 'meta', odds(b.o) + (b.boost ? ' boosted' : '') + ' · ' + b.u + 'u · ' + (b.b || 'book ?') + ' · ' + b.w));
      if (b.fair) mid.appendChild(h('div', 'plan ' + (b.fair.ok ? 'pos' : 'neg'), fairText(b)));
      if (b.boost) mid.appendChild(h('div', 'plan', 'Boosted price at ' + (b.b || 'his book') + '. Tail it if you can get the same boost.'));
      s.appendChild(mid);
      s2.appendChild(s);
    });
    var rest = openAll.filter(function (b) { return b.style !== 'tail'; });
    if (rest.length) {
      var det = h('details'), smry = h('summary', 'muted', rest.length + ' other open bet' + (rest.length === 1 ? '' : 's') + ' (not a Tail style)');
      det.appendChild(smry);
      rest.forEach(function (b) {
        var why = b.style === 'avoid' ? 'Avoid style' : 'No edge shown';
        det.appendChild(h('div', 'meta', (b.sport === 'CBK' ? 'CBB' : 'NFL') + ' · ' + b.d + ' · ' + odds(b.o) + (b.boost ? ' boosted' : '') + ' · ' + why +
          (b.fair ? ' · ' + (b.fair.ok ? 'price OK (min ' : 'price too short (needs ') + odds(b.fair.min) + ')' : '')));
      });
      s2.appendChild(det);
    }
    el.appendChild(s2);

    sum.sports.forEach(function (sp) {
      var s3 = h('section');
      s3.appendChild(h('h3', 'subh', sp.name + ' record'));
      s3.appendChild(table(['Bets', (sp.cur || '') + ' record', (sp.cur || '') + ' you', (sp.prev || '–') + ' record', (sp.prev || '–') + ' you', 'Verdict'],
        sp.rows.map(function (r) {
          return [r.name, rec(r.cur), cash(r.cur, S), rec(r.prev), cash(r.prev, S), { tag: r.verdict, cls: VERD[r.verdict] || '' }];
        })));
      if (sp.bands) {
        s3.appendChild(h('h3', 'subh', sp.name + ' straight bets by price'));
        s3.appendChild(table(['His price', 'Record', 'Hit %', 'Needed', 'You at $' + S, 'vs break-even', 'Worst price worth taking'],
          sp.bands.map(function (b) {
            var n = b.w + b.l;
            if (!n) return [b.name, '–', '–', '–', '–', '–', '–'];
            var e = (b.ratio - 1) * 100;
            return [b.name, b.w + '–' + b.l, (b.hit * 100).toFixed(0) + '%', (b.need * 100).toFixed(0) + '%', cash(b, S),
                    { text: (e >= 0 ? '+' : '−') + Math.abs(e).toFixed(0) + '%', cls: cls(e) },
                    odds(b.min) + ' (typical ' + odds(b.avg) + ')'];
          })));
      }
      el.appendChild(s3);
    });
    var f = h('footer');
    f.appendChild(h('p', null, 'Updated ' + sum.updated + '. Verdicts use this season and last together: Tail needs 100+ decided bets, ' +
      'profit beyond luck (about 90% confidence) and a profit in each season. Records are Brad’s own entries on his sheet; ' +
      'voids and pushes count as $0. Price bands: “vs break-even” is how much more (or less) often his straights at those prices win than ' +
      'the price needs, after pulling small bands toward break-even (as if each had 40 extra bets at no edge), so a 3–10 band moves only part way. ' +
      'The worst price worth taking is for a bet at the band’s typical price; each open bet gets its own.'));
    el.appendChild(f);
  }

  function start(store) {
    db = store;
    db.collection('mytails').onSnapshot(function (snap) {
      var m = {}; snap.docs.forEach(function (d) { var x = d.data(); if (x && x.price) m[d.id] = { price: x.price }; });
      mine = m; render();
    }, function () {});
    var timer = setTimeout(function () { if (!loaded) { failed = 'Brad’s record is taking too long to load. Reload the page to try again.'; render(); } }, 20000);
    // Same live-query form as the other tabs (a one-document collection).
    db.collection('bradsum').onSnapshot(function (snap) {
      clearTimeout(timer);
      try {
        var d = snap.docs.filter(function (x) { return x.id === 'latest'; })[0];
        sum = d ? d.data() : null; failed = '';
      }
      catch (e) { failed = 'Brad’s record could not be read (' + e.message + ').'; }
      loaded = true; render();
    }, function (e) { clearTimeout(timer); loaded = true; failed = 'Brad’s record could not be loaded' + (e && e.message ? ' (' + e.message + ')' : '') + '.'; render(); });
  }

  window.BradTab = { start: start, render: function (node) { if (node) { el = node; if (liveAt && Date.now() - liveAt > 60000) liveTried = false; } render(); } };
})();
