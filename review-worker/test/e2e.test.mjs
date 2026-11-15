// End-to-end on this machine only: wrangler dev (local D1 copy) + a fake Access issuer on 127.0.0.1.
// Simulates Selection Sunday 2027 with a fake clock (accepted only in this local setup): uploads, edits, undo, both freezes,
// verification, published lines, export verified by the Python code, refusals of every unauthorized request, immutability.
import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { createHash } from "node:crypto";
import { start, sql, FINAL } from "./devserver.mjs";
import { python, realReview, REPO } from "./helpers.mjs";

const RV = realReview();
let S, base;
const hdr = (tok, now, extra = {}) => ({ ...(tok ? { "Cf-Access-Jwt-Assertion": tok } : {}), ...(now ? { "X-Test-Now": now } : {}), ...extra });
const owner = (p, { now, body, headers = {} } = {}) => fetch(base + p, body === undefined ? { headers: hdr(S.ownerToken(), now, headers) } : { method: "POST", headers: hdr(S.ownerToken(), now, { "Content-Type": "application/json", "X-Review": "1", ...headers }), body: JSON.stringify(body) });
const machine = (p, { now, body } = {}) => fetch(base + p, body === undefined ? { headers: hdr(S.machineToken(), now) } : { method: "POST", headers: hdr(S.machineToken(), now, { "Content-Type": "application/json" }), body: JSON.stringify(body) });
const j = async (r) => ({ status: r.status, body: await r.json().catch(() => null) });
let MODEL_FILES = null;

function variant(collected, pending) {
  const rv = structuredClone(RV);
  rv.inputs = { ...rv.inputs, collected_at: collected, conference_games_pending: pending };
  rv.generated_at = collected.replace(/:00Z$/, ":30Z");
  rv.model_files = MODEL_FILES ??= JSON.parse(python("-c", null, ["import json; from bracketology import review; print(json.dumps(review.model_files()))"]));
  rv.edits = []; rv.edit_notes = [];
  return rv;
}

before(async () => { if (!RV) return; S = await start(); base = S.base; });
after(async () => { if (S) await S.stop(); });

const skip = !RV && "no local 2027 review (python -m bracketology.review build 2027)";
const ids = {};
let A, research, finalF;

test("every request without a valid owner identity is refused", { skip }, async () => {
  for (const p of ["/", "/api/state", "/api/export?kind=research", "/nope"]) {
    assert.equal((await fetch(base + p)).status, 403, `no token ${p}`);
    assert.equal((await fetch(base + p, { headers: { "Cf-Access-Jwt-Assertion": "garbage" } })).status, 403);
    assert.equal((await fetch(base + p, { headers: { "Cf-Access-Jwt-Assertion": S.ownerToken("intruder@example.com") } })).status, 403);
  }
  const forged = S.ownerToken().split("."); forged[1] = Buffer.from(JSON.stringify({ aud: ["local-test-aud"], iss: `http://${S.team}`, email: "owner@example.com", exp: 9e9 })).toString("base64url");
  assert.equal((await fetch(base + "/api/state", { headers: { "Cf-Access-Jwt-Assertion": forged.join(".") } })).status, 403, "forged payload");
  assert.equal((await fetch(base + "/api/edits", { method: "POST", headers: { "Content-Type": "application/json", "X-Review": "1" }, body: "{}" })).status, 403);
  // owner token but a cross-site or form-style write
  assert.equal((await owner("/api/edits", { body: {}, headers: { Origin: "https://evil.example" } })).status, 403);
  assert.equal((await fetch(base + "/api/edits", { method: "POST", headers: { "Cf-Access-Jwt-Assertion": S.ownerToken(), "Content-Type": "text/plain", "X-Review": "1" }, body: "{}" })).status, 403);
  assert.equal((await fetch(base + "/api/edits", { method: "POST", headers: { "Cf-Access-Jwt-Assertion": S.ownerToken(), "Content-Type": "application/json" }, body: "{}" })).status, 403);
  // machine token can't reach owner endpoints; owner token can't reach machine endpoints
  assert.equal((await machine("/api/state")).status, 403);
  assert.equal((await machine("/")).status, 403);
  assert.equal((await owner("/api/machine/published")).status, 403);
  assert.equal((await owner("/api/machine/review", { body: {} })).status, 403);
});

