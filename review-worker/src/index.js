// Owner-only review Worker (docs/43-44). Not deployed. Every HTTP request must carry a valid Cloudflare Access JWT:
//   owner (your email)        -> page, state, preview/save/undo edits, freeze, verify, export
//   machine (service token)   -> upload a public-data review, read the published lines (no edits, reasons or confidence)
// The Selection Sunday timer calls freeze/verify through the ReviewOps RPC entrypoint (service binding), not over HTTP.
import { WorkerEntrypoint } from "cloudflare:workers";
import { authenticate } from "./auth.js";
import { season as seasonCfg } from "./config.js";
import { checkEdit, linesOf, slotsOf, REASONS, when } from "./engine.js";
import { b3, buildFreeze, coreOf, cutoffOf, sha256hex, verifyFreeze } from "./freeze.js";
import PAGE from "./page.html";

const EARLIEST_MS = 30 * 60000;
const iso = (ms) => new Date(ms).toISOString().replace(/\.\d{3}Z$/, "Z");
const SEC = {
  "Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow", "X-Frame-Options": "DENY", "X-Content-Type-Options": "nosniff",
  "Referrer-Policy": "no-referrer", "Content-Security-Policy": "default-src 'none'; script-src 'self' 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'self'; img-src 'self' data:; base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
};
const json = (obj, status = 200) => new Response(JSON.stringify(obj), { status, headers: { ...SEC, "Content-Type": "application/json" } });
const deny = () => new Response("Forbidden", { status: 403, headers: SEC });

function localNow(env, req) {
  // A fake clock is accepted only in the local test setup (Access pointed at 127.0.0.1); production always uses server time.
  const local = /^127\.0\.0\.1:\d+$/.test(env.ACCESS_TEAM_DOMAIN || "") && env.ALLOW_TEST_OVERRIDES === "local-test-only";
  const h = req && req.headers.get("X-Test-Now");
  return local && h && when(h) !== null ? when(h) : Date.now();
}

async function latestReview(env, season, withBody = false) {
  return env.DB.prepare(`SELECT collected_at, core${withBody ? ", body" : ""} FROM reviews WHERE season = ? ORDER BY collected_at DESC LIMIT 1`).bind(season).first();
}
async function allEdits(env, season) {
  const { results } = await env.DB.prepare("SELECT id, at, client_at, body FROM edits WHERE season = ? ORDER BY seq").bind(season).all();
  return results.map((r) => ({ ...JSON.parse(r.body), id: r.id, at: r.at, client_at: r.client_at }));
}
async function freezeRow(env, season, kind) {
  return env.DB.prepare("SELECT season, kind, frozen_at, sha256, body FROM freezes WHERE season = ? AND kind = ?").bind(season, kind).first();
}

// Edits are open until the final snapshot exists or its confirmed deadline passes.
async function editWindow(env, season, cfg, now) {
  if (await freezeRow(env, season, "final")) return { open: false, why: "The final snapshot is frozen." };
  const fd = cutoffOf(cfg, "final");
  if (fd !== null && now > fd) return { open: false, why: `Past the final deadline (${iso(fd)}).` };
  const rc = cutoffOf(cfg, "research");
  return { open: true, note: now > rc ? "After the noon research cutoff: new edits count only for the final snapshot." : null };
}

function slim(rv) {
  const { teams_by_key, ...rest } = rv;
  return rest;
}

async function state(env, season, cfg, now) {
  const r = await latestReview(env, season, true);
  const edits = await allEdits(env, season);
  const freezes = [];
  for (const kind of ["research", "final"]) {
    const f = await freezeRow(env, season, kind);
    const c = cutoffOf(cfg, kind);
    freezes.push({ kind, cutoff: c === null ? null : iso(c), earliest: c === null ? null : iso(c - EARLIEST_MS), frozen: !!f, frozen_at: f ? f.frozen_at : null, sha256: f ? f.sha256 : null });
  }
  const win = await editWindow(env, season, cfg, now);
  if (!r) return json({ season, review: null, edits, freezes, window: win, reasons: REASONS });
  const core = JSON.parse(r.core), B = b3(core, edits, cfg);
  const rest = JSON.stringify({ season, server_time: iso(now), edits, b3_order: B.order, b3: linesOf(B.order, slotsOf(cfg.lines)), applied: B.applied, notes: B.notes, freezes, window: win, reasons: REASONS });
  // The stored review text is passed through unparsed (it is large); everything else is built here.
  return new Response(`{"review":${r.body},${rest.slice(1)}`, { headers: { ...SEC, "Content-Type": "application/json" } });
}

