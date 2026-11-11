/* NFL tab of the Betalytics Ledger: game picks and player props.
 * Stored in collections nflgames/<season-week>, nflprops/<game id>, nflresults/<season-week>. */
(function () {
  'use strict';
  var MK = {
    player_anytime_td: 'Anytime TD', player_receptions: 'Receptions', player_reception_yds: 'Rec yds',
    player_rush_attempts: 'Rush att', player_rush_yds: 'Rush yds', player_pass_attempts: 'Pass att',
    player_pass_completions: 'Completions', player_pass_interceptions: 'INTs', player_pass_tds: 'Pass TDs',
    player_pass_yds: 'Pass yds'
  };
  var GK = { sp: 'Spread', tot: 'Total', ml: 'Moneyline' };
  var data = { games: {}, props: {}, results: {} };
  var st = { view: 'games', rec: 'all', market: 'all', shownUp: 10, shownDone: 30 };
  var db = null, el = null;
  var U = function () { return window.LedgerUI; };

  function h(tag, attrs, text) {
    var e = document.createElement(tag);
    Object.keys(attrs || {}).forEach(function (k) { if (k === 'className') e.className = attrs[k]; else e.setAttribute(k, attrs[k]); });
    if (text != null) e.textContent = text;
    return e;
  }

  function layout() {
    el = document.getElementById('viewNfl');
    el.innerHTML =
      '<div class="filters" role="group" aria-label="NFL filters">' +
      '<div><span class="flabel">Show</span><span class="seg" id="nView"></span></div>' +
      '<div><span class="flabel">Picks</span><span class="seg" id="nRec"></span></div>' +
      '<div id="nMarketWrap"><span class="flabel">Market</span><span class="seg" id="nMarket"></span></div></div>' +
      '<section><h2>Recommended bets</h2><p class="muted lede">My calls from how Betalytics’ NFL picks have actually hit in your tracked results. ' +
      'Follow = their picks in that group have a proven edge; Fade = bet the other side.</p><div id="nRecs"></div></section>' +
      '<section><h2>Betalytics’ picks this week</h2><p class="muted lede" id="nLede"></p><div id="nUp" class="day"></div></section>' +
      '<div class="strip" aria-live="polite">' +
      '<div><div class="k">Record</div><div class="v" id="nRecd">–</div><div class="d" id="nRecD">&nbsp;</div></div>' +
      '<div><div class="k">Units</div><div class="v" id="nUnits">–</div><div class="d">1 unit per pick</div></div>' +
      '<div><div class="k">ROI</div><div class="v" id="nRoi">–</div><div class="d" id="nRoiD">&nbsp;</div></div>' +
      '<div><div class="k">Hit rate</div><div class="v" id="nHit">–</div><div class="d" id="nHitD">&nbsp;</div></div></div>' +
      '<section><h2 id="nBreakTitle">Breakdown</h2><div class="scroll"><table><thead><tr><th>Group</th><th>Picks</th>' +
      '<th>Record</th><th>Hit %</th><th>Model %</th><th>Units</th><th>ROI</th><th>Signal</th></tr></thead>' +
      '<tbody id="nBreak"></tbody></table></div></section>' +
      '<section><h2>Results</h2><div id="nDone" class="day"></div></section>' +
      '<section><h2>Betalytics’ own backtest</h2><div id="nBt" class="muted"></div></section>' +
      '<footer><p>Game picks are the Betalytics model’s side in each market. Early in the week Betalytics shows no prices, ' +
      'so those picks are graded at −110 and marked “−110 assumed”; picks priced by Betalytics use its price. ' +
      'Props: the side where Betalytics’ chance beats the market’s, at the listed book price. “Recommended” means Betalytics flagged it as an edge. ' +
      'A player who doesn’t play is void. Graded from nflverse scores and player stats, usually the day after each game. ' +
      'Upload a capture close to kickoff for Betalytics’ final numbers; a newer pre-kickoff upload replaces the older pick.</p></footer>';
  }

  function seg(id, key, opts) {
    var box = document.getElementById(id);
    box.innerHTML = '';
    opts.forEach(function (o) {
      var b = h('button', { type: 'button', id: id + '-' + o[0], 'aria-pressed': String(st[key] === o[0]) }, o[1]);
      b.onclick = function () { st[key] = o[0]; if (key === 'view') st.market = 'all'; st.shownUp = 10; st.shownDone = 30; render(); };
      box.appendChild(b);
    });
  }

  function edgeOf(r) {
    if (r.kind === 'prop') return r.p.hit - r.p.mkt;
    return r.p.hit - 1 / (1 + Ledger.profit(r.p.price));
  }

  function pickText(r) {
    var u = U(), p = r.p;
    if (r.kind === 'prop') return p.n + ' ' + p.side + ' ' + p.line + ' ' + (MK[p.mk] || p.mk).toLowerCase() + ' (' + u.fmtOdds(p.price) + ')';
    var team = p.side === 'home' ? r.g.h : p.side === 'away' ? r.g.a : (p.side === 'over' ? 'Over' : 'Under');
    var price = p.priced ? u.fmtOdds(p.price) : '−110 assumed';
    if (r.key === 'ml') return team + ' ML ' + u.fmtOdds(p.price);
    if (r.key === 'sp') return team + ' ' + u.fmtLine(p.line) + ' (' + price + ')';
    return team + ' ' + p.line + ' (' + price + ')';
  }

  function slip(r) {
    var u = U(), now = Date.now(), p = r.p, d = new Date(r.g.t);
    var s = h('div', { className: 'slip' });
    s.appendChild(h('span', { className: 'grade ' + (p.grade || 'x'), title: 'Betalytics price grade' }, p.grade || '–'));
    var mid = h('div'); mid.style.minWidth = '0';
    mid.appendChild(h('div', { className: 'pick' }, pickText(r)));
    var game = r.kind === 'prop' ? r.id.split('_').slice(2).join(' @ ') : r.g.a + ' @ ' + r.g.h;
    var sc = null;
    Object.keys(data.results).some(function (wk) { sc = ((data.results[wk] || {}).games || {})[r.id]; return !!sc; });
    var when = d.toLocaleDateString(undefined, { weekday: 'short' }) + ' ' + d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' });
    var meta = game + '  ' + (sc ? sc.as + '–' + sc.hs : when) + ' · ' + (r.kind === 'prop' ? MK[p.mk] || p.mk : GK[r.key]);
    if (r.kind === 'prop') meta += ' · model ' + Math.round(p.hit * 100) + '% vs market ' + Math.round(p.mkt * 100) + '%' + (p.book ? ' · ' + p.book : '');
    else meta += ' · ' + Math.round(p.hit * 100) + '% to hit';
    if (r.res && r.res.v != null) meta += ' · actual ' + r.res.v;
    mid.appendChild(h('div', { className: 'meta' }, meta));
    s.appendChild(mid);
    var res = h('div', { className: 'res' });
    if (r.void) res.appendChild(h('span', { className: 'tag open' }, 'Void'));
    else if (r.res) res.appendChild(h('span', { className: 'tag ' + r.res.r }, { W: 'Win', L: 'Loss', P: 'Push' }[r.res.r]));
    else res.appendChild(h('span', { className: 'tag open' }, now - Date.parse(r.g.t) > 72 * 36e5 ? 'No result' : 'Pending'));
    if (r.res) { var n = h('span', { className: 'num ' + (u.sign(r.res.u) || 'muted') }, u.fmtU(r.res.u) + 'u'); res.appendChild(n); }
    if (p.rec) res.appendChild(h('span', { className: 'tag top' }, 'Recommended'));
    s.appendChild(res);
    return s;
  }

  function filtered(all) {
    return all.filter(function (r) {
      if (st.view === 'games' ? r.kind !== 'game' : r.kind !== 'prop') return false;
      if (st.rec === 'rec' && !r.p.rec) return false;
      if (st.market !== 'all' && r.key !== st.market) return false;
      return true;
    });
  }

  function render() {
    if (!el || el.hidden) return;
    var u = U();
    if (!u) return;
    seg('nView', 'view', [['games', 'Game picks'], ['props', 'Props']]);
    seg('nRec', 'rec', [['all', 'All leans'], ['rec', 'Recommended']]);
    var mkts = st.view === 'games' ? [['all', 'All'], ['sp', 'Spread'], ['tot', 'Total'], ['ml', 'Moneyline']]
      : [['all', 'All']].concat(Object.keys(MK).map(function (k) { return [k, MK[k]]; }));
    seg('nMarket', 'market', mkts);

    var all = Ledger.nflRows(data.games, data.props, data.results);
    var list = filtered(all);
    var s = Ledger.summarize(list.filter(function (r) { return !r.void; }));
    document.getElementById('nRecd').textContent = s.graded ? s.w + '–' + s.l + (s.p ? '–' + s.p : '') : '–';
    document.getElementById('nRecD').textContent = s.open ? s.open + ' pending' : (s.graded ? 'all graded' : ' ');
    var un = document.getElementById('nUnits'); un.textContent = s.graded ? u.fmtU(s.units) : '–'; un.className = 'v ' + u.sign(s.units);
    var ro = document.getElementById('nRoi'); ro.textContent = s.roi == null ? '–' : (s.roi > 0 ? '+' : '') + (s.roi * 100).toFixed(1) + '%';
    ro.className = 'v ' + u.sign(s.roi || 0);
    document.getElementById('nRoiD').textContent = s.graded ? s.graded + ' graded picks' : ' ';
    document.getElementById('nHit').textContent = u.pct(s.hit);
    document.getElementById('nHitD').textContent = s.exp == null ? ' ' : 'model expected ' + u.pct(s.exp);

    // Breakdown
    var base = list.filter(function (r) { return !r.void; });
    var groups = [['All', base]];
    if (st.view === 'games') {
      ['sp', 'tot', 'ml'].forEach(function (k) { groups.push([GK[k], base.filter(function (r) { return r.key === k; })]); });
      groups.push(['Priced by Betalytics', base.filter(function (r) { return r.p.priced; })]);
    } else {
      [[0, .02, 'Edge under 2 pts'], [.02, .05, 'Edge 2–5 pts'], [.05, .10, 'Edge 5–10 pts'], [.10, 2, 'Edge 10+ pts']].forEach(function (b) {
        groups.push([b[2], base.filter(function (r) { var e = edgeOf(r); return e >= b[0] && e < b[1]; })]);
      });
      if (st.market === 'all') Object.keys(MK).forEach(function (k) { groups.push([MK[k], base.filter(function (r) { return r.key === k; })]); });
    }
    if (st.rec !== 'rec') groups.push(['Recommended', base.filter(function (r) { return r.p.rec; })]);
    document.getElementById('nBreakTitle').textContent = st.view === 'games' ? 'By market' : 'By edge and prop type';
    var tb = document.getElementById('nBreak'); tb.innerHTML = '';
    groups.forEach(function (g) {
      if (!g[1].length && g[0] !== 'All') return;
      var x = Ledger.summarize(g[1]), tr = h('tr');
      [g[0], String(x.n), x.graded ? x.w + '–' + x.l + (x.p ? '–' + x.p : '') : '–', u.pct(x.hit), u.pct(x.exp),
       x.graded ? u.fmtU(x.units) : '–', x.roi == null ? '–' : (x.roi * 100).toFixed(1) + '%'].forEach(function (c, i) {
        var td = h('td', null, c); if ((i === 5 || i === 6) && x.graded) td.className = u.sign(x.units); tr.appendChild(td);
      });
      var sg = u.signal(x), td = h('td'); td.appendChild(h('span', { className: 'sig ' + sg[1] }, sg[0])); tr.appendChild(td);
      tb.appendChild(tr);
    });

    // Recommendations from realized results (ignores the Picks/Market filters, uses the Show switch)
    var pool = all.filter(function (r) { return st.view === 'games' ? r.kind === 'game' : r.kind === 'prop'; });
    var rec = Ledger.recommend(pool,
      function (r) { return r.kind === 'game' ? [r.key] : [r.key + '|' + r.p.side, r.key]; },
      function (r) { return r.kind === 'game' ? r.key !== 'ml' : r.key !== 'player_anytime_td'; },
      function (r) { return r.kind === 'game' ? r.key === 'ml' : r.key === 'player_anytime_td'; });
    LedgerRecs.render(document.getElementById('nRecs'), rec, {
      bet: function (it) {
        var r = it.r, p = r.p;
        if (it.action === 'follow') return pickText(r);
        if (r.kind === 'prop') return p.n + ' ' + (p.side === 'over' ? 'under ' : 'over ') + p.line + ' ' + (MK[p.mk] || p.mk).toLowerCase() + ' (check price)';
        if (r.key === 'sp') return (p.side === 'home' ? r.g.a : r.g.h) + ' ' + U().fmtLine(-p.line) + ' (about −110)';
        return (p.side === 'over' ? 'Under ' : 'Over ') + p.line + ' (about −110)';
      },
      meta: function (it) {
        var r = it.r, d = new Date(r.g.t);
        var game = r.kind === 'prop' ? r.id.split('_').slice(2).join(' @ ') : r.g.a + ' @ ' + r.g.h;
        return game + ' · ' + d.toLocaleDateString(undefined, { weekday: 'short' }) + ' ' +
          d.toLocaleTimeString(undefined, { hour: 'numeric', minute: '2-digit' }) + (it.action === 'fade' ? ' · Betalytics has ' + pickText(r) : '');
      },
      groupName: function (k) {
        var parts = k.split('|');
        var base = GK[parts[0]] || MK[parts[0]] || parts[0];
        return parts.length > 1 ? base + ' ' + parts[1] + 's' : 'All ' + base.toLowerCase() + (GK[parts[0]] ? 's' : '');
      },
      order: function (keys) { return keys.sort(function (a, b) { return a.localeCompare(b); }); }
    });

    // Upcoming leans
    var now = Date.now();
    var up = list.filter(function (r) { return !r.res && !r.void && Date.parse(r.g.t) > now; })
      .sort(function (a, b) { return (b.p.rec - a.p.rec) || (edgeOf(b) - edgeOf(a)); });
    document.getElementById('nLede').textContent = up.length
      ? 'Upcoming ' + (st.view === 'games' ? 'game picks' : 'props') + ', recommended first, then the biggest edge over the market.'
      : 'No upcoming ' + (st.view === 'games' ? 'game picks' : 'props') + ' stored. Upload a capture from the NFL games or props page.';
    var ub = document.getElementById('nUp'); ub.innerHTML = '';
    up.slice(0, st.shownUp).forEach(function (r) { ub.appendChild(slip(r)); });
    if (up.length > st.shownUp) {
      var m = h('button', { type: 'button', className: 'more', id: 'nMoreUp' }, 'Show all ' + up.length);
      m.onclick = function () { st.shownUp = up.length; render(); }; ub.appendChild(m);
    }
    // Results
    var done = list.filter(function (r) { return r.res || r.void; });
    var dbx = document.getElementById('nDone'); dbx.innerHTML = '';
    if (!done.length) dbx.appendChild(h('p', { className: 'muted', style: 'margin:0' }, 'Results appear the day after games, once nflverse publishes scores and player stats.'));
    done.slice(0, st.shownDone).forEach(function (r) { dbx.appendChild(slip(r)); });
    if (done.length > st.shownDone) {
      var m2 = h('button', { type: 'button', className: 'more', id: 'nMoreDone' }, 'Show 50 more of ' + (done.length - st.shownDone));
      m2.onclick = function () { st.shownDone += 50; render(); }; dbx.appendChild(m2);
    }
    // Backtest
    var latest = null;
    Object.keys(data.games).sort().forEach(function (wk) { Object.values(data.games[wk]).forEach(function (g) { if (g.bt && (!latest || g.at > latest.at)) latest = g; }); });
    var bt = document.getElementById('nBt');
    if (latest && latest.bt) {
      var b = latest.bt, parts = [];
      if (b.sp) parts.push('Spread picks: ' + u.pct(b.sp.win) + ' over ' + b.sp.n + ' games');
      if (b.tot) parts.push('Totals (' + (b.tot.bucket || 'all') + '): ' + u.pct(b.tot.win) + ' over ' + b.tot.n);
      if (b.ml) parts.push('Moneyline log loss ' + b.ml.ll.toFixed(3) + ' vs market ' + b.ml.mll.toFixed(3) + ' (lower is better)');
      bt.textContent = parts.join(' · ') + '. Betalytics publishes these for model ' + latest.ver +
        '. Break-even at −110 is 52.4%. Your tracked results above are the independent check.';
    } else bt.textContent = 'Shown after your first NFL upload.';
  }

  function watch(name, fn) {
    db.collection(name).onSnapshot(function (snap) {
      var o = {};
      snap.docs.forEach(function (d) { var b = d.data(); if (b) fn(o, d.id, b); });
      data[name.replace('nfl', '')] = o;
      render();
    }, function () {});
  }

  window.NflTab = {
    start: function (database) {
      db = database;
      watch('nflgames', function (o, id, b) { if (b.games) o[id] = b.games; });
      watch('nflprops', function (o, id, b) { if (b.props) o[id] = b.props; });
      watch('nflresults', function (o, id, b) { o[id] = b; });
    },
    render: function () { if (!el) layout(); render(); },
    ingest: async function (cap) {
      var m = Ledger.mergeNfl(data, cap);
      var weeks = Object.keys(m.games), gids = Object.keys(m.props);
      for (var i = 0; i < weeks.length; i++) await db.doc('nflgames/' + weeks[i]).set({ week: weeks[i], games: m.games[weeks[i]] });
      for (var j = 0; j < gids.length; j++) await db.doc('nflprops/' + gids[j]).set({ game: gids[j], props: m.props[gids[j]] });
      var c = m.counts;
      if (!c.games && !c.props) return 'NFL: nothing new.';
      return 'NFL: saved ' + c.games + ' game' + (c.games === 1 ? '' : 's') + ' and ' + c.props + ' prop' + (c.props === 1 ? '' : 's') +
        (c.skipped ? ' (' + c.skipped + ' props had no line yet)' : '') + '.';
    }
  };
  layout();
})();
