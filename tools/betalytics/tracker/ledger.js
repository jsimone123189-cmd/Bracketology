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
      if (b && Array.isArray(b.results) && /\/games\/slate/.test(it.url || '')) out.push(b.results);
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

  /** Every pick as a flat row: {date, id, key, p, g, res|null}. */
  function rows(slates, scores) {
    var out = [];
    Object.keys(slates).forEach(function (date) {
      var games = slates[date] || {};
      var sc = scores[date] || {};
      Object.keys(games).forEach(function (id) {
        var g = games[id];
        Object.keys(g.picks || {}).forEach(function (key) {
          out.push({ date: date, id: id, key: key, p: g.picks[key], g: g,
                     res: gradePick(key, g.picks[key], sc[id]) });
        });
      });
    });
    out.sort(function (x, y) { return Date.parse(y.g.t) - Date.parse(x.g.t) || (x.id < y.id ? -1 : 1); });
    return out;
  }

  function summarize(list) {
    var s = { n: list.length, w: 0, l: 0, p: 0, open: 0, units: 0, expSum: 0, expN: 0, nullVar: 0 };
    list.forEach(function (r) {
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
    return s;
  }

  var api = { findSlates: findSlates, compactGame: compactGame, merge: merge, profit: profit,
              gradePick: gradePick, rows: rows, summarize: summarize };
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
  else root.Ledger = api;
})(typeof window !== 'undefined' ? window : this);
