// Local-only harness: a fake Access certificate server on 127.0.0.1, a throwaway D1 copy, and `wrangler dev --local`.
import { spawn, execFileSync } from "node:child_process";
import { createServer } from "node:http";
import { mkdtempSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { makeIssuer } from "./jwt.mjs";

const DIR = path.resolve(new URL("..", import.meta.url).pathname);
export const OWNER = "owner@example.com", AUD = "local-test-aud", MACHINE = "svc-local.access", FINAL = "2027-03-14T21:45:00Z";

export async function start({ port = 8790, finalDeadline = FINAL, chunk = null, persist: reuse = null } = {}) {
  const issuer = makeIssuer("k1");
  const certs = createServer((q, s) => { s.writeHead(q.url === "/cdn-cgi/access/certs" ? 200 : 404, { "Content-Type": "application/json" }); s.end(JSON.stringify(issuer.jwks)); });
  await new Promise((r) => certs.listen(0, "127.0.0.1", r));
  const team = `127.0.0.1:${certs.address().port}`;
  const persist = reuse || mkdtempSync(path.join(tmpdir(), "jbp-review-"));
  writeFileSync(path.join(DIR, ".dev.vars"), [
    `ACCESS_TEAM_DOMAIN=${team}`, `ACCESS_AUD=${AUD}`, `OWNER_EMAIL=${OWNER}`, `MACHINE_CLIENT_ID=${MACHINE}`,
    `ALLOW_TEST_OVERRIDES=local-test-only`, ...(finalDeadline ? [`TEST_FINAL_DEADLINE=${finalDeadline}`] : []), ...(chunk ? [`TEST_CHUNK=${chunk}`] : [])].join("\n") + "\n");
  const env = { ...process.env, CI: "1", WRANGLER_SEND_METRICS: "false", NO_UPDATE_NOTIFIER: "1" };
  if (!reuse) for (const db of ["jbp_private", "jbp_backup"]) execFileSync("npx", ["wrangler", "d1", "migrations", "apply", db, "--local", "--persist-to", persist], { cwd: DIR, env, stdio: "pipe" });
  const proc = spawn("npx", ["wrangler", "dev", "--local", "--persist-to", persist, "--port", String(port), "--ip", "127.0.0.1", "--show-interactive-dev-session=false", "--test-scheduled"], { cwd: DIR, env, stdio: ["ignore", "pipe", "pipe"], detached: true });
  let log = ""; proc.stdout.on("data", (d) => (log += d)); proc.stderr.on("data", (d) => (log += d));
  const base = `http://127.0.0.1:${port}`;
  for (let i = 0; i < 120; i++) {
    try { const r = await fetch(base + "/"); if (r.status) break; } catch {}
    await new Promise((r) => setTimeout(r, 500));
    if (i === 119) throw new Error("wrangler dev didn't start:\n" + log);
  }
  const t = () => Math.floor(Date.now() / 1000);
  const ownerToken = (email = OWNER) => issuer.sign({ aud: [AUD], iss: `http://${team}`, email, exp: t() + 3600, iat: t() });
  const machineToken = () => issuer.sign({ aud: [AUD], iss: `http://${team}`, common_name: MACHINE, exp: t() + 3600, iat: t() });
  async function stop() {
    try { process.kill(-proc.pid, "SIGTERM"); } catch {}
    await new Promise((r) => setTimeout(r, 1500)); try { process.kill(-proc.pid, "SIGKILL"); } catch {}
    certs.close(); rmSync(path.join(DIR, ".dev.vars"), { force: true });
  }
  return { base, persist, ownerToken, machineToken, stop, log: () => log, issuer, team };
}

export function sql(persist, command, db = "jbp_private") {
  // Returns {ok, out}: runs against the local D1 copy only.
  try { return { ok: true, out: execFileSync("npx", ["wrangler", "d1", "execute", db, "--local", "--persist-to", persist, "--command", command], { cwd: DIR, env: { ...process.env, CI: "1", WRANGLER_SEND_METRICS: "false" }, stdio: "pipe" }).toString() }; }
  catch (e) { return { ok: false, out: String(e.stdout) + String(e.stderr) }; }
}

export function wr(args) {
  // Run a wrangler command locally (tests only).
  return execFileSync("npx", ["wrangler", ...args], { cwd: DIR, env: { ...process.env, CI: "1", WRANGLER_SEND_METRICS: "false" }, stdio: "pipe" }).toString();
}
