// Research and final snapshots, mirroring review.problems / freeze / verify in Python (docs/43-45).
// Freezes are written once (D1 primary key + no-update/no-delete triggers); the stored body is the exact text that was hashed,
// so an exported freeze verifies with `python -m bracketology.review verify` given a .sha256 sidecar.
// Work is split into choose -> replay -> write so a long edit log can be replayed in chunks (one chunk per request) if a single
// request would exceed the free plan's 10 ms CPU limit; the result is identical either way (test/chunk.test.mjs).
import { applyEdits, linesOf, slotsOf, undoneSet, when } from "./engine.js";

export async function sha256hex(text) {
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(d)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
export const iso = (ms) => new Date(ms).toISOString().replace(/\.\d{3}Z$/, "Z");

// An incomplete final (a Selection Sunday conference final not yet over) may be frozen only in the last minutes before the
// deadline, so it is never taken while the finals could still finish in time.
export const INCOMPLETE_FINAL_WINDOW_MS = 10 * 60000;
export const EARLIEST_MS = 30 * 60000;

export function cutoffOf(cfg, kind) {
  if (kind === "research") return Date.parse(cfg.research_cutoff);
  if (kind === "final") return cfg.final_deadline ? Date.parse(cfg.final_deadline) : null;
  return null;
}

function sizesOk(L, lines) {
  const size = lines.reduce((a, b) => a + b, 0), vals = Object.values(L);
  const sizes = lines.map((_, i) => vals.filter((v) => v === i + 1).length);
  return vals.length === size && sizes.every((n, i) => n === lines[i]) ? null : `${vals.length} teams / line sizes ${sizes}, expected ${size} / ${lines}`;
}

// The parts of a review that freezes, B3 and published lines use. Kept separately at upload so those paths never parse the evidence.
export const CORE_KEYS = ["season", "generated_at", "model_version", "lines", "inputs", "consistency", "shadow", "v2_fingerprint", "model_files", "brackets", "model_order", "rest_order", "all_info", "phase"];
export function coreOf(rv) {
  const c = Object.fromEntries(CORE_KEYS.filter((k) => k in rv).map((k) => [k, rv[k]]));
  c.sources = { ...Object.fromEntries(Object.entries(rv.sources || {}).filter(([k]) => k !== "checks")), checks: (rv.sources || {}).checks || [] };
  return c;
}
export const complete = (rv) => Array.isArray(rv.inputs.conference_games_pending) && rv.inputs.conference_games_pending.length === 0;

// Why a stored review can't be frozen at this cutoff. Empty = freezable.
export function problems(rv, cutoff, cfg) {
  const bad = [], inp = rv.inputs || {};
  if (!inp.collected_at || when(inp.collected_at) === null) return ["no collection time recorded"];
  if (when(inp.collected_at) > cutoff) bad.push(`data collected ${inp.collected_at} after the ${iso(cutoff)} cutoff`);
  if (when(rv.generated_at) === null || when(rv.generated_at) > cutoff) bad.push(`generated ${rv.generated_at} after the cutoff`);
  if (inp.latest_game_used && inp.latest_game_used > iso(cutoff).slice(0, 10)) bad.push("uses games dated after Selection Sunday");
  if (JSON.stringify(rv.lines) !== JSON.stringify(cfg.lines)) bad.push(`format ${rv.lines} differs from the season's ${cfg.lines}`);
  for (const name of ["B1_model", "B2_shadow"]) {
    const L = (rv.brackets || {})[name];
    if (!L) { bad.push(`${name} missing`); continue; }
    const e = sizesOk(L, cfg.lines); if (e) bad.push(`${name} has ${e}`);
  }
  const B1 = (rv.brackets || {}).B1_model;
  if (B1 && rv.model_order && JSON.stringify(linesOf(rv.model_order, slotsOf(cfg.lines))) !== JSON.stringify(Object.fromEntries(rv.model_order.map((k) => [k, B1[k]]))))
    bad.push("B1 doesn't match the model order");
  if ((rv.consistency || {}).B2_same_field_as_B1 === false) bad.push("B2 field differs from B1");
  const ty = (rv.shadow || {}).train_years || [];
  if (ty.includes(rv.season)) bad.push("shadow was trained on the season being frozen");
  const alerts = ((rv.sources || {}).checks || []).filter((x) => x.level === "alert").map((x) => x.message);
  if (alerts.length) bad.push(`data-check alerts: ${alerts.slice(0, 3)}`);
  return bad;
}

export function b3(rv, edits, cfg) {
  return applyEdits(rv.model_order, rv.rest_order, edits, slotsOf(cfg.lines), rv.all_info, cfg.selection_sunday);
}

// Step 1: which review, and is it allowed now? reviews: [{collected_at, core, body_sha256}] newest first.
// Stops at the first usable review (research) or the first usable one with every conference final in (final, at most 4 looked at).
const MAX_SCAN = 4;
export function choose({ season, kind, cfg, reviews, now }) {
  const cutoff = cutoffOf(cfg, kind);
  if (cutoff === null) return { error: `No confirmed ${kind} deadline for ${season}. It's set in config.js once confirmed.` };
  const skipped = [], valid = [];
  for (const r of reviews) {
    if (when(r.collected_at) > cutoff) { skipped.push({ review: r.collected_at, problems: [`data collected ${r.collected_at} after the ${iso(cutoff)} cutoff`] }); continue; }
    if (valid.length && (kind === "research" || complete(valid[valid.length - 1].rv) || valid.length >= MAX_SCAN)) break;
    let rv; try { rv = JSON.parse(r.core); } catch { skipped.push({ review: r.collected_at, problems: ["unreadable"] }); continue; }
    const bad = problems(rv, cutoff, cfg);
    if (bad.length) skipped.push({ review: r.collected_at, problems: bad }); else valid.push({ r, rv });
  }
  if (!valid.length) return { error: `No freezable review for ${season} (${kind}). Skipped: ${JSON.stringify(skipped)}` };
  const pick = kind === "final" ? (valid.find((v) => complete(v.rv)) || valid[0]) : valid[0];
  const isComplete = complete(pick.rv);
  // Timing rules (also protect against an accidental early tap):
  if (now < cutoff - EARLIEST_MS && !(kind === "final" && isComplete && now > cutoffOf(cfg, "research")))
    return { error: `Too early: the ${kind} snapshot can't be frozen before ${iso(cutoff - EARLIEST_MS)}${kind === "final" ? " unless every conference final is in" : ""}.`, wait: true };
  if (kind === "final" && !isComplete && now < cutoff - INCOMPLETE_FINAL_WINDOW_MS) {
    const p = pick.rv.inputs.conference_games_pending;
    return { error: `Waiting for conference finals (${p == null ? "the scoreboard couldn't be read" : p.map((g) => g.game || g.conf).join(", ")}). An incomplete final is frozen only after ${iso(cutoff - INCOMPLETE_FINAL_WINDOW_MS)}.`, wait: true };
  }
  return { cutoff, pick, skipped, complete: isComplete };
}

// Step 2: replay. Edits counted are those logged at or before the cutoff (server time).
export function editsFor(edits, cutoff) {
  const inTime = edits.filter((e) => when(e.at) !== null && when(e.at) <= cutoff);
  return { inTime, late: edits.length - inTime.length };
}
export function replayStart(rv) { return { order: rv.model_order, rest: rv.rest_order, applied: [], notes: [], i: 0 }; }
export function replayStep(state, rv, inTime, cfg, maxEdits) {
  const chunk = inTime.slice(state.i, state.i + maxEdits);
  const r = applyEdits(state.order, state.rest, chunk, slotsOf(cfg.lines), rv.all_info, cfg.selection_sunday, undoneSet(inTime));
  return { order: r.order, rest: r.rest, applied: state.applied.concat(r.applied), notes: state.notes.concat(r.notes), i: state.i + chunk.length };
}

function fullBracket(L, info) {
  return Object.entries(L).map(([k, v]) => ({ key: k, team: (info[k] || {}).team ?? k, line: v, champ: (info[k] || {}).champ ?? null, projected_auto: (info[k] || {}).projected_auto ?? null }))
    .sort((a, b) => a.line - b.line || ((info[b.key] || {}).rank_score ?? 0) - ((info[a.key] || {}).rank_score ?? 0));
}

// Step 3: the snapshot text and its hash.
export async function writeBody({ season, kind, cfg, chosen, B, inTime, late, now }) {
  const { cutoff, pick, skipped } = chosen, { r, rv } = pick, mf = rv.model_files || {}, info = rv.all_info;
  const e3 = sizesOk(linesOf(B.order, slotsOf(cfg.lines)), cfg.lines);
  if (e3) throw new Error(`B3 has ${e3}`);        // can't happen: edits keep line sizes by construction
  const body = {
    schema: 2, kind, season, store: "cloudflare-d1", frozen_at: iso(now), cutoff: iso(cutoff), frozen_after_cutoff: now > cutoff,
    final_results_complete: complete(rv), conference_games_pending: rv.inputs.conference_games_pending ?? null,
    review_file: r.collected_at, review_sha256: r.body_sha256, review_generated_at: rv.generated_at,
    inputs: rv.inputs, sources: Object.fromEntries(Object.entries(rv.sources || {}).filter(([k]) => k !== "checks")), data_checks: (rv.sources || {}).checks || [],
    model: { version: rv.model_version, v2_fingerprint_used: rv.v2_fingerprint ?? null, v2_saved_fingerprint: mf.v2_saved_fingerprint ?? null,
      v2_file_sha256: mf.v2_file_sha256 ?? null, v2_expected_file_sha256: mf.v2_expected_file_sha256 ?? null,
      shadow_fingerprint_used: (rv.shadow || {}).fingerprint ?? null, shadow_train_years: (rv.shadow || {}).train_years ?? null, code_commit: mf.code_commit ?? null },
    consistency: { ...rv.consistency, B3_is_B1_plus_logged_edits: true, edits_counted_through: iso(cutoff) },
    brackets: { B1_model: fullBracket(rv.brackets.B1_model, info), B2_shadow: fullBracket(rv.brackets.B2_shadow, info), B3_manual: fullBracket(linesOf(B.order, slotsOf(cfg.lines)), info) },
    edit_history: { entries_as_logged: inTime, logged_after_cutoff_excluded: late, applied: B.applied, not_applied: B.notes },
    skipped_reviews: skipped,
  };
  const text = JSON.stringify(body, null, 1);
  return { text, sha256: await sha256hex(text), body };
}

// One-call freeze (small logs) used by tests and the direct path.
export async function buildFreeze({ season, kind, cfg, reviews, edits, now }) {
  const chosen = choose({ season, kind, cfg, reviews, now });
  if (chosen.error) throw new Error(chosen.error);
  const { inTime, late } = editsFor(edits, chosen.cutoff);
  const B = replayStep(replayStart(chosen.pick.rv), chosen.pick.rv, inTime, cfg, inTime.length);
  return writeBody({ season, kind, cfg, chosen, B, inTime, late, now });
}

// Independent check of a stored freeze: hash, cutoff, kind, sizes, edit times, exact v2.0.
export async function verifyFreeze({ row, season, kind, cfg, now }) {
  const res = { season, kind, checked_at: iso(now), problems: [] };
  if (!row) { res.problems.push("no freeze"); res.ok = false; return res; }
  res.sha256 = await sha256hex(row.body);
  if (res.sha256 !== row.sha256) res.problems.push(`hash mismatch: body ${res.sha256} recorded ${row.sha256}`);
  let b; try { b = JSON.parse(row.body); } catch { res.problems.push("unreadable"); res.ok = false; return res; }
  const cutoff = cutoffOf(cfg, kind);
  if (cutoff === null || b.cutoff !== iso(cutoff)) res.problems.push(`recorded cutoff ${b.cutoff} differs from the configured one`);
  if (b.kind !== kind) res.problems.push(`file is a ${b.kind} freeze, expected ${kind}`);
  if (cutoff !== null) {
    if (when(b.inputs.collected_at) > cutoff) res.problems.push("frozen data collected after the cutoff");
    if (when(b.review_generated_at) > cutoff) res.problems.push("frozen review generated after the cutoff");
    const lateE = (b.edit_history.applied || []).filter((e) => !(when(e.at) <= cutoff)).map((e) => e.id);
    if (lateE.length) res.problems.push(`edits after the cutoff: ${lateE}`);
  }
  for (const [n, rows] of Object.entries(b.brackets)) {
    const e = sizesOk(Object.fromEntries(rows.map((x) => [x.key, x.line])), cfg.lines); if (e) res.problems.push(`${n} incomplete`);
  }
  const m = b.model || {};
  if (!m.v2_file_sha256 || m.v2_file_sha256 !== m.v2_expected_file_sha256) res.problems.push("models/v2.joblib differs from the frozen baseline");
  if (!m.v2_fingerprint_used || m.v2_fingerprint_used !== m.v2_saved_fingerprint) res.problems.push("the model used is not the saved v2.0");
  res.ok = res.problems.length === 0; res.frozen_after_cutoff = b.frozen_after_cutoff; res.final_results_complete = b.final_results_complete;
  return res;
}
