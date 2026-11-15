// Research and final snapshots, mirroring review.problems / freeze / verify in Python (docs/43).
// Freezes are written once (D1 primary key + no-update/no-delete triggers); the stored body is the exact text that was hashed,
// so an exported freeze verifies with `python -m bracketology.review verify` given a .sha256 sidecar.
import { applyEdits, linesOf, slotsOf, when } from "./engine.js";

export async function sha256hex(text) {
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(d)].map((b) => b.toString(16).padStart(2, "0")).join("");
}
const iso = (ms) => new Date(ms).toISOString().replace(/\.\d{3}Z$/, "Z");

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

// Why a stored review can't be frozen at this cutoff. Empty = freezable. B3 is checked separately (it's computed here, not uploaded).
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

// The parts of a review that freezes, B3 and published lines use. Kept separately at upload so those paths never parse the evidence.
export const CORE_KEYS = ["season", "generated_at", "model_version", "lines", "inputs", "consistency", "shadow", "v2_fingerprint", "model_files", "brackets", "model_order", "rest_order", "all_info", "phase"];
export function coreOf(rv) {
  const c = Object.fromEntries(CORE_KEYS.filter((k) => k in rv).map((k) => [k, rv[k]]));
  c.sources = { ...Object.fromEntries(Object.entries(rv.sources || {}).filter(([k]) => k !== "checks")), checks: (rv.sources || {}).checks || [] };
  return c;
}

export function b3(rv, edits, cfg) {
  return applyEdits(rv.model_order, rv.rest_order, edits, slotsOf(cfg.lines), rv.all_info, cfg.selection_sunday);
}

function fullBracket(L, info) {
  return Object.entries(L).map(([k, v]) => ({ key: k, team: (info[k] || {}).team ?? k, line: v, champ: (info[k] || {}).champ ?? null, projected_auto: (info[k] || {}).projected_auto ?? null }))
    .sort((a, b) => a.line - b.line || ((info[b.key] || {}).rank_score ?? 0) - ((info[a.key] || {}).rank_score ?? 0));
}

// reviews: [{collected_at, core, body_sha256}] newest first. edits: all logged edits, oldest first.
// Scans newest to oldest and stops at the first usable review (research) or the first usable one with every conference final in
// (final, looking at most MAX_SCAN usable reviews), so the work stays small whatever the number of uploads.
const MAX_SCAN = 4;
export async function buildFreeze({ season, kind, cfg, reviews, edits, now }) {
  const cutoff = cutoffOf(cfg, kind);
  if (cutoff === null) throw new Error(`No confirmed ${kind} deadline for ${season}. It's set in config.js once confirmed.`);
  const inTime = edits.filter((e) => when(e.at) !== null && when(e.at) <= cutoff), late = edits.length - inTime.length;
  const skipped = [], valid = [];
  const complete = (rv) => Array.isArray(rv.inputs.conference_games_pending) && rv.inputs.conference_games_pending.length === 0;
  for (const r of reviews) {
    if (when(r.collected_at) > cutoff) { skipped.push({ review: r.collected_at, problems: [`data collected ${r.collected_at} after the ${iso(cutoff)} cutoff`] }); continue; }
    if (valid.length && (kind === "research" || complete(valid[valid.length - 1].rv) || valid.length >= MAX_SCAN)) break;
    let rv; try { rv = JSON.parse(r.core); } catch { skipped.push({ review: r.collected_at, problems: ["unreadable"] }); continue; }
    const bad = problems(rv, cutoff, cfg);
    if (bad.length) skipped.push({ review: r.collected_at, problems: bad }); else valid.push({ r, rv });
  }
  if (!valid.length) throw new Error(`No freezable review for ${season} (${kind}). Skipped: ${JSON.stringify(skipped)}`);
  const pick = kind === "final" ? (valid.find((v) => complete(v.rv)) || valid[0]) : valid[0];
  const { r, rv } = pick, mf = rv.model_files || {}, info = rv.all_info;
  const B = b3(rv, inTime, cfg), e3 = sizesOk(linesOf(B.order, slotsOf(cfg.lines)), cfg.lines);
  if (e3) throw new Error(`B3 has ${e3}`);        // can't happen: edits keep line sizes by construction
  const brackets = { B1_model: fullBracket(rv.brackets.B1_model, info), B2_shadow: fullBracket(rv.brackets.B2_shadow, info), B3_manual: fullBracket(linesOf(B.order, slotsOf(cfg.lines)), info) };
  const body = {
    schema: 2, kind, season, store: "cloudflare-d1", frozen_at: iso(now), cutoff: iso(cutoff), frozen_after_cutoff: now > cutoff,
    final_results_complete: complete(rv), conference_games_pending: rv.inputs.conference_games_pending ?? null,
    review_file: r.collected_at, review_sha256: r.body_sha256, review_generated_at: rv.generated_at,
    inputs: rv.inputs, sources: Object.fromEntries(Object.entries(rv.sources || {}).filter(([k]) => k !== "checks")), data_checks: (rv.sources || {}).checks || [],
    model: { version: rv.model_version, v2_fingerprint_used: rv.v2_fingerprint ?? null, v2_saved_fingerprint: mf.v2_saved_fingerprint ?? null,
      v2_file_sha256: mf.v2_file_sha256 ?? null, v2_expected_file_sha256: mf.v2_expected_file_sha256 ?? null,
      shadow_fingerprint_used: (rv.shadow || {}).fingerprint ?? null, shadow_train_years: (rv.shadow || {}).train_years ?? null, code_commit: mf.code_commit ?? null },
    consistency: { ...rv.consistency, B3_is_B1_plus_logged_edits: true, edits_counted_through: iso(cutoff) },
    brackets,
    edit_history: { entries_as_logged: inTime, logged_after_cutoff_excluded: late, applied: B.applied, not_applied: B.notes },
    skipped_reviews: skipped,
  };
  const text = JSON.stringify(body, null, 1);
  return { text, sha256: await sha256hex(text), body };
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
  res.ok = res.problems.length === 0; res.frozen_after_cutoff = b.frozen_after_cutoff;
  return res;
}
