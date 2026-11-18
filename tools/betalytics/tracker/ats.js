/* ATS form study (Strategy lab): does a team's recent record against the spread predict its next cover?
 * College: every game's consensus closing spread (collection "lines", from closing.py) and final score
 * (collection "atsscores", from ats_scores.py), collected from 2026-11-18. NFL: a fixed 27-season result. */
(function () {
  'use strict';
  var lines = {}, scores = {}, el = null;

  // NFL regular seasons 1999-2025 (nflverse closing spreads): how the team did ATS in its NEXT game.
  var NFL = [
    ['Won 5+ ATS in a row', 137, 145], ['Won 3+ ATS in a row', 672, 699], ['4–0 ATS last 4', 304, 312],
    ['4–0 ATS, covering by 10+ on average', 147, 153], ['Covering by 7+ on average, last 4', 746, 761],
    ['Covered 80%+ this season (6+ games)', 110, 120],
    ['Lost 3+ ATS in a row', 692, 660], ['Lost 5+ ATS in a row', 144, 111], ['Missing by 7+ on average, last 4', 755, 729],
    ['Covered 20% or less this season (6+ games)', 122, 105],
  ];

  var GROUPS = [
    ['hot3', 'Won 3+ ATS in a row', 'hot'], ['hot4', '4–0 ATS last 4', 'hot'], ['big', 'Covering by 7+ on average, last 4', 'hot'],
    ['cold3', 'Lost 3+ ATS in a row', 'cold'], ['cold4', '0–4 ATS last 4', 'cold'], ['bad', 'Missing by 7+ on average, last 4', 'cold'],
  ];

  function h(tag, cls, text) { var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function pct(w, l) { return w + l ? (100 * w / (w + l)).toFixed(1) + '%' : '–'; }

  /** Which form groups a team is in, from its earlier cover margins (oldest first). */
  function formOf(m) {
    var out = [], st = 0;
    for (var i = m.length - 1; i >= 0 && m[i] > 0; i--) st++;
    var cs = 0;
    for (var j = m.length - 1; j >= 0 && m[j] < 0; j--) cs++;
    if (st >= 3) out.push('hot3');
    if (cs >= 3) out.push('cold3');
    if (m.length >= 4) {
      var last = m.slice(-4), avg = last.reduce(function (a, b) { return a + b; }, 0) / 4;
      var w = last.filter(function (x) { return x > 0; }).length;
      if (w === 4) out.push('hot4');
      if (w === 0 && last.every(function (x) { return x < 0; })) out.push('cold4');
      if (avg >= 7) out.push('big');
      if (avg <= -7) out.push('bad');
    }
    return { groups: out, streak: st || -cs, n: m.length };
  }

  /** Walk every graded game in time order; tally how teams in each form group did next time out. */
  function study() {
    var games = [];
    Object.keys(lines).forEach(function (d) {
      var L = lines[d] || {}, S = scores[d] || {};
      Object.keys(L).forEach(function (id) { games.push({ id: id, g: L[id], s: S[id] }); });
    });
    games.sort(function (a, b) { return Date.parse(a.g.t) - Date.parse(b.g.t); });
    var hist = {}, tally = {}, upcoming = [], now = Date.now(), graded = 0;
    GROUPS.forEach(function (g) { tally[g[0]] = { w: 0, l: 0 }; });
    games.forEach(function (x) {
      var g = x.g, sides = [[g.h, 1], [g.a, -1]];
      if (!x.s) {
        if (Date.parse(g.t) > now - 3 * 3600e3) sides.forEach(function (sd) {
          var f = formOf(hist[sd[0]] || []);
          if (f.groups.length) upcoming.push({ team: sd[0], opp: sd[0] === g.h ? g.a : g.h, t: g.t, sp: g.sp * sd[1], f: f });
        });
        return;
      }
      graded++;
      var homeM = (x.s.hs - x.s.as) + g.sp;            // home cover margin; sp is the home spread
      sides.forEach(function (sd) {
        var m = homeM * sd[1], f = formOf(hist[sd[0]] || []);
        if (m !== 0) f.groups.forEach(function (k) { if (m > 0) tally[k].w++; else tally[k].l++; });
        (hist[sd[0]] = hist[sd[0]] || []).push(m);
      });
    });
    return { tally: tally, upcoming: upcoming, graded: graded };
  }

  function table(head, rows) {
    var wrap = h('div', 'scroll'), t = h('table'), tr = h('tr');
    head.forEach(function (c) { tr.appendChild(h('th', null, c)); });
    var th = h('thead'); th.appendChild(tr); t.appendChild(th);
    var tb = h('tbody');
    rows.forEach(function (r) { var row = h('tr'); r.forEach(function (c) { row.appendChild(h('td', null, c)); }); tb.appendChild(row); });
    t.appendChild(tb); wrap.appendChild(t);
    return wrap;
  }

  /** Units betting ON the group's teams at −110 (fading is roughly the mirror), and a z-score against 50%. */
  function fadeCells(w, l) {
    var n = w + l; if (!n) return ['–', '–'];
    var u = w * (100 / 110) - l, z = ((w / n) - 0.5) / Math.sqrt(0.25 / n);
    return [(u > 0 ? '+' : u < 0 ? '−' : '') + Math.abs(u).toFixed(1) + 'u', (z >= 0 ? '+' : '−') + Math.abs(z).toFixed(1) + 'σ'];
  }

  function render() {
    if (!el) return;
    el.innerHTML = '';
    var r = study();
    var sec = h('section');
    sec.appendChild(h('h2', null, 'ATS form'));
    sec.appendChild(h('p', 'muted lede', 'Does a team on a run against the spread keep covering? Hot means it has been covering, cold means it ' +
      'hasn’t. Each row is how those teams did ATS in their next game. Books adjust their lines to recent results, so the usual ' +
      'finding is that hot teams end up slightly overpriced and cold teams slightly underpriced. Signal compares the cover rate with a coin flip; you need about 52.4% just to break even at −110.'));

    sec.appendChild(h('h3', 'subh', 'NFL, 1999–2025 regular seasons'));
    sec.appendChild(table(['Team before the game', 'Next game ATS', 'Covered', 'Betting on them (−110)', 'Signal'],
      NFL.map(function (x) { var f = fadeCells(x[1], x[2]); return [x[0], x[1] + '–' + x[2], pct(x[1], x[2]), f[0], f[1]]; })));
    sec.appendChild(h('p', 'muted lede', 'Over 27 seasons, hot teams covered about 49% next time out: their streak tells you nothing ' +
      'you can bet. Teams that had lost 5+ ATS in a row covered 56.5% (255 games, +2.1σ). That is the only hint of an edge, and ' +
      'with ten rows tested, one reading of 2σ can be luck.'));

    sec.appendChild(h('h3', 'subh', 'College basketball, tracked from Nov 18'));
    sec.appendChild(h('p', 'muted lede', r.graded + ' games graded so far (every D-I game with a line, not only Betalytics’). ' +
      'A form group needs 3–4 earlier games per team, so this fills in over the next few weeks, and a verdict needs several hundred games per row.'));
    sec.appendChild(table(['Team before the game', 'Next game ATS', 'Covered', 'Betting on them (−110)', 'Signal'],
      GROUPS.map(function (g) { var t = r.tally[g[0]], f = fadeCells(t.w, t.l); return [g[1], t.w + t.l ? t.w + '–' + t.l : '–', pct(t.w, t.l), f[0], f[1]]; })));

    if (r.upcoming.length) {
      sec.appendChild(h('h3', 'subh', 'Teams in form, next games'));
      r.upcoming.sort(function (a, b) { return Date.parse(a.t) - Date.parse(b.t); });
      r.upcoming.slice(0, 30).forEach(function (u) {
        var s = h('div', 'slip');
        s.appendChild(h('span', 'grade ' + (u.f.streak > 0 ? 'A' : 'D'), u.f.streak > 0 ? 'Hot' : 'Cold'));
        var mid = h('div'); mid.style.minWidth = '0';
        mid.appendChild(h('div', 'pick', u.team + ' ' + (u.sp > 0 ? '+' : u.sp < 0 ? '−' : '') + (u.sp === 0 ? 'PK' : Math.abs(u.sp)) + ' vs ' + u.opp));
        var names = u.f.groups.map(function (k) { return GROUPS.filter(function (g) { return g[0] === k; })[0][1]; });
        mid.appendChild(h('div', 'meta', new Date(u.t).toLocaleString(undefined, { weekday: 'short', hour: 'numeric', minute: '2-digit' }) + ' · ' + names.join(' · ')));
        s.appendChild(mid);
        sec.appendChild(s);
      });
      sec.appendChild(h('p', 'muted lede', 'For information only until the college table shows an edge.'));
    }
    el.appendChild(sec);
  }

  function start(db) {
    db.collection('lines').onSnapshot(function (snap) {
      lines = {}; snap.docs.forEach(function (d) { var b = d.data(); if (b && b.games) lines[d.id] = b.games; }); render();
    }, function () {});
    db.collection('atsscores').onSnapshot(function (snap) {
      scores = {}; snap.docs.forEach(function (d) { var b = d.data(); if (b && b.games) scores[d.id] = b.games; }); render();
    }, function () {});
  }

  window.AtsForm = { start: start, render: function (node) { el = node; render(); }, formOf: formOf };
})();
