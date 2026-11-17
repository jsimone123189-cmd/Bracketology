/* Strategy lab: fixed strategies, tracked only on games after they were written down, against the
 * $50/month Betalytics subscription. Strategies are frozen on START: editing them later would let
 * hindsight back in, so add new ones with their own start date instead of changing these. */
(function () {
  'use strict';
  var START = '2026-11-18';      // first day counted as out-of-sample
  var COST = 50;                 // Betalytics subscription, $ per month
  var FADE_WIN = 100 / 110;      // the other side, assumed priced at -110

  function fadeU(r) { return r.res.r === 'W' ? -1 : r.res.r === 'L' ? FADE_WIN : 0; }
  function followU(r) { return r.res.u; }
  function day(r) { return new Date(r.g.t).toISOString().slice(0, 10); }

  var NCAAB = [
    { id: 'n1', name: 'Fade Betalytics on small spread favorites', how: 'When Betalytics takes a favorite of under 10 points, bet the underdog.',
      pick: function (r) { return r.key === 'sp' && r.p.line != null && r.p.line < 0 && r.p.line > -10; }, units: fadeU },
    { id: 'n2', name: 'Fade Betalytics overs', how: 'When Betalytics takes an over, bet the under.',
      pick: function (r) { return r.key === 'tot' && r.p.side === 'over'; }, units: fadeU },
    { id: 'n3', name: 'Follow spreads with a 2–5 pt edge', how: 'Betalytics spread picks whose edge over the price is 2 to 5 points.',
      pick: function (r) { return r.key === 'sp' && r.p.edge != null && r.p.edge >= 2 && r.p.edge < 5; }, units: followU },
    { id: 'n4', name: 'Follow A-grade spreads and totals', how: 'Betalytics A grades on spreads and totals (its Top bets).',
      pick: function (r) { return r.key !== 'ml' && r.p.grade === 'A'; }, units: followU },
    { id: 'n0', name: 'Baseline: follow every Betalytics pick', how: 'Every spread, total and moneyline Betalytics picks, as a yardstick.',
      pick: function () { return true; }, units: followU, baseline: true },
  ];
  var NFL = [
    { id: 'f1', name: 'Weekly TD card', how: 'Each week, the 8 likeliest anytime-TD overs with a Betalytics edge of 2–10 pts.',
      card: 8, pick: function (r) { return r.kind === 'prop' && r.key === 'player_anytime_td' && r.p.side === 'over' &&
        (r.p.hit - r.p.mkt) >= 0.02 && (r.p.hit - r.p.mkt) < 0.10; }, units: followU },
    { id: 'f2', name: 'Follow A-grade NFL spreads and totals', how: 'NFL game picks Betalytics shows as A, spreads and totals only.',
      pick: function (r) { return r.kind === 'game' && r.key !== 'ml' && r.p.grade === 'A'; }, units: followU },
    { id: 'f0', name: 'Baseline: every NFL game pick', how: 'Every NFL spread, total and moneyline Betalytics picks.',
      pick: function (r) { return r.kind === 'game'; }, units: followU, baseline: true },
  ];

  function applyCard(list, n) {
    // the n likeliest per NFL week (week = the game id's season_week prefix)
    var byWk = {};
    list.forEach(function (r) { var wk = String(r.id).split('_').slice(0, 2).join('_'); (byWk[wk] = byWk[wk] || []).push(r); });
    var out = [];
    Object.keys(byWk).forEach(function (wk) {
      out = out.concat(byWk[wk].sort(function (a, b) { return b.p.hit - a.p.hit; }).slice(0, n));
    });
    return out;
  }

  function score(s, rows) {
    var mine = rows.filter(function (r) { return !r.void && s.pick(r); });
    if (s.card) mine = applyCard(mine, s.card);
    var graded = mine.filter(function (r) { return r.res; });
    var split = function (list) {
      var u = 0, w = 0, l = 0, days = {};
      list.forEach(function (r) { var x = s.units(r); u += x; if (x > 0) w++; else if (x < 0) l++; days[day(r)] = 1; });
      return { n: list.length, w: w, l: l, u: u, days: Object.keys(days).length };
    };
    return {
      before: split(graded.filter(function (r) { return day(r) < START; })),
      after: split(graded.filter(function (r) { return day(r) >= START; })),
      upcoming: mine.filter(function (r) { return !r.res && Date.parse(r.g.t) > Date.now(); }).length,
    };
  }

  function h(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function money(x) { return (x < 0 ? '−$' : '$') + Math.abs(x).toFixed(0); }
  function rec(x) { return x.n ? x.w + '–' + x.l : '–'; }
  function roi(x) { return x.n ? ((x.u / x.n) * 100).toFixed(1) + '%' : '–'; }

  function unit() {
    try { var v = parseFloat(localStorage.getItem('lab-unit')); if (v > 0) return v; } catch (_) {}
    return 10;
  }

  function render(el, ncaabRows, nflRows) {
    el.innerHTML = '';
    var U = unit();
    var intro = h('section');
    intro.appendChild(h('h2', null, 'Is Betalytics worth $50 a month?'));
    intro.appendChild(h('p', 'muted lede', 'A short list of strategies, written down on ' + START + ' from the patterns found so far. Only games from that ' +
      'day on count toward the verdict, so no search can cherry-pick the results. Each strategy’s profit pace is compared with the ' +
      '$' + COST + ' subscription at your bet size. Earlier results are shown for context only.'));
    var row = h('div', 'filters');
    var lab = h('label', 'flabel', 'Your bet size per pick');
    var inp = h('input'); inp.type = 'number'; inp.min = '1'; inp.step = '1'; inp.id = 'labUnit'; inp.value = String(U);
    inp.style.cssText = 'width:90px;font:inherit;padding:6px 8px;border-radius:6px;border:1px solid var(--line);background:var(--surface);color:var(--ink)';
    inp.onchange = function () { try { localStorage.setItem('lab-unit', String(parseFloat(inp.value) || 10)); } catch (_) {} render(el, ncaabRows, nflRows); };
    lab.appendChild(document.createTextNode(' $')); row.appendChild(lab); row.appendChild(inp); intro.appendChild(row);
    el.appendChild(intro);

    var verdictBox = h('div', 'note');
    el.appendChild(verdictBox);
    var best = null;

    [['College basketball', NCAAB, ncaabRows], ['NFL', NFL, nflRows]].forEach(function (grp) {
      var sec = h('section');
      sec.appendChild(h('h3', 'subh', grp[0]));
      var wrap = h('div', 'scroll'), t = h('table'), head = h('tr');
      ['Strategy', 'Since ' + START.slice(5), 'Units', 'ROI', 'Per month at $' + U, 'Before (context)', 'Upcoming'].forEach(function (c) { head.appendChild(h('th', null, c)); });
      var th = h('thead'); th.appendChild(head); t.appendChild(th);
      var tb = h('tbody');
      grp[1].forEach(function (s) {
        var sc = score(s, grp[2] || []);
        var a = sc.after, perMonth = a.days ? a.u / a.days * 30 * U : null;
        if (!s.baseline && a.n >= 30 && (best == null || perMonth > best.perMonth)) best = { s: s, a: a, perMonth: perMonth };
        var tr = h('tr');
        var c0 = h('td'); c0.appendChild(h('div', null, s.name)); var sm = h('div', 'muted', s.how); sm.style.cssText = 'font-size:11px;white-space:normal;max-width:260px;font-family:var(--body);font-weight:400'; c0.appendChild(sm);
        tr.appendChild(c0);
        [rec(a), a.n ? (a.u > 0 ? '+' : '') + a.u.toFixed(1) : '–', roi(a), perMonth == null ? '–' : money(perMonth),
         sc.before.n ? rec(sc.before) + ', ' + roi(sc.before) : '–', String(sc.upcoming)].forEach(function (c, i) {
          var td = h('td', null, c);
          if ((i === 1 || i === 3) && a.n) td.className = a.u > 0 ? 'pos' : 'neg';
          if (i === 3 && perMonth != null) td.className = perMonth > COST ? 'pos' : 'neg';
          tr.appendChild(td);
        });
        tb.appendChild(tr);
      });
      t.appendChild(tb); wrap.appendChild(t); sec.appendChild(wrap);
      el.appendChild(sec);
    });

    var msg;
    if (!best) {
      msg = 'Not enough games since ' + START + ' to judge yet. Each strategy needs 30+ bets after that date. Until then, the honest ' +
        'answer from the data so far: following Betalytics as-is has lost money (college moneylines especially), its college A grades on ' +
        'spreads and totals have lost too (about \u22129%), and the only patterns that held up in both halves of the data are fading its small spread ' +
        'favorites (college) and its 2–10 pt anytime-TD overs (NFL, matching its own backtest). Give it about four weeks: if no ' +
        'strategy here is beating $' + COST + ' a month by mid-December, it isn’t paying for itself.';
    } else if (best.perMonth > COST) {
      msg = 'Best so far: “' + best.s.name + '”, ' + rec(best.a) + ' since ' + START + ', about ' + money(best.perMonth) +
        ' a month at $' + U + ' a bet, above the $' + COST + ' cost. Keep watching the sample: ' + best.a.n + ' bets is ' +
        (best.a.n < 200 ? 'still small, so a lucky streak can’t be ruled out.' : 'enough to start trusting it.');
    } else {
      msg = 'No strategy is beating the $' + COST + ' cost since ' + START + '. Best: “' + best.s.name + '” at about ' +
        money(best.perMonth) + ' a month at $' + U + ' a bet. If that holds for a few more weeks, Betalytics isn’t paying for itself.';
    }
    verdictBox.textContent = msg;
  }

  window.Lab = { render: render, START: START };
})();