function cleanEdit(input) {
  // Only known fields are kept; everything is re-validated by the engine.
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
  const rv = JSON.parse(r.core), prior = await allEdits(env, season);
  if (e.op === "undo" && !prior.some((p) => p.id === e.undo_of && p.op !== "undo")) return json({ error: "Nothing to undo with that id." }, 422);
  const before = b3(rv, prior, cfg), after = b3(rv, [...prior, e], cfg);
  if (e.op !== "undo" && !after.applied.some((a) => a.id === e.id)) return json({ error: (after.notes.find((n) => n.includes(e.id)) || "Not possible").replace(/^Edit \S+ (not applied|skipped): /, "") }, 422);
  const L0 = linesOf(before.order, slotsOf(cfg.lines)), L1 = linesOf(after.order, slotsOf(cfg.lines));
  const changes = [...new Set([...Object.keys(L0), ...Object.keys(L1)])].filter((k) => L0[k] !== L1[k])
    .map((k) => ({ key: k, team: (rv.all_info[k] || {}).team || k, from: L0[k] ?? null, to: L1[k] ?? null }));
  if (input.dry_run) return json({ preview: true, edit: e, changes });
  await env.DB.prepare("INSERT INTO edits (season, id, at, client_at, body) VALUES (?, ?, ?, ?, ?)").bind(season, e.id, e.at, clientAt, JSON.stringify(e)).run();
  return json({ saved: true, edit: e, changes, note: win.note });
}

async function doFreeze(env, season, kind, now) {
  const cfg = seasonCfg(env, season);
  if (!cfg) return { status: "error", error: "unknown season" };
  const existing = await freezeRow(env, season, kind);
  if (existing) {
    const v = await verifyFreeze({ row: existing, season, kind, cfg, now });
    if (!v.ok) return { status: "error", error: `existing ${kind} freeze fails verification: ${v.problems}` };
    return { status: "already_frozen", sha256: existing.sha256, frozen_at: existing.frozen_at };
  }
  const cutoff = cutoffOf(cfg, kind);
  if (cutoff === null) return { status: "error", error: `No confirmed ${kind} deadline for ${season}.` };
  const { results } = await env.DB.prepare("SELECT collected_at, core, body_sha256 FROM reviews WHERE season = ? ORDER BY collected_at DESC LIMIT 60").bind(season).all();
  const edits = await allEdits(env, season);
  let f;
  try { f = await buildFreeze({ season, kind, cfg, reviews: results, edits, now }); } catch (err) { return { status: "error", error: err.message }; }
  // Guard against freezing too early by mistake: not before 30 minutes ahead of the cutoff, except a final freeze once every
  // Selection Sunday conference final is in the data (and the research cutoff has passed).
  const early = now < cutoff - EARLIEST_MS && !(kind === "final" && f.body.final_results_complete && now > cutoffOf(cfg, "research"));
  if (early) return { status: "error", error: `Too early: the ${kind} snapshot can't be frozen before ${iso(cutoff - EARLIEST_MS)}${kind === "final" ? " unless every conference final is in" : ""}.` };
  try {
    await env.DB.prepare("INSERT INTO freezes (season, kind, frozen_at, sha256, body) VALUES (?, ?, ?, ?, ?)").bind(season, kind, f.body.frozen_at, f.sha256, f.text).run();
  } catch {
    return doFreeze(env, season, kind, now);                     // another run froze first: verify and report that one
  }
  return { status: "frozen", sha256: f.sha256, frozen_at: f.body.frozen_at, review: f.body.review_file, final_results_complete: f.body.final_results_complete, skipped: f.body.skipped_reviews.length };
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
  return json({ stored: true, season: rv.season, collected_at: rv.inputs.collected_at, bytes: text.length });
}

