// Edit engine: a line-for-line port of review.apply_edits / check_edit (Python is the reference; test/parity.test.mjs checks
// both give identical results). Used by the Worker (B3, freezes, published lines) and by the page (live preview).
// The bracket is an ordered list and lines come from the season's slot sizes, so line sizes can't break.

export const REASONS = {
  injury_or_availability: "Injury or availability", recent_form: "Recent form", committee_precedent: "Committee precedent",
  metric_disagreement: "Metrics disagree", head_to_head: "Head-to-head", schedule_quality: "Schedule quality",
  conference_tournament: "Conference tournament", bracketing_rule: "Bracketing rule", other: "Other (explain)",
};
export const OPS = ["move", "swap", "add", "remove", "undo"];

export const slotsOf = (lines) => lines.flatMap((n, i) => Array(n).fill(i + 1));
export const linesOf = (order, slots) => Object.fromEntries(order.map((k, i) => [k, slots[i]]));

function lineSpan(slots, line) {
  const a = slots.indexOf(line);
  if (a < 0) throw new Error(`line ${line} doesn't exist`);
  return [a, slots.lastIndexOf(line)];
}

export function when(s) {
  if (typeof s !== "string" || !/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})$/.test(s)) return null;
  const t = Date.parse(s);
  return Number.isNaN(t) ? null : t;
}

export function checkEdit(e) {
  const bad = [];
  if (!OPS.includes(e.op)) bad.push(`op must be one of ${[...OPS].sort().join(", ")}`);
  if (e.op !== "undo") {
    if (!(e.reason_code in REASONS)) bad.push("reason_code missing or unknown");
    if (e.reason_code === "other" && !String(e.explanation || "").trim()) bad.push("'other' needs an explanation");
    if (![1, 2, 3].includes(e.confidence)) bad.push("confidence must be 1, 2 or 3");
  }
  if (!e.id || !e.at) bad.push("needs id and at");
  else if (when(e.at) === null) bad.push("at must be an ISO timestamp");
  return bad;
}

export function phase(selectionSunday, at) {
  if (!selectionSunday) return "unknown";
  const ss = Date.parse(selectionSunday + "T00:00:00Z"), d = Date.parse(String(at).slice(0, 10) + "T00:00:00Z");
  return d >= ss - 7 * 86400000 ? "championship_week" : "pre_championship_week";
}

// order: field keys in model order (best first). rest: outside keys, best candidate first. info: key -> {team, champ, projected_auto, rank_score, p_in}.
export const undoneSet = (edits) => new Set(edits.filter((e) => e.op === "undo").map((e) => e.undo_of || e.id));   // undo_of: the id retracted (older files reuse the id)

// Pass `undone` (from the WHOLE edit list) to replay a long log in chunks: applyEdits(state.order, state.rest, edits.slice(i, j), ..., undone)
// continues exactly where the previous chunk stopped, so the result equals one pass over everything.
export function applyEdits(order0, rest0, edits, slots, info, selectionSunday, undone = undoneSet(edits)) {
  let order = [...order0], rest = [...rest0];
  const notes = [], out = [];
  const auto = (k) => !!(info[k].champ || info[k].projected_auto);
  const insertByScore = (k) => {
    let i = order.findIndex((x) => info[x].rank_score < info[k].rank_score);
    if (i < 0) i = order.length;
    order.splice(i, 0, k);
  };
  const pos = new Map(); order.forEach((t, i) => pos.set(t, i));     // each team's index in `order`, kept up to date after every applied edit
  const phaseCache = new Map();
  const phaseOf = (at) => { const d = String(at).slice(0, 10); if (!phaseCache.has(d)) phaseCache.set(d, phase(selectionSunday, d)); return phaseCache.get(d); };
  for (const e of edits) {
    if (e.op === "undo" || undone.has(e.id)) continue;
    const bad = checkEdit(e);
    if (bad.length) { notes.push(`Edit ${e.id} skipped: ${bad.join("; ")}`); continue; }
    const op = e.op, k = e.team;
    const saved = [order, rest];
    try {
      if (!(k in info)) throw new Error(`unknown team ${k}`);
      if (op === "move") {
        if (!order.includes(k)) throw new Error(`${info[k].team} isn't in the field`);
        const to = parseInt(e.to_line, 10), cur = order.indexOf(k), [a, b] = lineSpan(slots, to);
        if (slots[cur] !== to) { order.splice(cur, 1); order.splice(to < slots[cur] ? a : b, 0, k); }
      } else if (op === "swap") {
        const o = e.with;
        if (!order.includes(k) || !order.includes(o)) throw new Error("both teams must be in the field");
        const i = order.indexOf(k), j = order.indexOf(o); order[i] = o; order[j] = k;
      } else if (op === "add") {
        if (order.includes(k)) throw new Error(`${info[k].team} is already in the field`);
        // Python: next(t for t in reversed(sorted(order, key=p_in, reverse=True)) if not auto(t)) - stable sort, then reversed
        const desc = order.map((t, i) => [t, i]).sort((x, y) => info[y[0]].p_in - info[x[0]].p_in || x[1] - y[1]).map((x) => x[0]);
        const x = e.remove || desc.reverse().find((t) => !auto(t));
        if (!order.includes(x) || auto(x)) throw new Error("the team removed must be an at-large team in the field");
        const a = e.to_line ? lineSpan(slots, parseInt(e.to_line, 10))[0] : null;      // validated before anything changes
        order = order.filter((t) => t !== x); rest = [x, ...rest]; rest = rest.filter((t) => t !== k);
        if (a !== null) order.splice(a, 0, k); else insertByScore(k);
      } else if (op === "remove") {
        if (!order.includes(k) || auto(k)) throw new Error("only at-large teams in the field can be removed");
        const y = e.add || rest.find((t) => !order.includes(t));
        if (y == null || order.includes(y)) throw new Error("no replacement available");
        order = order.filter((t) => t !== k); rest = rest.filter((t) => t !== y); rest = [k, ...rest]; insertByScore(y);
      }
    } catch (err) {
      [order, rest] = saved; notes.push(`Edit ${e.id} not applied: ${err.message}`); continue;
    }
    // Teams whose line changed: each team's slot now vs before (pos still holds the positions before this edit).
    const changed = [];
    for (let i = 0; i < order.length; i++) { const t = order[i], b = pos.get(t); if (b === undefined || slots[b] !== slots[i]) changed.push(t); }
    let goneKey = null;                                                             // add/remove: the one team that left the field
    if (op === "add" || op === "remove") for (const t of pos.keys()) if (!order.includes(t)) { goneKey = t; break; }
    if (goneKey !== null) changed.push(goneKey);
    changed.sort();
    const bi = pos.has(k) ? pos.get(k) : -1;
    if (goneKey !== null) pos.delete(goneKey);
    for (let i = 0; i < order.length; i++) pos.set(order[i], i);
    const ai = pos.get(k);
    out.push({ ...e, phase: e.phase || phaseOf(e.at), line_before: bi < 0 ? null : slots[bi], line_after: ai === undefined ? null : slots[ai],
      overall_before: bi < 0 ? null : bi + 1, overall_after: ai === undefined ? null : ai + 1, teams_changed: changed });
  }
  return { order, rest, applied: out, notes };
}