test("owner page loads with strict security headers", { skip }, async () => {
  const r = await owner("/");
  assert.equal(r.status, 200);
  assert.match(await r.text(), /Bracket Review/);
  assert.match(r.headers.get("content-security-policy"), /frame-ancestors 'none'/);
  assert.equal(r.headers.get("cache-control"), "no-store");
  assert.equal(r.headers.get("x-robots-tag"), "noindex, nofollow");
});

test("machine upload: accepts a public-data review, refuses bad ones", { skip }, async () => {
  A = variant("2027-03-14T14:00:00Z", null);
  let r = await j(await machine("/api/machine/review", { body: A, now: "2027-03-14T14:01:00Z" }));
  assert.equal(r.status, 200, JSON.stringify(r.body)); assert.ok(r.body.stored);
  assert.equal((await machine("/api/machine/review", { body: A, now: "2027-03-14T14:02:00Z" })).status, 409, "duplicate");
  assert.equal((await machine("/api/machine/review", { body: { ...variant("2027-03-14T14:05:00Z", null), edits: [{ id: "x" }] }, now: "2027-03-14T14:06:00Z" })).status, 422, "edits never travel");
  assert.equal((await machine("/api/machine/review", { body: variant("2027-03-14T18:00:00Z", null), now: "2027-03-14T14:06:00Z" })).status, 422, "future data");
  assert.equal((await machine("/api/machine/review", { body: { ...variant("2027-03-14T14:07:00Z", null), lines: [4, 4] }, now: "2027-03-14T14:08:00Z" })).status, 422, "wrong format");
});

test("owner edits: preview doesn't save, save gets a server timestamp, invalid edits refused, undo is a new entry", { skip }, async () => {
  const field = A.model_order, outside = A.rest_order.filter((k) => !field.includes(k));
  const t7 = field[25], t1 = field[0], t2 = field[5], bub = outside[0];
  ids.t7 = t7; ids.bub = bub;
  let r = await j(await owner("/api/edits", { now: "2027-03-14T15:00:00Z", body: { op: "move", team: t7, to_line: 2, reason_code: "metric_disagreement", confidence: 2, dry_run: true } }));
  assert.equal(r.status, 200); assert.ok(r.body.preview); assert.ok(r.body.changes.some((c) => c.key === t7 && c.to === 2));
  r = await j(await owner("/api/state", { now: "2027-03-14T15:00:30Z" })); assert.equal(r.body.edits.length, 0, "preview stored nothing");
  r = await j(await owner("/api/edits", { now: "2027-03-14T15:01:00Z", body: { op: "move", team: t7, to_line: 2, reason_code: "metric_disagreement", confidence: 2, client_at: "2020-01-01T00:00:00Z", id: "mine", at: "2020-01-01T00:00:00Z" } }));
  assert.equal(r.status, 200); assert.equal(r.body.edit.at, "2027-03-14T15:01:00Z", "server time, not the client's"); assert.notEqual(r.body.edit.id, "mine");
  ids.move = r.body.edit.id;
  r = await j(await owner("/api/edits", { now: "2027-03-14T15:02:00Z", body: { op: "add", team: bub, reason_code: "committee_precedent", confidence: 1 } }));
  assert.equal(r.status, 200, JSON.stringify(r.body)); ids.add = r.body.edit.id;
  r = await j(await owner("/api/edits", { now: "2027-03-14T15:03:00Z", body: { op: "swap", team: t1, with: t2, reason_code: "head_to_head", confidence: 3 } }));
  assert.equal(r.status, 200); ids.swap = r.body.edit.id;
  for (const bad of [{ op: "move", team: t7, to_line: 17, reason_code: "recent_form", confidence: 2 }, { op: "move", team: t7, to_line: 3, reason_code: "other", confidence: 2 },
    { op: "move", team: t7, to_line: 3, reason_code: "nope", confidence: 2 }, { op: "move", team: t7, to_line: 3, reason_code: "recent_form", confidence: 5 },
    { op: "remove", team: field.find((k) => A.all_info[k].champ || A.all_info[k].projected_auto), reason_code: "recent_form", confidence: 2 }, { op: "drop table", team: t7 }])
    assert.equal((await owner("/api/edits", { now: "2027-03-14T15:04:00Z", body: bad })).status, 422, JSON.stringify(bad));
  r = await j(await owner("/api/edits", { now: "2027-03-14T15:10:00Z", body: { op: "undo", undo_of: ids.swap } })); assert.equal(r.status, 200);
  assert.equal((await owner("/api/edits", { now: "2027-03-14T15:11:00Z", body: { op: "undo", undo_of: "nothing" } })).status, 422);
  r = await j(await owner("/api/edits", { now: "2027-03-14T15:59:59Z", body: { op: "move", team: field[40], to_line: 9, reason_code: "schedule_quality", confidence: 2 } }));
  assert.equal(r.status, 200); ids.late_morning = r.body.edit.id;
  r = await j(await owner("/api/state", { now: "2027-03-14T15:59:59Z" }));
  assert.equal(r.body.edits.length, 5); assert.equal(r.body.b3[t7], 2); assert.ok(bub in r.body.b3); assert.equal(Object.keys(r.body.b3).length, 76);
  assert.deepEqual(r.body.review.brackets.B1_model, A.brackets.B1_model, "B1 untouched by edits");
  assert.deepEqual(r.body.review.brackets.B2_shadow, A.brackets.B2_shadow, "B2 untouched by edits");
  const counts = A.lines.map((_, i) => Object.values(r.body.b3).filter((v) => v === i + 1).length); assert.deepEqual(counts, A.lines, "line sizes kept");
});

