import { execFileSync } from "node:child_process";
import { readdirSync, readFileSync, existsSync } from "node:fs";
import path from "node:path";
export const REPO = path.resolve(new URL("../..", import.meta.url).pathname);
export const PY = path.join(REPO, ".venv/bin/python");
export function python(script, input, args = []) {
  return execFileSync(PY, [script, ...args], { cwd: REPO, input: input == null ? undefined : JSON.stringify(input), env: { ...process.env, PYTHONPATH: path.join(REPO, "src") }, maxBuffer: 1 << 28 }).toString();
}
// The newest real 2027 review built locally (private/, never committed). Tests that need it skip if it isn't there.
export function realReview() {
  const d = path.join(REPO, "private/review");
  if (!existsSync(d)) return null;
  const f = readdirSync(d).filter((x) => /^2027_\d{8}T\d{6}Z\.json$/.test(x)).sort().pop();
  return f ? JSON.parse(readFileSync(path.join(d, f), "utf8")) : null;
}
// Small deterministic PRNG so failures reproduce.
export function rng(seed) { let s = seed >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 2 ** 32); }
