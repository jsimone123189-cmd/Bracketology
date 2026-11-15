import { test, beforeEach } from "node:test";
import assert from "node:assert/strict";
import { authenticate, certsUrl, _resetCache } from "../src/auth.js";
import { makeIssuer, unsigned } from "./jwt.mjs";

const TEAM = "jaysbracketplays.cloudflareaccess.com", AUD = "aud-tag-123", OWNER = "owner@example.com";
const env = { ACCESS_TEAM_DOMAIN: TEAM, ACCESS_AUD: AUD, OWNER_EMAIL: OWNER, MACHINE_CLIENT_ID: "svc-123.access" };
const good = makeIssuer("k1"), other = makeIssuer("k1");          // same kid, different key: a forged signature
const fetcher = async (url) => { assert.equal(url, `https://${TEAM}/cdn-cgi/access/certs`); return new Response(JSON.stringify(good.jwks)); };
const now = Date.UTC(2027, 0, 10, 12), t = Math.floor(now / 1000);
const claims = (x = {}) => ({ aud: [AUD], iss: `https://${TEAM}`, email: OWNER, exp: t + 3600, iat: t, nbf: t - 5, ...x });
const req = (token) => new Request("https://review.jaysbracketplays.com/", { headers: token ? { "Cf-Access-Jwt-Assertion": token } : {} });
const auth = (token, e = env) => authenticate(req(token), e, fetcher, now);
beforeEach(() => _resetCache());

test("owner with a valid Access token gets in (email case-insensitive)", async () => {
  assert.deepEqual(await auth(good.sign(claims())), { kind: "owner", email: OWNER });
  assert.equal((await auth(good.sign(claims({ email: "Owner@Example.com" })))).kind, "owner");
});
test("fails closed when configuration is missing", async () => {
  for (const k of ["ACCESS_TEAM_DOMAIN", "ACCESS_AUD", "OWNER_EMAIL"]) assert.equal(await auth(good.sign(claims()), { ...env, [k]: "" }), null, k);
  assert.equal(await authenticate(req(good.sign(claims())), {}, fetcher, now), null);
});
test("rejects missing, malformed, unsigned and forged tokens", async () => {
  for (const tok of [null, "", "abc", "a.b", "a.b.c.d", unsigned(claims()), other.sign(claims()), good.sign(claims()).slice(0, -4) + "AAAA"]) assert.equal(await auth(tok), null, String(tok).slice(0, 20));
  assert.equal(await auth(good.sign(claims(), { alg: "HS256" })), null);
  assert.equal(await auth(good.sign(claims(), { kid: "unknown" })), null);
});
test("rejects wrong audience, issuer, expiry, not-yet-valid", async () => {
  assert.equal(await auth(good.sign(claims({ aud: ["someone-else"] }))), null);
  assert.equal(await auth(good.sign(claims({ iss: "https://evil.cloudflareaccess.com" }))), null);
  assert.equal(await auth(good.sign(claims({ exp: t - 1 }))), null);
  assert.equal(await auth(good.sign(claims({ exp: undefined }))), null);
  assert.equal(await auth(good.sign(claims({ nbf: t + 3600 }))), null);
});
test("anyone other than the owner is refused, even with a valid token", async () => {
  assert.equal(await auth(good.sign(claims({ email: "someone@example.com" }))), null);
  assert.equal(await auth(good.sign(claims({ email: undefined }))), null);
});
test("machine service token only when configured, and never with an email", async () => {
  const m = claims({ email: undefined, common_name: "svc-123.access" });
  assert.deepEqual(await auth(good.sign(m)), { kind: "machine", common_name: "svc-123.access" });
  assert.equal(await auth(good.sign(m), { ...env, MACHINE_CLIENT_ID: "" }), null);
  assert.equal(await auth(good.sign({ ...m, common_name: "other" })), null);
  assert.equal((await auth(good.sign({ ...m, email: OWNER }))).kind, "owner");
});
test("certificate source is pinned to an Access team domain", async () => {
  assert.equal(certsUrl("evil.example.com"), null);
  assert.equal(certsUrl("x.cloudflareaccess.com.evil.com"), null);
  assert.equal(await auth(good.sign(claims()), { ...env, ACCESS_TEAM_DOMAIN: "evil.example.com" }), null);
  const failing = async () => new Response("down", { status: 503 });
  assert.equal(await authenticate(req(good.sign(claims())), env, failing, now), null);     // certs unavailable -> closed
});