test("research snapshot at noon ET: only pre-noon data and edits, immutable, verifiable, idempotent", { skip }, async () => {
  let r = await j(await machine("/api/machine/review", { body: variant("2027-03-14T16:30:00Z", [{ conf: "big-ten" }]), now: "2027-03-14T16:31:00Z" }));
  assert.equal(r.status, 200);
  r = await j(await owner("/api/freeze", { now: "2027-03-14T15:00:00Z", body: { kind: "research" } }));
  assert.equal(r.body.status, "error"); assert.match(r.body.error, /Too early/, "an accidental early tap is refused");
  r = await j(await owner("/api/freeze", { now: "2027-03-14T16:35:00Z", body: { kind: "research" } }));
  assert.equal(r.body.status, "frozen", JSON.stringify(r.body)); assert.equal(r.body.review, "2027-03-14T14:00:00Z");
  research = r.body.sha256;
  r = await j(await owner("/api/freeze", { now: "2027-03-14T16:40:00Z", body: { kind: "research" } }));
  assert.equal(r.body.status, "already_frozen"); assert.equal(r.body.sha256, research);
  r = await j(await owner("/api/verify", { now: "2027-03-14T16:41:00Z", body: { kind: "research" } })); assert.ok(r.body.ok, JSON.stringify(r.body));
  const ex = await owner("/api/export?kind=research"), text = await ex.text(), b = JSON.parse(text);
  assert.equal(createHash("sha256").update(text).digest("hex"), research); assert.equal(ex.headers.get("x-sha256"), research);
  assert.equal(b.kind, "research"); assert.equal(b.cutoff, "2027-03-14T16:00:00Z"); assert.equal(b.inputs.collected_at, "2027-03-14T14:00:00Z");
  assert.deepEqual(b.edit_history.applied.map((e) => e.id).sort(), [ids.move, ids.add, ids.late_morning].sort(), "pre-noon edits, minus the undone swap");
  assert.ok(b.skipped_reviews.some((s) => s.problems.some((p) => p.includes("after the"))), "the 16:30 review was refused");
  const L = (n) => Object.fromEntries(b.brackets[n].map((x) => [x.key, x.line]));
  assert.deepEqual(L("B1_model"), A.brackets.B1_model); assert.deepEqual(L("B2_shadow"), A.brackets.B2_shadow);
  for (const n of ["B1_model", "B2_shadow", "B3_manual"]) assert.equal(b.brackets[n].length, 76);
  // B3 equals what the Python engine gives from the same review and edits
  const py = JSON.parse(python(path.join(REPO, "review-worker/test/py_engine.py"), [{ order: A.model_order, rest: A.rest_order, info: A.all_info, edits: b.edit_history.entries_as_logged, season: 2027 }]));
  const order = py.results[0].order; const slots = A.lines.flatMap((n, i) => Array(n).fill(i + 1));
  assert.deepEqual(L("B3_manual"), Object.fromEntries(order.map((k, i) => [k, slots[i]])));
  // the Python verifier accepts the exported file
  const d = mkdtempSync(path.join(tmpdir(), "jbp-fz-")); writeFileSync(path.join(d, "2027_freeze.json"), text); writeFileSync(path.join(d, "2027_freeze.json.sha256"), research + "\n");
  const v = JSON.parse(python("-c", null, ["import json,sys; from bracketology import review; print(json.dumps(review.verify(2027, sys.argv[1], write_record=False)))", d]));
  assert.ok(v.ok, JSON.stringify(v.problems));
});