// What the public site may show: team and line only. Before the final freeze it is the live B3; after it, the frozen final B3.
async function published(env, season, cfg) {
  const f = await freezeRow(env, season, "final");
  if (f) return json({ season, source: "final_freeze", sha256: f.sha256, teams: JSON.parse(f.body).brackets.B3_manual.map(({ key, team, line }) => ({ key, team, line })) });
  const r = await latestReview(env, season);
  if (!r) return json({ error: "no review" }, 404);
  const rv = JSON.parse(r.core), B = b3(rv, await allEdits(env, season), cfg), L = linesOf(B.order, slotsOf(cfg.lines));
  return json({ season, source: "live", collected_at: r.collected_at, teams: B.order.map((k) => ({ key: k, team: (rv.all_info[k] || {}).team || k, line: L[k] })) });
}

export default {
  async fetch(req, env) {
    const who = await authenticate(req, env);
    if (!who) return deny();                                      // fail closed: no valid Access identity, nothing at all
    const url = new URL(req.url), now = localNow(env, req), p = url.pathname;
    const season = Number(url.searchParams.get("season") || env.SEASON || 2027), cfg = seasonCfg(env, season);
    if (!cfg) return json({ error: "unknown season" }, 404);
    if (req.method !== "GET") {                                   // writes: same-origin JSON only (blocks cross-site form posts)
      const o = req.headers.get("Origin");
      if ((o && o !== url.origin) || !(req.headers.get("Content-Type") || "").startsWith("application/json")) return deny();
    }
    if (who.kind === "machine") {
      if (p === "/api/machine/review" && req.method === "POST") return ingest(env, await req.text(), now);
      if (p === "/api/machine/published" && req.method === "GET") return published(env, season, cfg);
      return deny();
    }
    // owner
    if (p.startsWith("/api/machine/")) return deny();
    if (req.method === "POST" && req.headers.get("X-Review") !== "1") return deny();
    if (p === "/" && req.method === "GET") return new Response(PAGE, { headers: { ...SEC, "Content-Type": "text/html; charset=utf-8" } });
    if (p === "/api/state" && req.method === "GET") return state(env, season, cfg, now);
    if (p === "/api/edits" && req.method === "POST") return saveEdit(env, season, cfg, await req.json().catch(() => ({})), now);
    if (p === "/api/freeze" && req.method === "POST") { const { kind } = await req.json().catch(() => ({})); return ["research", "final"].includes(kind) ? json(await doFreeze(env, season, kind, now)) : json({ error: "kind" }, 422); }
    if (p === "/api/verify" && req.method === "POST") { const { kind } = await req.json().catch(() => ({})); return ["research", "final"].includes(kind) ? json(await doVerify(env, season, kind, now)) : json({ error: "kind" }, 422); }
    if (p === "/api/export-edits" && req.method === "GET")      // your own backup of the full edit log (D1 free restore covers only 7 days)
      return new Response(JSON.stringify(await allEdits(env, season), null, 1), { headers: { ...SEC, "Content-Type": "application/json", "Content-Disposition": `attachment; filename="${season}_edits.json"` } });
    if (p === "/api/export" && req.method === "GET") {
      const kind = url.searchParams.get("kind"), f = ["research", "final"].includes(kind) ? await freezeRow(env, season, kind) : null;
      if (!f) return json({ error: "no such freeze" }, 404);
      return new Response(f.body, { headers: { ...SEC, "Content-Type": "application/json", "Content-Disposition": `attachment; filename="${season}_${kind === "final" ? "final_" : ""}freeze.json"`, "X-Sha256": f.sha256 } });
    }
    return json({ error: "not found" }, 404);
  },
};

// Called by the timer Worker through a service binding (not reachable from the internet).
export class ReviewOps extends WorkerEntrypoint {
  async freeze(season, kind) { return doFreeze(this.env, season, kind, Date.now()); }
  async verify(season, kind) { return doVerify(this.env, season, kind, Date.now()); }
}
