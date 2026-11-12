/* Shared "Recommended bets" and "Real edge" rendering for the Betalytics Ledger tabs. */
(function () {
  'use strict';
  var VERDICT = { follow: ['Follow', 'up'], fade: ['Fade', 'fade'], avoid: ['Avoid', 'down'], none: ['No edge', ''], few: ['Too few', ''] };

  function h(tag, cls, text) {
    var e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }
  function pct(x) { return x == null ? '–' : (x * 100).toFixed(1) + '%'; }
  function pts(x) { return x == null ? '–' : (x > 0 ? '+' : x < 0 ? '−' : '') + Math.abs(x * 100).toFixed(1); }

  /**
   * box: container element. rec: Ledger.recommend(...) result.
   * o: {bet(item) -> bet text, meta(item) -> game/time line, groupName(key) -> label, order(keys) -> sorted keys}
   */
  function render(box, rec, o) {
    box.innerHTML = '';
    var list = h('div', 'recs');
    if (!rec.picks.length) {
      list.appendChild(h('p', 'muted', 'No bets recommended right now. No group of Betalytics picks has shown a real edge ' +
        'either way yet. The table below shows how each group is hitting and how close it is to a verdict.'));
    }
    rec.picks.forEach(function (it) {
      var s = h('div', 'slip');
      var v = VERDICT[it.action];
      s.appendChild(h('span', 'grade ' + (it.action === 'follow' ? 'A' : 'B'), it.action === 'follow' ? '✓' : '⇄'));
      var mid = h('div'); mid.style.minWidth = '0';
      mid.appendChild(h('div', 'pick', o.bet(it)));
      mid.appendChild(h('div', 'meta', o.meta(it)));
      var e = it.e, edge = it.action === 'fade' ? e.fadeEdge : e.edge;
      var why = o.groupName(it.group) + ': ' + e.w + '–' + e.l + ' tracked (' + pct(e.raw) + '). Estimated real hit rate ' +
        pct(e.est) + (it.action === 'fade' ? ', so the other side wins about ' + pct(1 - e.est) : '') +
        '; ' + pts(edge) + ' pts over break-even.';
      mid.appendChild(h('div', 'meta', why));
      s.appendChild(mid);
      var res = h('div', 'res');
      res.appendChild(h('span', 'tag rec-' + it.action, v[0]));
      res.appendChild(h('span', 'num pos', pts(edge) + ' pts'));
      s.appendChild(res);
      list.appendChild(s);
    });
    box.appendChild(list);

    var keys = o.order(Object.keys(rec.groups));
    var wrap = h('div', 'scroll');
    var t = h('table'), head = h('tr');
    ['Group', 'Decided', 'Record', 'Hit %', 'Units', 'Est. long-run hit', 'Est. edge following', 'Est. edge fading', 'Verdict'].forEach(function (c) { head.appendChild(h('th', null, c)); });
    var thead = h('thead'); thead.appendChild(head); t.appendChild(thead);
    var tb = h('tbody');
    keys.forEach(function (k) {
      var e = rec.groups[k], tr = h('tr');
      var u = (e.units > 0 ? '+' : e.units < 0 ? '−' : '') + Math.abs(e.units).toFixed(1);
      [o.groupName(k), String(e.n), e.w + '–' + e.l, pct(e.raw), u, e.be == null ? 'ROI ' + pts(e.est) : pct(e.est),
       pts(e.edge), e.fadeEdge == null ? '–' : pts(e.fadeEdge)].forEach(function (c, i) {
        var td = h('td', null, c);
        if (i === 4 && Math.abs(e.units) > 1e-9) td.className = e.units > 0 ? 'pos' : 'neg';
        if (i === 6 && e.n >= 100) td.className = e.edge > 0 ? 'pos' : 'neg';
        tr.appendChild(td);
      });
      var vd = VERDICT[e.verdict], td = h('td'); td.appendChild(h('span', 'sig ' + vd[1], vd[0])); tr.appendChild(td);
      tb.appendChild(tr);
    });
    t.appendChild(tb); wrap.appendChild(t);
    var cap = h('p', 'muted lede', 'Record, Hit % and Units are what actually happened (1 unit per pick). The "Est." columns are my ' +
      'long-run estimate: each group starts as if it already had 100 wins and 100 losses, so a hot or cold streak over a few dozen ' +
      'games barely moves it and a real edge has to show up over hundreds. Est. edge is percentage points above break-even ' +
      '(fading assumes the other side at −110). A verdict needs 100+ decided picks and 80% confidence.');
    box.appendChild(h('h3', 'subh', 'Real edge by group'));
    box.appendChild(cap);
    box.appendChild(wrap);
  }

  window.LedgerRecs = { render: render };
})();
