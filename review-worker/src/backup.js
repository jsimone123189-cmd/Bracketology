// Automatic private backups (docs/45). Two layers, both inside your Cloudflare account and never in GitHub, the public site or logs:
//  1. A second D1 database (BACKUP) with the same record tables, append-only, filled incrementally every day (cron) and after
//     every freeze. Kept for the whole season: nothing in it can be updated or deleted. Each run checks that both copies match
//     (row counts per table, a SHA-256 over the full edit log, the freeze hashes) and logs the result in backup_runs.
//  2. An off-site bundle you download from the page (edits, snapshots, verifications, publications, and the reviews needed to
//     rebuild B3 and both snapshots). The page shows when you last downloaded one.
// D1's own point-in-time restore (Time Travel: 7 days on the free plan) also covers both databases.
import { iso, sha256hex } from "./freeze.js";

const TABLES = ["edits", "freezes", "verifications", "publications"];
const REVIEWS_PER_RUN = 8;          // keeps one run small (each review is ~220 KB); a backlog catches up over the next runs

async function editDigest(db) {
  const { results } = await db.prepare("SELECT seq, id, at, client_at, body FROM edits ORDER BY seq").all();
  return sha256hex(results.map((r) => `${r.seq}|${r.id}|${r.at}|${r.client_at ?? ""}|${r.body}`).join("\n"));
}
async function counts(db) {
  const out = {};
  for (const t of ["reviews", ...TABLES]) out[t] = (await db.prepare(`SELECT COUNT(*) AS n FROM ${t}`).first()).n;
  return out;
}

export async function runBackup(env, now) {
  if (!env.BACKUP) return { ok: false, error: "no BACKUP database bound" };
  const M = env.DB, K = env.BACKUP, copied = {};
  // append-only tables keyed by seq: copy rows newer than the backup's newest
  for (const [t, cols] of [["edits", "seq, season, id, at, client_at, body"], ["verifications", "seq, season, kind, checked_at, ok, body"],
                           ["publications", "seq, season, at, review_collected_at, edits_through_seq, lines, sha256"]]) {
    const top = (await K.prepare(`SELECT COALESCE(MAX(seq), 0) AS m FROM ${t}`).first()).m;
    const { results } = await M.prepare(`SELECT ${cols} FROM ${t} WHERE seq > ? ORDER BY seq`).bind(top).all();
    const names = cols.split(", "), q = `INSERT INTO ${t} (${cols}) VALUES (${names.map(() => "?").join(", ")})`;
    if (results.length) await K.batch(results.map((r) => K.prepare(q).bind(...names.map((n) => r[n]))));
    copied[t] = results.length;
  }
  // freezes (one per season and kind) and reviews (keyed by collection time): copy the ones the backup lacks
  const have = new Set((await K.prepare("SELECT season || '/' || kind AS k FROM freezes").all()).results.map((r) => r.k));
  const fz = (await M.prepare("SELECT season, kind, frozen_at, sha256, body FROM freezes").all()).results.filter((r) => !have.has(`${r.season}/${r.kind}`));
  if (fz.length) await K.batch(fz.map((r) => K.prepare("INSERT INTO freezes (season, kind, frozen_at, sha256, body) VALUES (?, ?, ?, ?, ?)").bind(r.season, r.kind, r.frozen_at, r.sha256, r.body)));
  copied.freezes = fz.length;
  const haveR = new Set((await K.prepare("SELECT season || '/' || collected_at AS k FROM reviews").all()).results.map((r) => r.k));
  const missing = (await M.prepare("SELECT season, collected_at FROM reviews ORDER BY collected_at").all()).results.filter((r) => !haveR.has(`${r.season}/${r.collected_at}`));
  for (const k of missing.slice(0, REVIEWS_PER_RUN)) {
    const r = await M.prepare("SELECT season, collected_at, generated_at, uploaded_at, body, body_sha256, core FROM reviews WHERE season = ? AND collected_at = ?").bind(k.season, k.collected_at).first();
    await K.prepare("INSERT INTO reviews (season, collected_at, generated_at, uploaded_at, body, body_sha256, core) VALUES (?, ?, ?, ?, ?, ?, ?)")
      .bind(r.season, r.collected_at, r.generated_at, r.uploaded_at, r.body, r.body_sha256, r.core).run();
  }
  copied.reviews = Math.min(missing.length, REVIEWS_PER_RUN); copied.reviews_still_behind = Math.max(0, missing.length - REVIEWS_PER_RUN);
  // check
  const cm = await counts(M), ck = await counts(K), dm = await editDigest(M), dk = await editDigest(K);
  const sh = async (db) => (await db.prepare("SELECT season || '/' || kind || '/' || sha256 AS s FROM freezes ORDER BY season, kind").all()).results.map((r) => r.s).join(",");
  const freezesMatch = (await sh(M)) === (await sh(K));
  const ok = dm === dk && freezesMatch && TABLES.every((t) => cm[t] === ck[t]) && (cm.reviews === ck.reviews || copied.reviews_still_behind > 0);
  await K.prepare("INSERT INTO backup_runs (at, ok, copied, counts, digest) VALUES (?, ?, ?, ?, ?)").bind(iso(now), ok ? 1 : 0, JSON.stringify(copied), JSON.stringify({ main: cm, backup: ck }), dk).run();
  return { ok, at: iso(now), copied, counts: { main: cm, backup: ck }, edit_digest_match: dm === dk, freezes_match: freezesMatch };
}

// The off-site bundle: every record row as stored (exact text, so snapshot hashes re-verify), plus the reviews a restore needs:
// the latest one (for the live B3) and the ones each snapshot was taken from. Other reviews are in the BACKUP database.
export async function bundle(env, season, now) {
  const M = env.DB, all = async (q, ...b) => (await M.prepare(q).bind(...b).all()).results;
  const edits = await all("SELECT seq, season, id, at, client_at, body FROM edits WHERE season = ? ORDER BY seq", season);
  const freezes = await all("SELECT season, kind, frozen_at, sha256, body FROM freezes WHERE season = ?", season);
  const verifications = await all("SELECT seq, season, kind, checked_at, ok, body FROM verifications WHERE season = ? ORDER BY seq", season);
  const publications = await all("SELECT seq, season, at, review_collected_at, edits_through_seq, lines, sha256 FROM publications WHERE season = ? ORDER BY seq", season);
  const index = await all("SELECT season, collected_at, generated_at, uploaded_at, body_sha256 FROM reviews WHERE season = ? ORDER BY collected_at", season);
  const need = new Set(freezes.map((f) => JSON.parse(f.body).review_file));
  if (index.length) need.add(index[index.length - 1].collected_at);
  for (const p of publications) need.add(p.review_collected_at);
  const reviews = [];
  for (const c of need) reviews.push(await M.prepare("SELECT season, collected_at, generated_at, uploaded_at, body, body_sha256, core FROM reviews WHERE season = ? AND collected_at = ?").bind(season, c).first());
  const out = { format: "jbp-review-backup", version: 1, made_at: iso(now), season, counts: { edits: edits.length, freezes: freezes.length, reviews_included: reviews.length, reviews_total: index.length },
    edit_digest: await sha256hex(edits.map((r) => `${r.seq}|${r.id}|${r.at}|${r.client_at ?? ""}|${r.body}`).join("\n")),
    edits, freezes, verifications, publications, review_index: index, reviews: reviews.filter(Boolean) };
  return JSON.stringify(out);
}
