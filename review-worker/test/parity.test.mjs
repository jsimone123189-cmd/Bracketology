// The JS engine (Worker and page) must give exactly the Python engine's results, and the season config must match Python's.
import { test } from "node:test";
import assert from "node:assert/strict";
import path from "node:path";
import { applyEdits, slotsOf, undoneSet } from "../src/engine.js";
import { SEASONS } from "../src/config.js";
import { python, realReview, rng, REPO } from "./helpers.mjs";

const rv = realReview();
const REASONS = ["injury_or_availability", "recent_form", "committee_precedent", "metric_disagreement", "head_to_head", "schedule_quality", "conference_tournament", "bracketing_rule", "other"];

function randomCase(r, n) {
  const field = rv.model_order, outside = rv.rest_order, all = [...field, ...outside], pick = (a) => a[Math.floor(r() * a.length)];
  const edits = [];
  for (let i = 0; i < n; i++) {
    const op = pick(["move", "move", "move", "swap", "add", "remove", "undo", "move"]), id = `e${i}`;
    const e = { id, at: `2027-03-${String(1 + Math.floor(r() * 14)).padStart(2, "0")}T1${Math.floor(r() * 10)}:00:00Z`, op, reason_code: pick(REASONS), confidence: pick([1, 2, 3, 2]) };
    if (e.reason_code === "other" && r() < 0.7) e.explanation = "because";
    if (r() < 0.04) delete e.reason_code;                      // invalid entries too
    if (op === "move") { e.team = pick(r() < 0.9 ? field : all); e.to_line = r() < 0.95 ? 1 + Math.floor(r() * 16) : 17; }
    if (op === "swap") { e.team = pick(field); e.with = pick(r() < 0.9 ? field : outside); }
    if (op === "add") { e.team = pick(r() < 0.85 ? outside : field); if (r() < 0.4) e.remove = pick(field); if (r() < 0.3) e.to_line = 1 + Math.floor(r() * 17); }
    if (op === "remove") { e.team = pick(field); if (r() < 0.4) e.add = pick(outside); }
    if (op === "undo") { if (!edits.length) continue; const t = pick(edits); if (r() < 0.5) e.undo_of = t.id; else e.id = t.id; }
    edits.push(e);
  }
  return { order: field, rest: outside, info: rv.all_info, edits, season: 2027 };
}

test("JS engine matches Python on 400 random edit sequences over the real 2027 field", { skip: !rv && "no local 2027 review" }, () => {
  const r = rng(20270314), cases = Array.from({ length: 400 }, (_, i) => randomCase(r, 1 + (i % 12)));
  const py = JSON.parse(python(path.join(REPO, "review-worker/test/py_engine.py"), cases));
  const slots = slotsOf(SEASONS[2027].lines);
  let applied = 0, rejected = 0;
  cases.forEach((c, i) => {
    const js = applyEdits(c.order, c.rest, c.edits, slots, c.info, SEASONS[2027].selection_sunday), p = py.results[i];
    assert.deepEqual(js.order, p.order, `order differs in case ${i}`);
    assert.deepEqual(js.applied, p.applied, `records differ in case ${i}`);
    assert.equal(js.notes.length, p.notes.length, `notes differ in case ${i}: ${js.notes} | ${p.notes}`);
    applied += js.applied.length; rejected += js.notes.length;
    assert.equal(js.order.length, 76);
  });
  assert.ok(applied > 500 && rejected > 50, `coverage: ${applied} applied, ${rejected} rejected`);
});

test("season config matches Python (cutoff, 76-team lines, Selection Sunday, final deadline 5:45 p.m. EDT)", () => {
  const { config } = JSON.parse(python(path.join(REPO, "review-worker/test/py_engine.py"), []));
  const s = SEASONS[2027];
  assert.equal(s.research_cutoff, config.research_cutoff);
  assert.equal(s.research_cutoff, "2027-03-14T16:00:00Z");
  assert.deepEqual(s.lines, config.lines);
  assert.equal(s.lines.reduce((a, b) => a + b, 0), 76);
  assert.equal(s.selection_sunday, config.selection_sunday);
  assert.equal(s.final_deadline, config.final_deadline); assert.equal(s.final_deadline, "2027-03-14T21:45:00Z");
});

test("replaying a long log in chunks gives exactly the one-pass result (CPU fallback)", { skip: !rv && "no local 2027 review" }, () => {
  const r = rng(7), slots = slotsOf(SEASONS[2027].lines), ss = SEASONS[2027].selection_sunday;
  for (let c = 0; c < 150; c++) {
    const k = randomCase(r, 5 + (c % 40)), whole = applyEdits(k.order, k.rest, k.edits, slots, k.info, ss), size = 1 + (c % 7), U = undoneSet(k.edits);
    let st = { order: k.order, rest: k.rest, applied: [], notes: [] };
    for (let i = 0; i < k.edits.length; i += size) {
      const x = applyEdits(st.order, st.rest, k.edits.slice(i, i + size), slots, k.info, ss, U);
      st = { order: x.order, rest: x.rest, applied: st.applied.concat(x.applied), notes: st.notes.concat(x.notes) };
    }
    assert.deepEqual(st.order, whole.order); assert.deepEqual(st.applied, whole.applied); assert.deepEqual(st.notes, whole.notes);
  }
});
