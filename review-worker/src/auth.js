// Cloudflare Access JWT validation (https://developers.cloudflare.com/cloudflare-one/identity/authorization-cookie/validating-json/).
// Access sits in front of the Worker; this is the second, independent check, so a misrouted request, a disabled Access
// policy or a forged header still fails. Every failure returns null (fail closed): no configuration, no token, bad signature,
// wrong audience/issuer, expired, or an identity that isn't the owner (or the configured machine service token).

const enc = new TextEncoder();
const b64url = (s) => Uint8Array.from(atob(s.replace(/-/g, "+").replace(/_/g, "/") + "===".slice((s.length + 3) % 4)), (c) => c.charCodeAt(0));
const json = (s) => JSON.parse(new TextDecoder().decode(b64url(s)));

let cache = { url: null, at: 0, keys: null };
const CERT_TTL_MS = 10 * 60 * 1000;

export function certsUrl(team) {
  // Production: https://<team>.cloudflareaccess.com. Plain http is allowed only for a 127.0.0.1 test server.
  if (/^127\.0\.0\.1:\d+$/.test(team)) return `http://${team}/cdn-cgi/access/certs`;
  if (!/^[a-z0-9-]+\.cloudflareaccess\.com$/.test(team)) return null;
  return `https://${team}/cdn-cgi/access/certs`;
}
export const issuerOf = (team) => (/^127\.0\.0\.1:\d+$/.test(team) ? `http://${team}` : `https://${team}`);

async function keys(team, fetcher) {
  const url = certsUrl(team);
  if (!url) return null;
  if (cache.url === url && Date.now() - cache.at < CERT_TTL_MS && cache.keys) return cache.keys;
  const r = await fetcher(url);
  if (!r.ok) return null;
  const body = await r.json();
  const out = {};
  for (const k of body.keys || []) {
    if (k.kty !== "RSA" || !k.kid) continue;
    out[k.kid] = await crypto.subtle.importKey("jwk", { kty: "RSA", n: k.n, e: k.e, alg: "RS256", ext: true }, { name: "RSASSA-PKCS1-v1_5", hash: "SHA-256" }, false, ["verify"]);
  }
  cache = { url, at: Date.now(), keys: out };
  return out;
}
export const _resetCache = () => { cache = { url: null, at: 0, keys: null }; };

// Returns {kind: "owner"|"machine", email?, common_name?} or null.
export async function authenticate(request, env, fetcher = fetch, now = Date.now()) {
  try {
    const team = (env.ACCESS_TEAM_DOMAIN || "").trim(), aud = (env.ACCESS_AUD || "").trim(), owner = (env.OWNER_EMAIL || "").trim().toLowerCase();
    if (!team || !aud || !owner) return null;                       // not configured -> nobody gets in
    const token = request.headers.get("Cf-Access-Jwt-Assertion");
    if (!token) return null;
    const parts = token.split(".");
    if (parts.length !== 3) return null;
    const header = json(parts[0]), claims = json(parts[1]);
    if (header.alg !== "RS256" || !header.kid) return null;
    const ks = await keys(team, fetcher);
    const key = ks && ks[header.kid];
    if (!key) return null;
    const ok = await crypto.subtle.verify("RSASSA-PKCS1-v1_5", key, b64url(parts[2]), enc.encode(parts[0] + "." + parts[1]));
    if (!ok) return null;
    const auds = Array.isArray(claims.aud) ? claims.aud : [claims.aud];
    if (!auds.includes(aud)) return null;
    if (claims.iss !== issuerOf(team)) return null;
    const t = Math.floor(now / 1000);
    if (typeof claims.exp !== "number" || claims.exp < t) return null;
    if (typeof claims.nbf === "number" && claims.nbf > t + 60) return null;
    if (claims.email && String(claims.email).toLowerCase() === owner) return { kind: "owner", email: owner };
    const machine = (env.MACHINE_CLIENT_ID || "").trim();
    if (machine && !claims.email && claims.common_name === machine) return { kind: "machine", common_name: machine };
    return null;
  } catch {
    return null;
  }
}