test("final snapshot: waits for the last conference final, refuses post-deadline data, then edits close", { skip }, async () => {
  let r = await j(await owner("/api/edits", { now: "2027-03-14T17:00:00Z", body: { op: "move", team: ids.t7, to_line: 3, reason_code: "conference_tournament", confidence: 2 } }));
  assert.equal(r.status, 200); assert.match(r.body.note, /final snapshot/); ids.afternoon = r.body.edit.id;
  assert.equal((await machine("/api/machine/review", { body: variant("2027-03-14T20:40:00Z", [{ conf: "big-ten" }]), now: "2027-03-14T20:40:00Z" })).status, 200);
  r = await j(await owner("/api/freeze", { now: "2027-03-14T20:45:00Z", body: { kind: "final" } }));
  assert.match(r.body.error || "", /Too early/, "Big Ten final still on and the deadline is an hour away");
  for (const [c, p] of [["2027-03-14T21:20:00Z", []], ["2027-03-14T21:50:00Z", []]])
    assert.equal((await machine("/api/machine/review", { body: variant(c, p), now: c })).status, 200);
  r = await j(await owner("/api/freeze", { now: "2027-03-14T21:46:00Z", body: { kind: "final" } }));
  assert.equal(r.body.status, "frozen", JSON.stringify(r.body)); assert.equal(r.body.review, "2027-03-14T21:20:00Z"); assert.equal(r.body.final_results_complete, true);
  finalF = r.body.sha256; assert.notEqual(finalF, research);
  const b = JSON.parse(await (await owner("/api/export?kind=final")).text());
  assert.ok(b.edit_history.applied.some((e) => e.id === ids.afternoon), "afternoon edit counts for the final");
  assert.equal(Object.fromEntries(b.brackets.B3_manual.map((x) => [x.key, x.line]))[ids.t7], 3);
  assert.ok(b.skipped_reviews.some((s) => s.review === "2027-03-14T21:50:00Z"), "post-deadline review refused");
  r = await j(await owner("/api/verify", { now: "2027-03-14T21:47:00Z", body: { kind: "final" } })); assert.ok(r.body.ok, JSON.stringify(r.body));
  assert.equal((await owner("/api/edits", { now: "2027-03-14T21:48:00Z", body: { op: "move", team: ids.t7, to_line: 1, reason_code: "recent_form", confidence: 1 } })).status, 409, "edits closed after the final freeze");
  // research snapshot is untouched by everything after it
  r = await j(await owner("/api/state", { now: "2027-03-14T21:49:00Z" }));
  assert.equal(r.body.freezes.find((f) => f.kind === "research").sha256, research);
});

test("published lines: team and line only, from the final snapshot", { skip }, async () => {
  const r = await j(await machine("/api/machine/published"));
  assert.equal(r.status, 200); assert.equal(r.body.source, "final_freeze"); assert.equal(r.body.sha256, finalF);
  assert.equal(r.body.teams.length, 76);
  for (const t of r.body.teams) assert.deepEqual(Object.keys(t).sort(), ["key", "line", "team"]);
  const s = JSON.stringify(r.body); for (const w of ["reason", "confidence", "explanation", "model_line", "p_in", "B1", "B2"]) assert.ok(!s.includes(w), w);
});

test("edit backup download: owner only, full history", { skip }, async () => {
  const r = await owner("/api/export-edits"); assert.equal(r.status, 200);
  const e = await r.json(); assert.equal(e.length, 6); assert.ok(e.some((x) => x.op === "undo"));
  assert.equal((await fetch(base + "/api/export-edits")).status, 403); assert.equal((await machine("/api/export-edits")).status, 403);
});

test("stored edits and snapshots can't be changed or deleted, even with direct database access", { skip }, async () => {
  for (const c of ["UPDATE freezes SET sha256 = 'x'", "DELETE FROM freezes", "UPDATE edits SET at = '2027-03-14T12:00:00Z'", "DELETE FROM edits",
    "INSERT INTO freezes (season, kind, frozen_at, sha256, body) VALUES (2027, 'research', 'x', 'x', 'x')"]) {
    const r = sql(S.persist, c); assert.equal(r.ok, false, c); }
  const r = sql(S.persist, "SELECT COUNT(*) AS n FROM edits"); assert.ok(r.ok && /"n": 6/.test(r.out), r.out);
});
