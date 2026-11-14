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

  function lineStr(key, side, line) {
    if (key === 'sp') return (line > 0 ? '+' : line < 0 ? '−' : '') + (line === 0 ? 'PK' : Math.abs(line));
    return (side === 'over' ? 'Over ' : 'Under ') + line;
  }

  /** "When to bet" and "worst line" for a recommended pick, from Ledger.betPlan. */
  function planText(it) {
    var pl = Ledger.betPlan(it), mv = pl.move, parts = [];
    var size = mv ? Math.abs(mv.mean).toFixed(2) + ' pts on average over ' + mv.n + ' picks' : '';
    if (pl.when === 'early') {
      parts.push('When: bet early, as soon as Betalytics posts. Lines in this group move against your side by tip (' + size + ').');
    } else if (pl.when === 'late') {
      parts.push('When: wait until close to tip. Lines in this group drift toward your side (' + size + ').');
    } else if (mv && mv.n >= 30) {
      parts.push('When: timing hasn’t mattered for this group (lines moved ' + (mv.mean < 0 ? '−' : '') + Math.abs(mv.mean).toFixed(2) + ' pts on average, ' +
        mv.same + ' of ' + mv.n + ' closed at the same number). Bet when convenient and shop for the best number.');
    } else {
      parts.push('When: not enough closing-line data for this group yet. Bet when convenient and shop for the best number.');
    }
    if (pl.bet) {
      var key = it.r.key;
      parts.push(pl.worst != null
        ? 'Worst line to take: ' + lineStr(key, pl.bet.side, pl.worst) + ' (the estimated edge is gone past that).'
        : 'Only at ' + lineStr(key, pl.bet.side, pl.bet.line) + ' or better; the estimated edge is too thin to give up a half point.');
    }
    return parts.join(' ');
  }

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
      mid.appendChild(h('div', 'plan', planText(it)));
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
    ['Group', 'Decided', 'Record', 'Hit %', 'Units', 'Est. long-run hit', 'Est. edge following', 'Est. edge fading', 'Line move', 'Verdict'].forEach(function (c) { head.appendChild(h('th', null, c)); });
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
      var mv = e.move || { n: 0 };
      tr.appendChild(h('td', null, mv.n ? (mv.mean > 0 ? '+' : mv.mean < 0 ? '−' : '') + Math.abs(mv.mean).toFixed(2) + ' (' + mv.n + ')' : '–'));
      var vd = VERDICT[e.verdict], td = h('td'); td.appendChild(h('span', 'sig ' + vd[1], vd[0])); tr.appendChild(td);
      tb.appendChild(tr);
    });
    t.appendChild(tb); wrap.appendChild(t);
    var cap = h('p', 'muted lede', 'Record, Hit % and Units are what actually happened (1 unit per pick). The "Est." columns are my ' +
      'long-run estimate: each group starts as if it already had 100 wins and 100 losses, so a hot or cold streak over a few dozen ' +
      'games barely moves it and a real edge has to show up over hundreds. Est. edge is percentage points above break-even ' +
      '(fading assumes the other side at −110). A verdict needs 100+ decided picks and 80% confidence. Line move is how far the ' +
      'line moved from Betalytics’ number to the close, in points (picks with a closing line in brackets); plus means ' +
      'Betalytics’ side got more expensive by tip, so following it pays to bet early and fading it pays to wait.');
    box.appendChild(h('h3', 'subh', 'Real edge by group'));
    box.appendChild(cap);
    box.appendChild(wrap);
  }

  window.LedgerRecs = { render: render };
})();
