// Owner-only review Worker (docs/43-45). Not deployed. Every HTTP request must carry a valid Cloudflare Access JWT:
//   owner (your email)        -> page, state, preview/save/undo edits, publish, freeze (backup button), verify, backups, exports
//   machine (service token)   -> upload a public-data review; read the PUBLISHED lines (team + line only)
// The timer Worker calls freeze/verify/backup through the ReviewOps RPC entrypoint (service binding), never over HTTP.
// A daily cron copies every record into a second, append-only D1 database (BACKUP).
import { WorkerEntrypoint } from "cloudflare:workers";
import { authenticate } from "./auth.js";
import { season as seasonCfg } from "./config.js";
import { checkEdit, linesOf, slotsOf, REASONS, when, applyEdits } from "./engine.js";
import { b3, choose, coreOf, cutoffOf, earliestOf, editsFor, iso, replayStart, replayStep, sha256hex, verifyFreeze, writeBody } from "./freeze.js";
import { runBackup, bundle } from "./backup.js";
import PAGE from "./page.html";

// Edits replayed per request. Measured locally at ~2 ms per 100 edits; 150 keeps a chunk far under the 10 ms free limit.
const CHUNK = 150;
const SEC = {
  "Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow", "X-Frame-Options": "DENY", "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer", "Content-Security-Policy": "default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
};
const json = (obj, status = 200) => new Response(JSON.stringify(obj), { status, headers: { ...SEC, "Content-Type": "application/json" } });
const deny = () => new Response("Forbidden", { status: 403, headers: SEC });
const isLocalTest = (env) => /^127\.0\.0\.1:\d+$/.test(env.ACCESS_TEAM_DOMAIN || "") && env.ALLOW_TEST_OVERRIDES === "local-test-only";

function localNow(env, req) {
  // A fake clock is accepted only in the local test setup (Access pointed at 127.0.0.1); production always uses server time.
  const h = req && req.headers.get("X-Test-Now");
  return isLocalTest(env) && h && when(h) !== null ? when(h) : Date.now();
}
const chunkSize = (env) => (isLocalTest(env) && Number(env.TEST_CHUNK) > 0 ? Number(env.TEST_CHUNK) : CHUNK);

async function latestReview(env, season, withBody = false) {
  return env.DB.prepare(`SELECT collected_at, core${withBody ? ", body" : ""} FROM reviews WHERE season = ? ORDER BY collected_at DESC LIMIT 1`).bind(season).first();
}
async function allEdits(env, season, maxSeq = null) {
  const q = maxSeq == null ? env.DB.prepare("SELECT seq, id, at, client_at, body FROM edits WHERE season = ? ORDER BY seq").bind(season)
    : env.DB.prepare("SELECT seq, id, at, client_at, body FROM edits WHERE season = ? AND seq <= ? ORDER BY seq").bind(season, maxSeq);
  const { results } = await q.all();
  return results.map((r) => ({ ...JSON.parse(r.body), id: r.id, at: r.at, client_at: r.client_at, seq: r.seq }));
}
const strip = (es) => es.map(({ seq, ...e }) => e);
async function freezeRow(env, season, kind) {
  return env.DB.prepare("SELECT season, kind, frozen_at, sha256, body FROM freezes WHERE season = ? AND kind = ?").bind(season, kind).first();
}
async function latestPublication(env, season) {
  return env.DB.prepare("SELECT seq, at, review_collected_at, edits_through_seq, lines, sha256 FROM publications WHERE season = ? ORDER BY seq DESC LIMIT 1").bind(season).first();
}

// Edits are open until the final snapshot exists or its confirmed deadline passes.
async function editWindow(env, season, cfg, now) {
  if (await freezeRow(env, season, "final")) return { open: false, why: "The final snapshot is frozen." };
  const fd = cutoffOf(cfg, "final");
  if (fd !== null && now > fd) return { open: false, why: `Past the final deadline (${iso(fd)}).` };
  const rc = cutoffOf(cfg, "research"), rf = await freezeRow(env, season, "research");
  return { open: true, note: rf ? "The research snapshot is frozen: new edits count only for the final snapshot." : now > rc ? "After the noon research cutoff: new edits count only for the final snapshot." : null };
}

const slim = ({ teams_by_key, ...rest }) => rest;

