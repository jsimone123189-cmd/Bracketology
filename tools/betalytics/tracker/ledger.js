/* Betalytics NCAAB ledger: import Betalytics captures and grade picks.
 * Shared by the tracker page (window.Ledger) and Node (module.exports). */
(function (root) {
  'use strict';
  var MARKETS = { moneyline: 'ml', spread: 'sp', total: 'tot' };
  var PICK_FIELD = { moneyline: 'pick_ml', spread: 'pick_spread', total: 'pick_total' };

  function team(t) {
    t = t || {};
    return { n: t.name || '', s: t.short_name || t.name || '', a: t.abbr || '', k: t.kenpom_name || '' };
  }

  /** The slate game lists inside a capture file (or a raw slate response). */
  function findSlates(capture) {
    var out = [];
    var items = capture && Array.isArray(capture.items) ? capture.items : [];
    items.forEach(function (it) {
      var b = it && it.body;
      // NCAAB only; other sports' slates (e.g. NFL) share the URL shape and must not mix in.
      if (b && Array.isArray(b.results) && /\/ncaab\/games\/slate/.test(it.url || '')) out.push(b.results);
    });
    if (!out.length && capture && Array.isArray(capture.results)) out.push(capture.results);
    return out;
  }

  /** One game reduced to what grading needs; null when the model made no priced pick. */
  function compactGame(g) {
    var m = g && g.model;
    if (!m || m.projection_only || !g.market || !m.two_signal) return null;
    var picks = {};
    Object.keys(MARKETS).forEach(function (mk) {
      var side = m[PICK_FIELD[mk]];
      var sig = side && m.two_signal[mk] && m.two_signal[mk][side];
      if (!sig || sig.best_price == null) return;
      if (mk !== 'moneyline' && sig.line == null) return;
      picks[MARKETS[mk]] = {
        side: side, line: sig.line == null ? null : sig.line, price: sig.best_price,
        hit: sig.hit_chance == null ? null : sig.hit_chance,
        edge: sig.price_edge_pts == null ? null : sig.price_edge_pts,
        grade: sig.price_grade || null, stars: sig.stars == null ? null : sig.stars,
        top: !!sig.top_bet,
      };
    });
    if (!Object.keys(picks).length) return null;
    return { t: g.game_time, h: team(g.home), a: team(g.away), ver: m.version || '',
             at: m.created_at || '', picks: picks };
  }

  /**
   * Merge a capture into stored slates ({date: {gameId: game}}).
   * A game is taken only if the model ran before tip-off, and a newer
   * pre-tip run replaces an older one, so each pick is the last one
   * Betalytics showed before the game started.
   * Returns {slates: {date: games} for changed dates only, counts}.
   */
  function merge(stored, capture) {
    var changed = {};
    var counts = { added: 0, updated: 0, unchanged: 0, started: 0, noPick: 0 };
    findSlates(capture).forEach(function (results) {
      results.forEach(function (g) {
        if (!g || !g.game_id || !g.game_date || !g.game_time) return;
        var c = compactGame(g);
        if (!c) { counts.noPick++; return; }
        if (!c.at || Date.parse(c.at) >= Date.parse(c.t)) { counts.started++; return; }
        var day = changed[g.game_date] || stored[g.game_date] || {};
        var old = day[g.game_id];
        if (old && Date.parse(old.at) >= Date.parse(c.at)) { counts.unchanged++; return; }
        if (!changed[g.game_date]) changed[g.game_date] = Object.assign({}, stored[g.game_date] || {});
        changed[g.game_date][g.game_id] = c;
        counts[old ? 'updated' : 'added']++;
      });
    });
    return { slates: changed, counts: counts };
  }

  /** Profit on a 1-unit stake at American odds. */
  function profit(price) { return price > 0 ? price / 100 : 100 / -price; }

  function gradePick(key, p, score) {
    if (!score || score.hs == null || score.as == null) return null;
    var margin = p.side === 'home' ? score.hs - score.as : score.as - score.hs;
    var diff;
    if (key === 'ml') diff = margin;
    else if (key === 'sp') diff = margin + p.line;
    else diff = p.side === 'over' ? score.hs + score.as - p.line : p.line - (score.hs + score.as);
    var r = diff > 0 ? 'W' : diff < 0 ? 'L' : 'P';
    return { r: r, u: r === 'W' ? profit(p.price) : r === 'L' ? -1 : 0 };
  }

  /**
   * Closing line value of a pick against the consensus closing line (oriented to Betalytics' home/away).
   * Spreads and totals: points better than the close (positive = Betalytics got the better number).
   * Moneylines: closing no-vig win chance minus the break-even of the pick's price.
   */
  function clv(key, p, c) {
    if (!c) return null;
    if (key === 'sp' && c.sp && c.sp.home != null && p.line != null) {
      var close = p.side === 'home' ? c.sp.home : -c.sp.home;
      return { pts: p.line - close, close: close };
    }
    if (key === 'tot' && c.tot && c.tot.line != null && p.line != null) {
      return { pts: p.side === 'over' ? c.tot.line - p.line : p.line - c.tot.line, close: c.tot.line };
    }
    if (key === 'ml' && c.ml && c.ml.home_p != null) {
      var fair = p.side === 'home' ? c.ml.home_p : 1 - c.ml.home_p;
      return { prob: fair - 1 / (1 + profit(p.price)), close: p.side === 'home' ? c.ml.home : c.ml.away };
    }
    return null;
  }

  /** Every pick as a flat row: {date, id, key, p, g, res|null, clv|null}. */
  function rows(slates, scores, closing) {
    var out = [];
    closing = closing || {};
    Object.keys(slates).forEach(function (date) {
      var games = slates[date] || {};
      var sc = scores[date] || {};
      var cl = closing[date] || {};
      Object.keys(games).forEach(function (id) {
        var g = games[id];
        Object.keys(g.picks || {}).forEach(function (key) {
          out.push({ date: date, id: id, key: key, p: g.picks[key], g: g,
                     res: gradePick(key, g.picks[key], sc[id]), clv: clv(key, g.picks[key], cl[id]) });
        });
      });
    });
    out.sort(function (x, y) { return Date.parse(y.g.t) - Date.parse(x.g.t) || (x.id < y.id ? -1 : 1); });
    return out;
  }

  function summarize(list) {
    var s = { n: list.length, w: 0, l: 0, p: 0, open: 0, units: 0, expSum: 0, expN: 0, nullVar: 0,
              clvN: 0, clvBeat: 0, clvSame: 0, clvPts: 0, clvPtsN: 0 };
    list.forEach(function (r) {
      if (r.clv) {
        var v = r.clv.pts != null ? r.clv.pts : r.clv.prob;
        s.clvN++;
        if (Math.abs(v) < 1e-9) s.clvSame++; else if (v > 0) s.clvBeat++;
        if (r.clv.pts != null) { s.clvPts += r.clv.pts; s.clvPtsN++; }
      }
      if (!r.res) { s.open++; return; }
      s[r.res.r.toLowerCase()]++;
      s.units += r.res.u;
      if (r.res.r !== 'P') {
        if (r.p.hit != null) { s.expSum += r.p.hit; s.expN++; }
        // Variance of a 1-unit bet's profit if it only won at its break-even rate (no edge).
        var b = profit(r.p.price), be = 1 / (1 + b);
        s.nullVar += be * (1 - be) * (1 + b) * (1 + b);
      }
    });
    var decided = s.w + s.l;
    s.decided = decided;
    // Standard deviations the units sit above (or below) pure luck at these prices.
    s.z = s.nullVar ? s.units / Math.sqrt(s.nullVar) : null;
    s.graded = decided + s.p;
    s.hit = decided ? s.w / decided : null;
    s.exp = s.expN ? s.expSum / s.expN : null;
    s.roi = s.graded ? s.units / s.graded : null;
    var moved = s.clvN - s.clvSame;      // picks where the line moved at all
    s.beatRate = moved ? s.clvBeat / moved : null;
    s.beatZ = moved ? (s.clvBeat - moved / 2) / Math.sqrt(moved / 4) : null;
    s.avgClvPts = s.clvPtsN ? s.clvPts / s.clvPtsN : null;
    return s;
  }

  /* ---------------- NFL ---------------- */

  /** NFL game and player-prop predictions inside a capture. */
  function findNfl(capture) {
    var out = { games: [], props: [] };
    var items = capture && Array.isArray(capture.items) ? capture.items : [];
    items.forEach(function (it) {
      var b = it && it.body, u = it && it.url || '';
      if (!b || !Array.isArray(b.results)) return;
      if (/\/nfl\/games\/model-predictions/.test(u)) out.games = out.games.concat(b.results);
      if (/\/nfl\/players\/model-predictions/.test(u)) out.props = out.props.concat(b.results);
    });
    return out;
  }

  /** The model's side in one two-way market: the side with the higher hit chance. */
  function nflSide(sig, a, b) {
    if (!sig || !sig[a] || !sig[b] || sig[a].hit_chance == null || sig[b].hit_chance == null) return null;
    return sig[a].hit_chance >= sig[b].hit_chance ? a : b;
  }

  function compactNflGame(g) {
    var ts = g.two_signal || {}, picks = {};
    [['sp', 'spread', 'home', 'away'], ['tot', 'total', 'over', 'under'], ['ml', 'moneyline', 'home', 'away']].forEach(function (m) {
      var side = nflSide(ts[m[1]], m[2], m[3]);
      if (!side) return;
      var s = ts[m[1]][side];
      var price = s.best_price;
      if (price == null && m[0] === 'ml') return;          // a moneyline cannot be graded without a price
      if (m[0] !== 'ml' && s.line == null) return;
      picks[m[0]] = { side: side, line: s.line == null ? null : s.line, price: price == null ? -110 : price,
                      priced: price != null, hit: s.hit_chance, grade: s.price_grade || null,
                      stars: s.stars == null ? null : s.stars, top: !!s.top_bet,
                      rec: !!((g.edges || {})[m[1]] || s.top_bet), edge: s.price_edge_pts == null ? null : s.price_edge_pts };
    });
    if (!Object.keys(picks).length) return null;
    var bt = g.backtest || {}, b = {};
    if (bt.spread && bt.spread.n) b.sp = { n: bt.spread.n, win: bt.spread.win_rate };
    if (bt.total && bt.total.n) b.tot = { n: bt.total.n, win: bt.total.win_rate, bucket: bt.total.bucket || '' };
    if (bt.moneyline && bt.moneyline.n) b.ml = { n: bt.moneyline.n, ll: bt.moneyline.log_loss, mll: bt.moneyline.market_log_loss };
    return { t: g.kickoff_utc, wk: g.season + '-' + String(g.week).padStart(2, '0'), h: g.home_team, a: g.away_team,
             ver: g.version || '', vin: g.vintage || '', at: g.created_at || '', picks: picks, bt: b };
  }

  /** A prop reduced to grading needs. Side = where the model's chance beats the market's. */
  function compactProp(p) {
    var ln = p.line || {};
    if (ln.value == null || p.over_chance == null || p.market_over_chance == null) return null;
    var side = p.over_chance >= p.market_over_chance ? 'over' : 'under';
    var price = side === 'over' ? ln.over_price : ln.under_price;
    if (price == null) return null;
    var hit = side === 'over' ? p.over_chance : p.under_chance;
    var mkt = side === 'over' ? p.market_over_chance : 1 - p.market_over_chance;
    var sig = (p.two_signal || {})[side] || {};
    return { pid: p.player_id, n: p.player_name, tm: p.team, pos: p.position, mk: p.market, line: ln.value,
             side: side, price: sig.best_price != null ? sig.best_price : price, book: ln.book || '',
             hit: hit, mkt: Math.round(mkt * 10000) / 10000, rec: !!((p.edges || {})[side]),
             grade: sig.price_grade || null, vin: p.vintage || '', at: p.created_at || '' };
  }

  /**
   * Merge NFL predictions into stored docs.
   * stored = {games: {week: {gameId: game}}, props: {gameId: {propKey: prop}}}.
   * Taken only when the model ran before kickoff; a newer pre-kickoff run replaces an older one.
   */
  function mergeNfl(stored, capture) {
    var found = findNfl(capture);
    var games = {}, props = {}, counts = { games: 0, props: 0, started: 0, skipped: 0 };
    var kick = {};
    Object.keys(stored.games || {}).forEach(function (wk) {
      Object.keys(stored.games[wk]).forEach(function (id) { kick[id] = stored.games[wk][id].t; });
    });
    found.games.forEach(function (g) { if (g.game_id && g.kickoff_utc) kick[g.game_id] = g.kickoff_utc; });
    found.games.forEach(function (g) {
      var c = g.game_id && compactNflGame(g);
      if (!c) { counts.skipped++; return; }
      if (!c.at || Date.parse(c.at) >= Date.parse(c.t)) { counts.started++; return; }
      var wk = games[c.wk] || Object.assign({}, (stored.games || {})[c.wk] || {});
      var old = wk[g.game_id];
      if (old && Date.parse(old.at) >= Date.parse(c.at)) return;
      wk[g.game_id] = c; games[c.wk] = wk; counts.games++;
    });
    found.props.forEach(function (p) {
      var c = p.game_id && compactProp(p);
      if (!c) { counts.skipped++; return; }
      var t = kick[p.game_id];
      if (!t || !c.at || Date.parse(c.at) >= Date.parse(t)) { counts.started++; return; }
      var k = c.pid + '|' + c.mk;
      var doc = props[p.game_id] || Object.assign({}, (stored.props || {})[p.game_id] || {});
      var old = doc[k];
      if (old && Date.parse(old.at) >= Date.parse(c.at)) return;
      c.t = t;
      doc[k] = c; props[p.game_id] = doc; counts.props++;
    });
    return { games: games, props: props, counts: counts };
  }

  var PROP_STAT = {
    player_anytime_td: ['rushing_tds', 'receiving_tds', 'special_teams_tds'], player_receptions: ['receptions'],
    player_reception_yds: ['receiving_yards'], player_rush_attempts: ['carries'], player_rush_yds: ['rushing_yards'],
    player_pass_attempts: ['attempts'], player_pass_completions: ['completions'],
    player_pass_interceptions: ['passing_interceptions'], player_pass_tds: ['passing_tds'], player_pass_yds: ['passing_yards']
  };

  /** Grade a prop from the player's game stats ({market: value}); null stats = did not play (no action). */
  function gradeProp(p, stats) {
    if (!stats || stats[p.mk] == null) return null;
    var v = stats[p.mk], diff = p.side === 'over' ? v - p.line : p.line - v;
    var r = diff > 0 ? 'W' : diff < 0 ? 'L' : 'P';
    return { r: r, u: r === 'W' ? profit(p.price) : r === 'L' ? -1 : 0, v: v };
  }

  /** Flat rows for NFL game picks and props. results = {week: {games: {id: {hs, as}}, stats: {gameId: {pid: {...}}}}} */
  function nflRows(games, props, results) {
    var out = [];
    var res = {};
    Object.keys(results || {}).forEach(function (wk) {
      var r = results[wk] || {};
      Object.keys(r.games || {}).forEach(function (id) { res[id] = { score: r.games[id], stats: (r.stats || {})[id] || null }; });
    });
    Object.keys(games || {}).forEach(function (wk) {
      Object.keys(games[wk]).forEach(function (id) {
        var g = games[wk][id];
        Object.keys(g.picks).forEach(function (key) {
          var sc = res[id] && res[id].score;
          out.push({ kind: 'game', wk: wk, id: id, key: key, p: g.picks[key], g: g, res: gradePick(key, g.picks[key], sc) });
        });
      });
    });
    Object.keys(props || {}).forEach(function (gid) {
      var doc = props[gid];
      Object.keys(doc).forEach(function (k) {
        var p = doc[k], r = res[gid], graded = null;
        if (r && r.stats) {                     // the game is final once its stats are stored
          graded = gradeProp(p, r.stats[p.pid] || null);
          if (!graded) graded = { r: 'V', u: 0 };   // did not play: void
        }
        out.push({ kind: 'prop', id: gid, key: p.mk, p: p, g: { t: p.t }, res: graded && graded.r === 'V' ? null : graded,
                   void: !!(graded && graded.r === 'V') });
      });
    });
    out.sort(function (x, y) { return Date.parse(y.g.t) - Date.parse(x.g.t); });
    return out;
  }

  /* ---------------- Real edge: how Betalytics' picks actually hit ---------------- */

  var PRIOR = 100;        // pseudo-picks on each side at 50%: the market is assumed efficient until shown otherwise
  var CONFIDENT = 0.8;    // posterior probability needed to recommend following or fading
  var MIN_N = 100;        // decided picks a group needs before any verdict
  var FADE_BE = 110 / 210; // break-even of the other side, assumed priced at -110

  function phi(x) {       // standard normal CDF (Abramowitz-Stegun erf approximation)
    var t = 1 / (1 + 0.3275911 * Math.abs(x) / Math.SQRT2);
    var y = 1 - (((((1.061405429 * t - 1.453152027) * t) + 1.421413741) * t - 0.284496736) * t + 0.254829592) * t *
      Math.exp(-x * x / 2);
    return x >= 0 ? (1 + y) / 2 : (1 - y) / 2;
  }

  /**
   * Realized performance of a group of graded picks, shrunk toward 50%.
   * est = posterior mean hit rate; edge = est - break-even when following; fadeEdge = (1 - est) - break-even of the other side.
   * pFollow / pFade = probability the group really clears break-even following / fading.
   * Moneylines (prices vary too much for a hit rate) use units instead: est is shrunk ROI.
   */
  function realEdge(list, opts) {
    opts = opts || {};
    var w = 0, l = 0, beSum = 0, units = 0, nullVar = 0;
    list.forEach(function (r) {
      if (!r.res || r.res.r === 'P') return;
      if (r.res.r === 'W') w++; else l++;
      var b = profit(r.p.price), be = 1 / (1 + b);
      beSum += be; units += r.res.u; nullVar += be * (1 - be) * (1 + b) * (1 + b);
    });
    var n = w + l, out = { n: n, w: w, l: l, raw: n ? w / n : null, units: units };
    if (opts.byUnits) {
      var roi = units / (n + PRIOR), sd = Math.sqrt(Math.max(nullVar, 1)) / (n + PRIOR);
      out.est = roi; out.edge = roi; out.pFollow = n ? phi(roi / sd) : 0.5; out.pFade = 0; out.fadeEdge = null;
      return out;
    }
    var a = w + PRIOR, bb = l + PRIOR, mean = a / (a + bb);
    var sdp = Math.sqrt(a * bb / ((a + bb) * (a + bb) * (a + bb + 1)));
    var be = n ? beSum / n : FADE_BE;
    out.est = mean; out.be = be;
    out.edge = mean - be;
    out.fadeEdge = (1 - mean) - FADE_BE;
    out.pFollow = 1 - phi((be - mean) / sdp);
    out.pFade = phi(((1 - FADE_BE) - mean) / sdp);
    return out;
  }

  /** 'follow' | 'fade' | 'none' | 'few' for a group, given whether fading is possible for it. */
  function verdict(e, canFade) {
    if (e.n < MIN_N) return 'few';
    if (e.pFollow >= CONFIDENT && e.edge > 0) return 'follow';
    if (canFade && e.pFade >= CONFIDENT && e.fadeEdge > 0) return 'fade';
    if (!canFade && e.pFollow <= 1 - CONFIDENT && e.edge < 0) return 'avoid';   // clearly losing, other side unpriced
    return 'none';
  }

  /**
   * Recommend upcoming picks from graded history.
   * groupsOf(r) -> list of group keys, most specific first (e.g. ['sp|A', 'sp']); the first group with enough
   * data decides. canFade(r) says whether the other side is a near -110 two-way bet.
   * Returns {groups: {key: realEdge + verdict}, picks: [{r, group, e, action}]} for upcoming picks with an action.
   */
  function recommend(all, groupsOf, canFade, isUnits) {
    var hist = {};
    all.forEach(function (r) {
      if (!r.res) return;
      groupsOf(r).forEach(function (k) { (hist[k] = hist[k] || []).push(r); });
    });
    var groups = {};
    Object.keys(hist).forEach(function (k) {
      var sample = hist[k][0];
      var e = realEdge(hist[k], { byUnits: isUnits(sample) });
      e.verdict = verdict(e, canFade(sample));
      groups[k] = e;
    });
    var now = Date.now(), picks = [];
    all.forEach(function (r) {
      if (r.res || r.void || Date.parse(r.g.t) <= now) return;
      var keys = groupsOf(r), g = null, k = null;
      for (var i = 0; i < keys.length; i++) {
        if (groups[keys[i]] && groups[keys[i]].n >= MIN_N) { g = groups[keys[i]]; k = keys[i]; break; }
      }
      if (!g || (g.verdict !== 'follow' && g.verdict !== 'fade')) return;
      picks.push({ r: r, group: k, e: g, action: g.verdict });
    });
    picks.sort(function (x, y) {
      var ex = x.action === 'fade' ? x.e.fadeEdge : x.e.edge, ey = y.action === 'fade' ? y.e.fadeEdge : y.e.edge;
      return ey - ex || Date.parse(x.r.g.t) - Date.parse(y.r.g.t);
    });
    return { groups: groups, picks: picks };
  }

  var api = { realEdge: realEdge, verdict: verdict, recommend: recommend, MIN_N: MIN_N, PRIOR: PRIOR,
              findSlates: findSlates, compactGame: compactGame, merge: merge, profit: profit,
              gradePick: gradePick, clv: clv, rows: rows, summarize: summarize,
              findNfl: findNfl, compactNflGame: compactNflGame, compactProp: compactProp, mergeNfl: mergeNfl,
              gradeProp: gradeProp, nflRows: nflRows, PROP_STAT: PROP_STAT };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.Ledger = api;
})(typeof window !== 'undefined' ? window : this);
