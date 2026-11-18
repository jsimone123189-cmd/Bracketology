/* "Brad Evans" tab: reads one small summary document (collection "bradsum", doc "latest") that the
 * daily job builds from his public sheet with tools/brad/brad_sheet.py. Every bet is stored in the
 * "brad" collection as the record; the page doesn't download them. */
(function () {
  'use strict';
  var sum = null, loaded = false, failed = '', el = null;

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

    var s2 = h('section');
    s2.appendChild(h('h3', 'subh', 'Open bets on his sheet worth a look'));
    var open = (sum.open || []).filter(function (b) { return b.style === 'tail'; });
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
    var rest = (sum.open || []).filter(function (b) { return b.style !== 'tail'; });
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

  function start(db) {
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

  window.BradTab = { start: start, render: function (node) { if (node) el = node; render(); } };
})();