async function freezeSummary(env, season, cfg) {
  const out = [];
  for (const kind of ["research", "final"]) {
    const f = await freezeRow(env, season, kind), c = cutoffOf(cfg, kind);
    let complete = null, pending = null;
    if (f && kind === "final") { const b = JSON.parse(f.body); complete = b.final_results_complete; pending = b.conference_games_pending; }
    out.push({ kind, cutoff: c === null ? null : iso(c), earliest: c === null ? null : iso(earliestOf(cfg, kind)), frozen: !!f, frozen_at: f ? f.frozen_at : null, sha256: f ? f.sha256 : null, complete, pending });
  }
  return out;
}

async function state(env, season, cfg, now) {
  const r = await latestReview(env, season, true);
  const edits = await allEdits(env, season), freezes = await freezeSummary(env, season, cfg), win = await editWindow(env, season, cfg, now);
  const pub = await latestPublication(env, season), lastEdit = edits.length ? edits[edits.length - 1].seq : 0;
  const lastBackup = env.BACKUP ? await env.BACKUP.prepare("SELECT at, ok FROM backup_runs ORDER BY seq DESC LIMIT 1").first().catch(() => null) : null;
  const lastDownload = await env.DB.prepare("SELECT at FROM downloads ORDER BY seq DESC LIMIT 1").first();
  const warnings = [];
  const fin = freezes.find((f) => f.kind === "final");
  if (fin.frozen && fin.complete === false) warnings.push(`FINAL SNAPSHOT IS INCOMPLETE: frozen before ${fin.pending == null ? "the scoreboard could be read" : "these finals ended: " + fin.pending.map((g) => g.game || g.conf).join(", ")}. Their champions are projected, and the public site says so.`);
  if (lastBackup && !lastBackup.ok) warnings.push("The last automatic backup reported a problem. Open Snapshots → Backups.");
  const meta = { season, server_time: iso(now), edits: strip(edits), freezes, window: win, reasons: REASONS, warnings,
    publication: pub ? { at: pub.at, sha256: pub.sha256, edits_through_seq: pub.edits_through_seq, review_collected_at: pub.review_collected_at, current: pub.edits_through_seq === lastEdit && !!r && pub.review_collected_at === r.collected_at } : null,
    backup: { last_run: lastBackup, last_download: lastDownload ? lastDownload.at : null } };
  if (!r) return json({ ...meta, review: null });
  const core = JSON.parse(r.core), B = b3(core, strip(edits), cfg);
  const rest = JSON.stringify({ ...meta, b3_order: B.order, b3: linesOf(B.order, slotsOf(cfg.lines)), applied: B.applied, notes: B.notes });
  return new Response(`{"review":${r.body},${rest.slice(1)}`, { headers: { ...SEC, "Content-Type": "application/json" } });   // large review text passed through unparsed
}

function cleanEdit(input) {
  const e = { op: input.op };
  for (const f of ["team", "with", "add", "remove", "reason_code", "explanation", "undo_of"]) if (input[f] != null && input[f] !== "") e[f] = String(input[f]).slice(0, f === "explanation" ? 500 : 80);
  if (input.to_line != null && input.to_line !== "") { const n = Number(input.to_line); if (!Number.isInteger(n) || n < 1 || n > 16) return { error: "line must be a whole number from 1 to 16" }; e.to_line = n; }
  if (input.confidence != null) e.confidence = Number(input.confidence);
  return { e };
}

async function saveEdit(env, season, cfg, input, now) {
  const win = await editWindow(env, season, cfg, now);
  if (!win.open) return json({ error: win.why }, 409);
  const r = await latestReview(env, season);
  if (!r) return json({ error: "No review uploaded yet." }, 409);
  const { e, error } = cleanEdit(input);
  if (error) return json({ error }, 422);
  e.id = "e" + crypto.randomUUID().replace(/-/g, "").slice(0, 12);
  e.at = iso(now);                                              // server time is the record; the phone's clock is kept for reference
  const clientAt = typeof input.client_at === "string" && when(input.client_at) !== null ? input.client_at : null;
  const bad = checkEdit(e);
  if (bad.length) return json({ error: bad.join("; ") }, 422);
  const rv = JSON.parse(r.core), prior = strip(await allEdits(env, season)), slots = slotsOf(cfg.lines);
  if (e.op === "undo" && !prior.some((p) => p.id === e.undo_of && p.op !== "undo")) return json({ error: "Nothing to undo with that id." }, 422);
  const before = b3(rv, prior, cfg);
  // A new edit needs one more step on top of the current bracket; only an undo needs a replay without the retracted edit.
  const after = e.op === "undo" ? b3(rv, [...prior, e], cfg) : applyEdits(before.order, before.rest, [e], slots, rv.all_info, cfg.selection_sunday);
  if (e.op !== "undo" && !after.applied.some((a) => a.id === e.id)) return json({ error: (after.notes.find((n) => n.includes(e.id)) || "Not possible").replace(/^Edit \S+ (not applied|skipped): /, "") }, 422);
  const L0 = linesOf(before.order, slots), L1 = linesOf(after.order, slots);
  const changes = [...new Set([...Object.keys(L0), ...Object.keys(L1)])].filter((k) => L0[k] !== L1[k])
    .map((k) => ({ key: k, team: (rv.all_info[k] || {}).team || k, from: L0[k] ?? null, to: L1[k] ?? null }));
  if (input.dry_run) return json({ preview: true, edit: e, changes });
  await env.DB.prepare("INSERT INTO edits (season, id, at, client_at, body) VALUES (?, ?, ?, ?, ?)").bind(season, e.id, e.at, clientAt, JSON.stringify(e)).run();
  return json({ saved: true, edit: e, changes, note: win.note });
}

