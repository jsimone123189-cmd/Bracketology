/* Strategy lab: when to bet Betalytics' college picks.
 * 1) By how long before tip the version the tracker graded was posted (its model run time).
 * 2) Early vs latest: games where the pick changed during the day, graded both ways. */
(function () {
  'use strict';
  function h(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  var LEAD = [['14+ hours before tip', 14, 1e9], ['9–14 hours', 9, 14], ['5–9 hours', 5, 9], ['2–5 hours', 2, 5], ['Under 2 hours', 0, 2]];

  function tally(list, resOf) {
    var x = { w: 0, l: 0, u: 0, c: 0, cn: 0 };
    list.forEach(function (r) {
      var res = resOf(r); if (!res || res.r === 'P') return;
      if (res.r === 'W') x.w++; else x.l++;
      x.u += res.u;
      if (r.clv && r.clv.pts != null && resOf === now) { x.c += r.clv.pts; x.cn++; }
    });
    return x;
  }
  function now(r) { return r.res; }
  function early(r) { return r.first ? r.first.res : r.res; }
  function fmt(x) { return x.w + x.l ? x.w + '–' + x.l : '–'; }
  function hit(x) { return x.w + x.l ? (100 * x.w / (x.w + x.l)).toFixed(1) + '%' : '–'; }
  function u(x) { return x.w + x.l ? (x.u > 0 ? '+' : x.u < 0 ? '−' : '') + Math.abs(x.u).toFixed(1) + 'u' : '–'; }
  function clv(x) { return x.cn ? (x.c >= 0 ? '+' : '−') + Math.abs(x.c / x.cn).toFixed(2) + ' (' + x.cn + ')' : '–'; }

  function table(head, rows) {
    var wrap = h('div', 'scroll'), t = h('table'), tr = h('tr');
    head.forEach(function (c) { tr.appendChild(h('th', null, c)); });
    var th = h('thead'); th.appendChild(tr); t.appendChild(th);
    var tb = h('tbody');
    rows.forEach(function (r) { var row = h('tr'); r.forEach(function (c) { row.appendChild(h('td', null, c)); }); tb.appendChild(row); });
    t.appendChild(tb); wrap.appendChild(t); return wrap;
  }

  function render(el, rows) {
    el.innerHTML = '';
    var sides = rows.filter(function (r) { return r.key !== 'ml'; });
    var bsp = sides.filter(function (r) { return r.key === 'sp' && r.p.grade === 'B'; });
    var sec = h('section');
    sec.appendChild(h('h2', null, 'When to bet Betalytics'));
    sec.appendChild(h('p', 'muted lede', 'College spreads and totals, by how long before tip Betalytics posted the version the tracker graded ' +
      '(the latest one you captured). Line move is how far the closing line moved toward Betalytics’ side, in points: plus means ' +
      'their number was better than the close, so betting at that time beat the market.'));
    var lead = function (r) { return (Date.parse(r.g.t) - Date.parse(r.g.at)) / 36e5; };
    sec.appendChild(table(['Posted', 'All: record', 'Hit %', 'Units', 'Line move', 'B spreads: record', 'Hit %', 'Line move'],
      LEAD.map(function (b) {
        var inB = function (r) { var l = lead(r); return l >= b[1] && l < b[2]; };
        var a = tally(sides.filter(inB), now), x = tally(bsp.filter(inB), now);
        return [b[0], fmt(a), hit(a), u(a), clv(a), fmt(x), hit(x), clv(x)];
      })));

    var changed = sides.filter(function (r) { return r.first && r.res; });
    var cb = changed.filter(function (r) { return r.key === 'sp' && (r.p.grade === 'B' || r.first.p.grade === 'B'); });
    sec.appendChild(h('h3', 'subh', 'Early vs latest version'));
    if (!changed.length) {
      sec.appendChild(h('p', 'muted', 'Collecting from Nov 18: when Betalytics changes a pick during the day (line, price, side or edge), ' +
        'the tracker now keeps the first version you captured as well as the latest, and grades both. Results appear here as those games finish.'));
    } else {
      var e = tally(changed, early), l = tally(changed, now), eb = tally(cb, early), lb = tally(cb, now);
      sec.appendChild(table(['Games where the pick changed', 'First version', 'Hit %', 'Units', 'Latest version', 'Hit %', 'Units'],
        [['All spreads and totals (' + changed.length + ')', fmt(e), hit(e), u(e), fmt(l), hit(l), u(l)],
         ['B spreads, either version (' + cb.length + ')', fmt(eb), hit(eb), u(eb), fmt(lb), hit(lb), u(lb)]]));
      sec.appendChild(h('p', 'muted lede', 'If the first versions keep beating the latest, bet as soon as Betalytics posts; if the latest win more, wait.'));
    }
    el.appendChild(sec);
  }
  window.Timing = { render: render };
})();
