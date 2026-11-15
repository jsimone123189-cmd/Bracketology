// Test-only Access look-alike: an RSA key, its JWKS, and signed tokens. Never used outside tests.
import { generateKeyPairSync, createSign } from "node:crypto";
const b64u = (b) => Buffer.from(b).toString("base64url");
export function makeIssuer(kid = "k1") {
  const { publicKey, privateKey } = generateKeyPairSync("rsa", { modulusLength: 2048 });
  const jwk = publicKey.export({ format: "jwk" });
  return {
    kid, jwks: { keys: [{ ...jwk, kid, alg: "RS256", use: "sig" }] },
    sign(claims, header = {}) {
      const h = b64u(JSON.stringify({ alg: "RS256", kid, typ: "JWT", ...header })), p = b64u(JSON.stringify(claims));
      const s = createSign("RSA-SHA256").update(`${h}.${p}`).sign(privateKey);
      return `${h}.${p}.${b64u(s)}`;
    },
  };
}
export const unsigned = (claims) => `${b64u(JSON.stringify({ alg: "none", kid: "k1" }))}.${b64u(JSON.stringify(claims))}.`;