// Publish: the current B3 becomes what the public site shows (lines only). Until you publish, edits stay private drafts.
async function publish(env, season, cfg, now) {
  if (await freezeRow(env, season, "final")) return json({ error: "The final snapshot is frozen; it is what the site shows now." }, 409);
  const r = await latestReview(env, season);
  if (!r) return json({ error: "No review uploaded yet." }, 409);
  const edits = await allEdits(env, season), rv = JSON.parse(r.core), B = b3(rv, strip(edits), cfg), L = linesOf(B.order, slotsOf(cfg.lines));
  const lines = JSON.stringify(B.order.map((k) => ({ key: k, team: (rv.all_info[k] || {}).team || k, line: L[k] })));
  const through = edits.length ? edits[edits.length - 1].seq : 0, sha = await sha256hex(lines);
  await env.DB.prepare("INSERT INTO publications (season, at, review_collected_at, edits_through_seq, lines, sha256) VALUES (?, ?, ?, ?, ?, ?)").bind(season, iso(now), r.collected_at, through, lines, sha).run();
  return json({ published: true, at: iso(now), sha256: sha });
}

// Freeze, in one request or, for a long edit log, in chunks: each call replays at most CHUNK edits and reports progress;
// callers (timer, page button) repeat until "frozen". The final text is identical to a single pass.
async function doFreeze(env, season, kind, now, maxChunk = chunkSize(env)) {
  const cfg = seasonCfg(env, season);
  if (!cfg) return { status: "error", error: "unknown season" };
  const existing = await freezeRow(env, season, kind);
  if (existing) {
    const v = await verifyFreeze({ row: existing, season, kind, cfg, now });
    if (!v.ok) return { status: "error", error: `existing ${kind} freeze fails verification: ${v.problems}` };
    return { status: "already_frozen", sha256: existing.sha256, frozen_at: existing.frozen_at, final_results_complete: v.final_results_complete };
  }
  const { results } = await env.DB.prepare("SELECT collected_at, core, body_sha256 FROM reviews WHERE season = ? ORDER BY collected_at DESC LIMIT 60").bind(season).all();
  const chosen = choose({ season, kind, cfg, reviews: results, now });
  if (chosen.error) return { status: chosen.wait ? "waiting" : "error", error: chosen.error };
  const job = await env.DB.prepare("SELECT review_collected_at, max_seq, state FROM freeze_jobs WHERE season = ? AND kind = ?").bind(season, kind).first();
  let maxSeq, B;
  if (job && job.review_collected_at === chosen.pick.r.collected_at) { maxSeq = job.max_seq; B = JSON.parse(job.state); }
  else {
    const last = await env.DB.prepare("SELECT MAX(seq) AS m FROM edits WHERE season = ?").bind(season).first();
    maxSeq = last.m || 0; B = replayStart(chosen.pick.rv);
  }
  const { inTime, late } = editsFor(strip(await allEdits(env, season, maxSeq)), chosen.cutoff);
  B = replayStep(B, chosen.pick.rv, inTime, cfg, maxChunk);
  if (B.i < inTime.length) {
    await env.DB.prepare("INSERT INTO freeze_jobs (season, kind, started_at, review_collected_at, max_seq, state) VALUES (?, ?, ?, ?, ?, ?) ON CONFLICT (season, kind) DO UPDATE SET review_collected_at = excluded.review_collected_at, max_seq = excluded.max_seq, state = excluded.state")
      .bind(season, kind, iso(now), chosen.pick.r.collected_at, maxSeq, JSON.stringify(B)).run();
    return { status: "in_progress", done: B.i, total: inTime.length };
  }
  let f;
  try { f = await writeBody({ season, kind, cfg, chosen, B, inTime, late, now }); } catch (err) { return { status: "error", error: err.message }; }
  try {
    await env.DB.prepare("INSERT INTO freezes (season, kind, frozen_at, sha256, body) VALUES (?, ?, ?, ?, ?)").bind(season, kind, f.body.frozen_at, f.sha256, f.text).run();
  } catch {
    return doFreeze(env, season, kind, now, maxChunk);            // another run froze first: verify and report that one
  }
  await env.DB.prepare("DELETE FROM freeze_jobs WHERE season = ? AND kind = ?").bind(season, kind).run();
  return { status: "frozen", sha256: f.sha256, frozen_at: f.body.frozen_at, review: f.body.review_file, final_results_complete: f.body.final_results_complete,
    pending: f.body.conference_games_pending, skipped: f.body.skipped_reviews.length };
}

