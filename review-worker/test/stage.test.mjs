// Pre-deployment checks (docs/45), all on this machine:
//  - every route x every identity (none, garbage, intruder, service token, owner)
//  - publish: drafts never reach the published lines
//  - incomplete final: waits, then freezes only in the last 10 minutes, flagged, warned, labelled
//  - chunked freeze (forced small chunks) gives the same B3 as the Python engine
//  - automatic backup (button and cron), append-only backup database
//  - restore into fresh databases from (a) the backup database and (b) the downloaded bundle: same edits, timestamps,
//    undo history, B3, publications and snapshot hashes; snapshots still verify; protections still on
import { test, before, after } from "node:test";
import assert from "node:assert/strict";
import { readFileSync, mkdtempSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { start, sql, wr, FINAL } from "./devserver.mjs";
import { python, realReview, REPO } from "./helpers.mjs";

const RV = realReview(), skip = !RV && "no local 2027 review";
let S, base, MF, orig = {};
const H = (tok, now, x = {}) => ({ ...(tok ? { "Cf-Access-Jwt-Assertion": tok } : {}), ...(now ? { "X-Test-Now": now } : {}), ...x });
const ownerReq = (p, { now, body } = {}) => fetch(base + p, body === undefined ? { headers: H(S.ownerToken(), now) } : { method: "POST", headers: H(S.ownerToken(), now, { "Content-Type": "application/json", "X-Review": "1" }), body: JSON.stringify(body) });
const machineReq = (p, { now, body } = {}) => fetch(base + p, body === undefined ? { headers: H(S.machineToken(), now) } : { method: "POST", headers: H(S.machineToken(), now, { "Content-Type": "application/json" }), body: JSON.stringify(body) });
const J = async (r) => ({ status: r.status, body: await r.json().catch(() => null) });
function variant(collected, pending) {
  const rv = structuredClone(RV); MF ??= JSON.parse(python("-c", null, ["import json; from bracketology import review; print(json.dumps(review.model_files()))"]));
  rv.inputs = { ...rv.inputs, collected_at: collected, conference_games_pending: pending }; rv.generated_at = collected.replace(/:00Z$/, ":30Z");
  rv.model_files = MF; rv.edits = []; rv.edit_notes = []; return rv;
}
async function freezeLoop(kind, now) {
  const seen = []; let r;
  for (let i = 0; i < 50; i++) { r = (await J(await ownerReq("/api/freeze", { now, body: { kind } }))).body; seen.push(r.status); if (r.status !== "in_progress") break; }
  return { r, seen };
}

before(async () => { if (!RV) return; S = await start({ port: 8792, chunk: 3 }); base = S.base; });
after(async () => { if (S) await S.stop(); });

test("route matrix: only the owner reaches owner routes; the service token reaches only its two routes", { skip }, async () => {
  const src = readFileSync(new URL("../src/index.js", import.meta.url), "utf8");
  const routes = [...src.matchAll(/"(GET|POST) (\/[^"]*)":/g)].map((m) => [m[1], m[2]]);
  const owner = routes.filter(([, p]) => !p.startsWith("/api/machine/")), machine = routes.filter(([, p]) => p.startsWith("/api/machine/"));
  assert.equal(machine.length, 2); assert.ok(owner.length >= 10, `routes found: ${routes.length}`);
  const call = (tok, [m, p]) => fetch(base + p, m === "GET" ? { headers: H(tok) } : { method: "POST", headers: H(tok, null, { "Content-Type": "application/json", "X-Review": "1" }), body: "{}" });
  for (const r of [...routes, ["GET", "/nope"], ["POST", "/api/nope"]]) {
    for (const [who, tok] of [["none", null], ["garbage", "x.y.z"], ["intruder", S.ownerToken("intruder@example.com")]])
      assert.equal((await call(tok, r)).status, 403, `${who} ${r.join(" ")}`);
  }
  for (const r of owner) assert.equal((await call(S.machineToken(), r)).status, 403, `machine must not reach ${r.join(" ")}`);
  for (const r of machine) assert.equal((await call(S.ownerToken(), r)).status, 403, `owner token must not reach ${r.join(" ")}`);
  for (const r of [["GET", "/nope"], ["POST", "/api/nope"]]) assert.equal((await call(S.machineToken(), r)).status, 403);
  for (const r of owner) assert.notEqual((await call(S.ownerToken(), r)).status, 403, `owner should reach ${r.join(" ")}`);
});

test("publish: nothing public until you publish; later drafts stay private; lines only", { skip }, async () => {
  assert.equal((await machineReq("/api/machine/review", { body: variant("2027-03-10T14:00:00Z", null), now: "2027-03-10T14:01:00Z" })).status, 200);
  assert.equal((await machineReq("/api/machine/published")).status, 404, "nothing published yet");
  const f = RV.model_order, out = RV.rest_order.filter((k) => !f.includes(k));
  const edits = [["move", { team: f[25], to_line: 2 }], ["move", { team: f[40], to_line: 8 }], ["add", { team: out[0] }], ["swap", { team: f[0], with: f[6] }],
    ["move", { team: f[60], to_line: 12 }], ["move", { team: f[12], to_line: 6 }], ["move", { team: f[33], to_line: 7 }], ["move", { team: f[20], to_line: 4 }], ["move", { team: f[50], to_line: 10 }]];
  const ids = [];
  for (const [i, [op, x]] of edits.entries()) {
    const r = await J(await ownerReq("/api/edits", { now: `2027-03-10T15:0${i}:00Z`, body: { op, ...x, reason_code: "recent_form", confidence: 2, client_at: `2027-03-10T15:0${i}:05Z` } }));
    assert.equal(r.status, 200, JSON.stringify(r.body)); ids.push(r.body.edit.id);
  }
  assert.equal((await ownerReq("/api/edits", { now: "2027-03-10T15:20:00Z", body: { op: "undo", undo_of: ids[3] } })).status, 200);
  let st = (await J(await ownerReq("/api/state", { now: "2027-03-10T15:30:00Z" }))).body;
  assert.equal(st.publication, null);
  assert.equal((await J(await ownerReq("/api/publish", { now: "2027-03-10T16:00:00Z", body: {} }))).status, 200);
  let pub = (await J(await machineReq("/api/machine/published"))).body;
  assert.equal(pub.source, "published"); assert.deepEqual(Object.fromEntries(pub.teams.map((t) => [t.key, t.line])), st.b3);
  for (const t of pub.teams) assert.deepEqual(Object.keys(t).sort(), ["key", "line", "team"]);
  const text = JSON.stringify(pub); for (const w of ["reason", "confidence", "explanation", "B2", "shadow", "p_in", "model_line"]) assert.ok(!text.includes(w), w);
  // a draft after publishing
  assert.equal((await ownerReq("/api/edits", { now: "2027-03-10T16:05:00Z", body: { op: "move", team: f[30], to_line: 3, reason_code: "head_to_head", confidence: 1 } })).status, 200);
  const pub2 = (await J(await machineReq("/api/machine/published"))).body;
  assert.equal(pub2.sha256, pub.sha256, "draft not visible publicly"); assert.equal(Object.fromEntries(pub2.teams.map((t) => [t.key, t.line]))[f[30]], st.b3[f[30]]);
  st = (await J(await ownerReq("/api/state", { now: "2027-03-10T16:06:00Z" }))).body; assert.equal(st.publication.current, false);
});

test("research freeze in chunks equals the Python engine, and verifies", { skip }, async () => {
  assert.equal((await machineReq("/api/machine/review", { body: variant("2027-03-14T15:30:00Z", [{ conf: "big-ten", game: "Purdue vs Michigan" }]), now: "2027-03-14T15:31:00Z" })).status, 200);
  const { r, seen } = await freezeLoop("research", "2027-03-14T16:02:00Z");
  assert.equal(r.status, "frozen", JSON.stringify(r)); assert.ok(seen.filter((x) => x === "in_progress").length >= 2, `chunked: ${seen}`);
  const b = JSON.parse(await (await ownerReq("/api/export?kind=research")).text());
  const rvR = variant("2027-03-14T15:30:00Z", null);
  const py = JSON.parse(python(path.join(REPO, "review-worker/test/py_engine.py"), [{ order: rvR.model_order, rest: rvR.rest_order, info: rvR.all_info, edits: b.edit_history.entries_as_logged, season: 2027 }]));
  const slots = RV.lines.flatMap((n, i) => Array(n).fill(i + 1));
  assert.deepEqual(Object.fromEntries(b.brackets.B3_manual.map((x) => [x.key, x.line])), Object.fromEntries(py.results[0].order.map((k, i) => [k, slots[i]])));
  assert.deepEqual(b.edit_history.applied.map((e) => e.teams_changed), py.results[0].applied.map((e) => e.teams_changed));
  assert.ok((await J(await ownerReq("/api/verify", { now: "2027-03-14T16:10:00Z", body: { kind: "research" } }))).body.ok);
});

test("incomplete final: waits for the finals, freezes only in the last 10 minutes, warns you, and is labelled publicly", { skip }, async () => {
  assert.equal((await machineReq("/api/machine/review", { body: variant("2027-03-14T21:20:00Z", [{ conf: "big-ten", game: "Purdue vs Michigan" }]), now: "2027-03-14T21:20:30Z" })).status, 200);
  let r = (await J(await ownerReq("/api/freeze", { now: "2027-03-14T21:25:00Z", body: { kind: "final" } }))).body;
  assert.equal(r.status, "waiting"); assert.match(r.error, /Waiting for conference finals \(Purdue vs Michigan\)/);
  const { r: f } = await freezeLoop("final", "2027-03-14T21:36:00Z");
  assert.equal(f.status, "frozen"); assert.equal(f.final_results_complete, false);
  const st = (await J(await ownerReq("/api/state", { now: "2027-03-14T21:37:00Z" }))).body;
  assert.ok(st.warnings.some((w) => /FINAL SNAPSHOT IS INCOMPLETE/.test(w) && /Purdue vs Michigan/.test(w)), JSON.stringify(st.warnings));
  assert.equal(st.freezes.find((x) => x.kind === "final").complete, false);
  const pub = (await J(await machineReq("/api/machine/published"))).body;
  assert.equal(pub.source, "final_freeze"); assert.equal(pub.complete, false); assert.deepEqual(pub.pending, ["Purdue vs Michigan"]);
  assert.equal((await ownerReq("/api/publish", { now: "2027-03-14T21:38:00Z", body: {} })).status, 409);
});

test("automatic backup: button and daily cron both copy everything and check it; the backup can't be altered", { skip }, async () => {
  const r = (await J(await ownerReq("/api/backup", { now: "2027-03-14T21:40:00Z", body: {} }))).body;
  assert.ok(r.ok, JSON.stringify(r)); assert.deepEqual(r.counts.main, r.counts.backup); assert.ok(r.edit_digest_match && r.freezes_match);
  const n = () => Number(/"n": (\d+)/.exec(sql(S.persist, "SELECT COUNT(*) AS n FROM backup_runs", "jbp_backup").out)[1]);
  const before = n();
  const cron = await fetch(base + "/__scheduled?cron=23+9+*+*+*"); assert.equal(cron.status, 200);       // local-only trigger for the daily cron
  await new Promise((x) => setTimeout(x, 1500));
  assert.equal(n(), before + 1, "the cron ran a backup");
  const runs = sql(S.persist, "SELECT MIN(ok) AS allok FROM backup_runs", "jbp_backup"); assert.ok(/"allok": 1/.test(runs.out), runs.out);
  for (const c of ["UPDATE edits SET at = 'x'", "DELETE FROM freezes", "DELETE FROM backup_runs", "UPDATE reviews SET core = ''"]) assert.equal(sql(S.persist, c, "jbp_backup").ok, false, c);
  // remember everything to compare after restoring
  orig.state = (await J(await ownerReq("/api/state", { now: "2027-03-14T21:41:00Z" }))).body;
  orig.published = (await J(await machineReq("/api/machine/published"))).body;
  const bundle = await (await ownerReq("/api/backup-bundle", { now: "2027-03-14T21:42:00Z" })).text();
  orig.bundlePath = path.join(mkdtempSync(path.join(tmpdir(), "jbp-bundle-")), "bundle.json"); writeFileSync(orig.bundlePath, bundle);
  const b = JSON.parse(bundle); assert.equal(b.format, "jbp-review-backup"); assert.equal(b.edits.length, 11); assert.equal(b.freezes.length, 2);
  assert.ok((await J(await ownerReq("/api/state", { now: "2027-03-14T21:43:00Z" }))).body.backup.last_download);
});

async function checkRestored(label, persist) {
  await S.stop(); S = await start({ port: 8792, chunk: 3, persist }); base = S.base;
  const st = (await J(await ownerReq("/api/state", { now: "2027-03-14T21:50:00Z" }))).body;
  assert.deepEqual(st.edits, orig.state.edits, `${label}: edits, ids, server and client timestamps, undo entries`);
  assert.ok(st.edits.some((e) => e.op === "undo"), "undo history kept");
  assert.deepEqual(st.b3, orig.state.b3, `${label}: B3`);
  assert.deepEqual(st.freezes.map((f) => [f.kind, f.sha256, f.complete]), orig.state.freezes.map((f) => [f.kind, f.sha256, f.complete]), `${label}: snapshot hashes`);
  for (const kind of ["research", "final"]) assert.ok((await J(await ownerReq("/api/verify", { now: "2027-03-14T21:51:00Z", body: { kind } }))).body.ok, `${label}: ${kind} verifies`);
  assert.deepEqual((await J(await machineReq("/api/machine/published"))).body, orig.published, `${label}: published lines`);
  for (const c of ["UPDATE edits SET at = 'x'", "DELETE FROM freezes", "DELETE FROM publications"]) assert.equal(sql(persist, c).ok, false, `${label}: protection back on (${c})`);
}

test("restore (a): from the backup database into a fresh database", { skip }, async () => {
  const sqlFile = path.join(mkdtempSync(path.join(tmpdir(), "jbp-r1-")), "restore.sql");
  const out = execNode(["scripts/restore.mjs", "--from-db", "jbp_backup", "--local", "--persist-to", S.persist, "--out", sqlFile]);
  assert.match(out, /11 edits/);
  const text = readFileSync(sqlFile, "utf8"); assert.ok((text.match(/^UPDATE reviews SET body = body \|\| /gm) || []).length > 20, "long texts restored in pieces");
  const fresh = mkdtempSync(path.join(tmpdir(), "jbp-fresh-a-"));
  wr(["d1", "execute", "jbp_private", "--local", "--persist-to", fresh, "--file", sqlFile]);
  wr(["d1", "migrations", "apply", "jbp_backup", "--local", "--persist-to", fresh]);
  await checkRestored("from backup database", fresh);
});

test("restore (b): from the downloaded bundle into a fresh database", { skip }, async () => {
  const sqlFile = path.join(mkdtempSync(path.join(tmpdir(), "jbp-r2-")), "restore.sql");
  execNode(["scripts/restore.mjs", "--from-bundle", orig.bundlePath, "--out", sqlFile]);
  const fresh = mkdtempSync(path.join(tmpdir(), "jbp-fresh-b-"));
  wr(["d1", "execute", "jbp_private", "--local", "--persist-to", fresh, "--file", sqlFile]);
  wr(["d1", "migrations", "apply", "jbp_backup", "--local", "--persist-to", fresh]);
  await checkRestored("from bundle", fresh);
});

import { execFileSync } from "node:child_process";
function execNode(args) { return execFileSync("node", args, { cwd: path.resolve(new URL("..", import.meta.url).pathname), env: { ...process.env, CI: "1" }, maxBuffer: 1 << 28 }).toString(); }
