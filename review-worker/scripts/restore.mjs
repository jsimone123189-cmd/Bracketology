#!/usr/bin/env node
// Rebuild the private review database from a backup (docs/45). Writes a .sql file to run against a NEW, EMPTY D1 database:
//   node scripts/restore.mjs --from-bundle 2027_review_backup_2027-03-01.json --out restore.sql
//   node scripts/restore.mjs --from-db jbp_backup --remote --out restore.sql          (reads the backup database through wrangler)
//   then: npx wrangler d1 execute <new database> --remote --file restore.sql
// D1 limits one SQL statement to 100 KB, and reviews/snapshots are larger, so each long text is inserted empty and then appended
// in pieces before the append-only triggers are created (they are added last). Stored text is restored byte for byte, so
// snapshot hashes still verify. The file contains your private ledger: keep it off GitHub and delete it after use.
import { readFileSync, writeFileSync } from "node:fs";
import { execFileSync } from "node:child_process";
import path from "node:path";

const DIR = path.resolve(new URL("..", import.meta.url).pathname);
const arg = (k) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : null; };
const flag = (k) => process.argv.includes(k);
const PIECE = 20000;            // characters per appended piece: at most 80 KB even if every character took 4 bytes

const COLS = {
  reviews: ["season", "collected_at", "generated_at", "uploaded_at", "body", "body_sha256", "core"],
  edits: ["seq", "season", "id", "at", "client_at", "body"],
  freezes: ["season", "kind", "frozen_at", "sha256", "body"],
  verifications: ["seq", "season", "kind", "checked_at", "ok", "body"],
  publications: ["seq", "season", "at", "review_collected_at", "edits_through_seq", "lines", "sha256"],
};
const KEY = { reviews: ["season", "collected_at"], edits: ["seq"], freezes: ["season", "kind"], verifications: ["seq"], publications: ["seq"] };

function lit(v) { return v === null || v === undefined ? "NULL" : typeof v === "number" ? String(v) : `'${String(v).replace(/'/g, "''")}'`; }

export function restoreSql(tables) {
  const schema = readFileSync(path.join(DIR, "migrations/0001_init.sql"), "utf8");
  const stmts = schema.split(/;\s*\n/).map((s) => s.trim()).filter(Boolean).map((s) => s.replace(/^(--[^\n]*\n)+/, "").trim()).filter(Boolean);
  const triggers = stmts.filter((s) => /^CREATE TRIGGER/i.test(s)), rest = stmts.filter((s) => !/^CREATE TRIGGER/i.test(s));
  const out = [...rest.map((s) => s + ";")];
  for (const [t, rows] of Object.entries(tables)) {
    for (const r of rows) {
      const long = COLS[t].filter((c) => typeof r[c] === "string" && r[c].length > PIECE);
      out.push(`INSERT INTO ${t} (${COLS[t].join(", ")}) VALUES (${COLS[t].map((c) => (long.includes(c) ? "''" : lit(r[c]))).join(", ")});`);
      const where = KEY[t].map((k) => `${k} = ${lit(r[k])}`).join(" AND ");
      for (const c of long) for (let i = 0; i < r[c].length; i += PIECE) out.push(`UPDATE ${t} SET ${c} = ${c} || ${lit(r[c].slice(i, i + PIECE))} WHERE ${where};`);
    }
  }
  out.push(...triggers.map((s) => s + ";"));
  // record the migration as applied, so later migrations run normally
  out.push("CREATE TABLE IF NOT EXISTS d1_migrations (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE, applied_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP);");
  out.push("INSERT INTO d1_migrations (name) VALUES ('0001_init.sql');");
  const big = out.find((x) => Buffer.byteLength(x, "utf8") >= 100000);
  if (big) throw new Error(`a statement is ${Buffer.byteLength(big, "utf8")} bytes, over D1's 100 KB limit`);
  return out.join("\n") + "\n";
}

function fromDb(name, where) {
  const q = (sql) => JSON.parse(execFileSync("npx", ["wrangler", "d1", "execute", name, where, ...(arg("--persist-to") ? ["--persist-to", arg("--persist-to")] : []), "--json", "--command", sql],
    { cwd: DIR, env: { ...process.env, CI: "1", WRANGLER_SEND_METRICS: "false" }, maxBuffer: 1 << 30 }).toString())[0].results;
  return Object.fromEntries(Object.keys(COLS).map((t) => [t, q(`SELECT ${COLS[t].join(", ")} FROM ${t}`)]));
}

if (import.meta.url === `file://${process.argv[1]}`) {
  const out = arg("--out") || "restore.sql";
  let tables;
  if (arg("--from-bundle")) {
    const b = JSON.parse(readFileSync(arg("--from-bundle"), "utf8"));
    if (b.format !== "jbp-review-backup") throw new Error("not a review backup bundle");
    tables = { reviews: b.reviews, edits: b.edits, freezes: b.freezes, verifications: b.verifications, publications: b.publications };
  } else if (arg("--from-db")) tables = fromDb(arg("--from-db"), flag("--remote") ? "--remote" : "--local");
  else { console.error("usage: --from-bundle FILE | --from-db NAME [--remote|--local] [--persist-to DIR] --out FILE"); process.exit(2); }
  writeFileSync(out, restoreSql(tables));
  console.log(`wrote ${out}: ${Object.entries(tables).map(([t, r]) => `${r.length} ${t}`).join(", ")}`);
}