async function doVerify(env, season, kind, now) {
  const cfg = seasonCfg(env, season);
  if (!cfg) return { ok: false, problems: ["unknown season"] };
  const v = await verifyFreeze({ row: await freezeRow(env, season, kind), season, kind, cfg, now });
  await env.DB.prepare("INSERT INTO verifications (season, kind, checked_at, ok, body) VALUES (?, ?, ?, ?, ?)").bind(season, kind, v.checked_at, v.ok ? 1 : 0, JSON.stringify(v)).run();
  return v;
}

async function ingest(env, body, now) {
  let rv; try { rv = typeof body === "string" ? JSON.parse(body) : body; } catch { return json({ error: "not JSON" }, 400); }
  const cfg = seasonCfg(env, rv && rv.season);
  if (!cfg) return json({ error: "unknown season" }, 422);
  const need = ["generated_at", "inputs", "brackets", "model_order", "rest_order", "all_info", "lines", "teams"];
  const miss = need.filter((k) => rv[k] == null);
  if (miss.length || !rv.inputs.collected_at || when(rv.inputs.collected_at) === null) return json({ error: `missing ${miss.join(", ") || "inputs.collected_at"}` }, 422);
  if (when(rv.inputs.collected_at) > now + 5 * 60000) return json({ error: "collected_at is in the future" }, 422);
  if (JSON.stringify(rv.lines) !== JSON.stringify(cfg.lines)) return json({ error: "wrong field format" }, 422);
  if (rv.edits && rv.edits.length) return json({ error: "reviews must not carry edits (they live only here)" }, 422);
  const text = JSON.stringify(slim(rv));
  try {
    await env.DB.prepare("INSERT INTO reviews (season, collected_at, generated_at, uploaded_at, body, body_sha256, core) VALUES (?, ?, ?, ?, ?, ?, ?)")
      .bind(rv.season, rv.inputs.collected_at, rv.generated_at, iso(now), text, await sha256hex(text), JSON.stringify(coreOf(rv))).run();
  } catch { return json({ error: "a review with this collection time already exists" }, 409); }
  return json({ stored: true, season: rv.season, collected_at: rv.inputs.collected_at });     // nothing private in the reply (it may reach Actions logs)
}

// What the public site may show: team and line only. After the final freeze: its B3, with completeness stated.
// Before it: the latest B3 you PUBLISHED (never unpublished drafts). Nothing published yet: 404, and the site shows the model.
async function published(env, season) {
  const f = await freezeRow(env, season, "final");
  if (f) {
    const b = JSON.parse(f.body);
    return json({ season, source: "final_freeze", complete: b.final_results_complete, pending: (b.conference_games_pending || []).map((g) => g.game || g.conf),
      frozen_at: b.frozen_at, sha256: f.sha256, teams: b.brackets.B3_manual.map(({ key, team, line }) => ({ key, team, line })) });
  }
  const p = await latestPublication(env, season);
  if (!p) return json({ error: "nothing published yet" }, 404);
  return json({ season, source: "published", complete: null, published_at: p.at, sha256: p.sha256, teams: JSON.parse(p.lines) });
}

