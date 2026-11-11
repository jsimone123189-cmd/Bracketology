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
    ['Group', 'Decided', 'Record', 'Hit %', 'Est. real', 'Following', 'Fading', 'Verdict'].forEach(function (c) { head.appendChild(h('th', null, c)); });
    var thead = h('thead'); thead.appendChild(head); t.appendChild(thead);
    var tb = h('tbody');
    keys.forEach(function (k) {
      var e = rec.groups[k], tr = h('tr');
      [o.groupName(k), String(e.n), e.w + '–' + e.l, pct(e.raw), e.be == null ? 'ROI ' + pts(e.est) : pct(e.est),
       pts(e.edge), e.fadeEdge == null ? '–' : pts(e.fadeEdge)].forEach(function (c, i) {
        var td = h('td', null, c);
        if (i === 5 && e.n >= 100) td.className = e.edge > 0 ? 'pos' : 'neg';
        tr.appendChild(td);
      });
      var vd = VERDICT[e.verdict], td = h('td'); td.appendChild(h('span', 'sig ' + vd[1], vd[0])); tr.appendChild(td);
      tb.appendChild(tr);
    });
    t.appendChild(tb); wrap.appendChild(t);
    var cap = h('p', 'muted lede', 'How Betalytics’ picks are really hitting. "Est. real" pulls each group toward 50% until ' +
      'its sample is large, because the betting market is hard to beat and small samples mislead. "Following" and "Fading" ' +
      'are points over break-even each way (fading assumes the other side at −110). A verdict needs 100+ decided picks ' +
      'and 80% confidence.');
    box.appendChild(h('h3', 'subh', 'Real edge by group'));
    box.appendChild(cap);
    box.appendChild(wrap);
  }

  window.LedgerRecs = { render: render };
})();