const ROUTES_OWNER = {
  "GET /": async () => new Response(PAGE, { headers: { ...SEC, "Content-Type": "text/html; charset=utf-8" } }),
  "GET /api/state": (c) => state(c.env, c.season, c.cfg, c.now),
  "POST /api/edits": async (c) => saveEdit(c.env, c.season, c.cfg, await c.req.json().catch(() => ({})), c.now),
  "POST /api/publish": (c) => publish(c.env, c.season, c.cfg, c.now),
  "POST /api/freeze": async (c) => { const { kind } = await c.req.json().catch(() => ({})); return ["research", "final"].includes(kind) ? json(await doFreeze(c.env, c.season, kind, c.now)) : json({ error: "kind" }, 422); },
  "POST /api/verify": async (c) => { const { kind } = await c.req.json().catch(() => ({})); return ["research", "final"].includes(kind) ? json(await doVerify(c.env, c.season, kind, c.now)) : json({ error: "kind" }, 422); },
  "POST /api/backup": async (c) => json(await runBackup(c.env, c.now)),
  "GET /api/export": async (c) => {
    const kind = c.url.searchParams.get("kind"), f = ["research", "final"].includes(kind) ? await freezeRow(c.env, c.season, kind) : null;
    if (!f) return json({ error: "no such freeze" }, 404);
    return new Response(f.body, { headers: { ...SEC, "Content-Type": "application/json", "Content-Disposition": `attachment; filename="${c.season}_${kind === "final" ? "final_" : ""}freeze.json"`, "X-Sha256": f.sha256 } });
  },
  "GET /api/export-edits": async (c) => new Response(JSON.stringify(strip(await allEdits(c.env, c.season)), null, 1), { headers: { ...SEC, "Content-Type": "application/json", "Content-Disposition": `attachment; filename="${c.season}_edits.json"` } }),
  "GET /api/backup-bundle": async (c) => {      // off-site copy: everything needed to rebuild (docs/45); the download is logged so the page can remind you
    const text = await bundle(c.env, c.season, c.now);
    await c.env.DB.prepare("INSERT INTO downloads (at, what) VALUES (?, ?)").bind(iso(c.now), "bundle").run();
    return new Response(text, { headers: { ...SEC, "Content-Type": "application/json", "Content-Disposition": `attachment; filename="${c.season}_review_backup_${iso(c.now).slice(0, 10)}.json"` } });
  },
};
const ROUTES_MACHINE = {
  "POST /api/machine/review": async (c) => ingest(c.env, await c.req.text(), c.now),
  "GET /api/machine/published": (c) => published(c.env, c.season),
};
export const ROUTES = { owner: Object.keys(ROUTES_OWNER), machine: Object.keys(ROUTES_MACHINE) };

export default {
  async fetch(req, env) {
    const who = await authenticate(req, env);
    if (!who) return deny();                                      // fail closed: no valid Access identity, nothing at all
    const url = new URL(req.url), now = localNow(env, req);
    const season = Number(url.searchParams.get("season") || env.SEASON || 2027), cfg = seasonCfg(env, season);
    if (!cfg) return json({ error: "unknown season" }, 404);
    if (req.method !== "GET") {                                   // writes: same-origin JSON only (blocks cross-site form posts)
      const o = req.headers.get("Origin");
      if ((o && o !== url.origin) || !(req.headers.get("Content-Type") || "").startsWith("application/json")) return deny();
    }
    const key = `${req.method} ${url.pathname}`, c = { req, env, url, now, season, cfg };
    if (who.kind === "machine") return ROUTES_MACHINE[key] ? ROUTES_MACHINE[key](c) : deny();     // machine: two routes, nothing else
    if (url.pathname.startsWith("/api/machine/")) return deny();
    if (req.method === "POST" && req.headers.get("X-Review") !== "1") return deny();
    return ROUTES_OWNER[key] ? ROUTES_OWNER[key](c) : json({ error: "not found" }, 404);
  },
  async scheduled(event, env, ctx) {
    ctx.waitUntil(runBackup(env, Date.now()));                     // daily automatic backup into the BACKUP database
  },
};

// Called by the timer Worker through a service binding (not reachable from the internet). freeze() may return
// "in_progress" for a long edit log; the timer calls again until "frozen" (each call is a separate, small request).
export class ReviewOps extends WorkerEntrypoint {
  async freeze(season, kind) { const r = await doFreeze(this.env, season, kind, Date.now()); if (r.status === "frozen") await runBackup(this.env, Date.now()); return r; }
  async verify(season, kind) { return doVerify(this.env, season, kind, Date.now()); }
  async backup() { return runBackup(this.env, Date.now()); }
}
