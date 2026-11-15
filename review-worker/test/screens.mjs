// Phone screenshots of the review page against the local Worker (no deployment). Output: private/screens/*.png (gitignored).
// Uses the Chrome that puppeteer downloaded earlier, driven over the DevTools protocol.
import { spawn } from "node:child_process";
import { writeFileSync, readdirSync, mkdtempSync } from "node:fs";
import { tmpdir, homedir } from "node:os";
import path from "node:path";
import { start } from "./devserver.mjs";
import { python, realReview, REPO } from "./helpers.mjs";

const OUT = path.join(REPO, "private/screens");
const chromeDir = path.join(homedir(), ".cache/puppeteer/chrome"), ver = readdirSync(chromeDir)[0];
const CHROME = path.join(chromeDir, ver, "chrome-linux64/chrome");
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const S = await start({ port: 8795, finalDeadline: null });
try {
  const rv = realReview(); rv.model_files = JSON.parse(python("-c", null, ["import json; from bracketology import review; print(json.dumps(review.model_files()))"]));
  const M = (p, body) => fetch(S.base + p, { method: "POST", headers: { "Cf-Access-Jwt-Assertion": S.machineToken(), "Content-Type": "application/json" }, body: JSON.stringify(body) });
  const O = (body) => fetch(S.base + "/api/edits", { method: "POST", headers: { "Cf-Access-Jwt-Assertion": S.ownerToken(), "Content-Type": "application/json", "X-Review": "1" }, body: JSON.stringify(body) });
  console.log("upload", (await M("/api/machine/review", rv)).status);
  const f = rv.model_order, out = rv.rest_order.filter((k) => !f.includes(k));
  const pick = (name, i) => f.find((k) => k === name) || f[i];
  const duke = pick("duke", 24), hero = f[14];
  for (const e of [{ op: "move", team: f[33], to_line: 7, reason_code: "committee_precedent", confidence: 2, explanation: "Q1 road wins look better than the metrics say" },
                   { op: "add", team: out[0], reason_code: "head_to_head", confidence: 1 }]) console.log("edit", (await O(e)).status);

  const prof = mkdtempSync(path.join(tmpdir(), "chrome-"));
  const chrome = spawn(CHROME, ["--headless=new", "--no-sandbox", "--disable-gpu", "--hide-scrollbars", `--user-data-dir=${prof}`, "--remote-debugging-port=9333", "about:blank"], { stdio: "ignore" });
  let tabs; for (let i = 0; i < 40; i++) { try { tabs = await (await fetch("http://127.0.0.1:9333/json")).json(); if (tabs.length) break; } catch {} await sleep(250); }
  const ws = new WebSocket(tabs.find((t) => t.type === "page").webSocketDebuggerUrl); await new Promise((r) => (ws.onopen = r));
  let id = 0; const pend = new Map(); ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.id && pend.has(d.id)) { pend.get(d.id)(d); pend.delete(d.id); } };
  const cdp = (method, params = {}) => new Promise((r) => { const i = ++id; pend.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
  const js = async (expr) => (await cdp("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true })).result?.result?.value;
  const shot = async (name, full = false) => {
    const r = await cdp("Page.captureScreenshot", { format: "png", captureBeyondViewport: full });
    writeFileSync(path.join(OUT, name + ".png"), Buffer.from(r.result.data, "base64")); console.log("shot", name);
  };
  await cdp("Network.enable");
  await cdp("Network.setExtraHTTPHeaders", { headers: { "Cf-Access-Jwt-Assertion": S.ownerToken() } });
  await cdp("Emulation.setDeviceMetricsOverride", { width: 390, height: 844, deviceScaleFactor: 2, mobile: true });
  await cdp("Emulation.setTouchEmulationEnabled", { enabled: true });
  for (const theme of ["light", "dark"]) {
    await cdp("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: theme }] });
    await cdp("Page.navigate", { url: S.base + "/" }); await sleep(1800);
    await shot(`1-board-${theme}`);
    if (theme === "dark") break;
    await js(`window.scrollTo(0, 1500)`); await sleep(200); await shot("2-board-scrolled-edited");
    await js(`document.querySelector('[data-team="${duke}"]').click()`); await sleep(400); await shot("3-team-sheet");
    await js(`document.querySelector('[data-line="2"]').click()`); await sleep(150);
    await js(`document.querySelector('[data-reason="metric_disagreement"]').click()`); await sleep(150);
    await js(`document.getElementById("why").value="Top-25 metrics everywhere but NET"; document.getElementById("why").dispatchEvent(new Event("input",{bubbles:true}))`);
    await js(`document.getElementById("sheet").scrollTop=430`); await sleep(200); await shot("4-edit-form");
    await js(`document.getElementById("preview").click()`); await sleep(900);
    await js(`document.getElementById("save").scrollIntoView({block:"end"})`); await sleep(200); await shot("5-preview-before-save");
    await js(`document.getElementById("save").click()`); await sleep(1200); await shot("6-saved-toast");
    await js(`window.scrollTo(0,0)`); await sleep(200); await shot("6b-publish-bar");
    await js(`document.querySelector('[data-tab="log"]').click()`); await sleep(400); await shot("7-history");
    await js(`document.querySelector('[data-tab="brackets"]').click()`); await sleep(400); await shot("8-three-brackets");
    await js(`document.querySelector('[data-tab="snaps"]').click()`); await sleep(400); await shot("9-snapshots", true);
  }
  // a stranger: same page, no identity
  await cdp("Network.setExtraHTTPHeaders", { headers: {} });
  await cdp("Emulation.setEmulatedMedia", { features: [{ name: "prefers-color-scheme", value: "light" }] });
  await cdp("Page.navigate", { url: S.base + "/" }); await sleep(800); await shot("10-not-signed-in");
  // what an incomplete final looks like (second local server with a test deadline and a fake clock)
  await S.stop();
  const S2 = await start({ port: 8796 }); S.stop = S2.stop;
  const rv2 = structuredClone(rv); rv2.inputs = { ...rv2.inputs, collected_at: "2027-03-14T21:20:00Z", conference_games_pending: [{ conf: "big-ten", game: "Purdue vs Michigan" }] }; rv2.generated_at = "2027-03-14T21:20:30Z";
  await fetch(S2.base + "/api/machine/review", { method: "POST", headers: { "Cf-Access-Jwt-Assertion": S2.machineToken(), "Content-Type": "application/json", "X-Test-Now": "2027-03-14T21:21:00Z" }, body: JSON.stringify(rv2) });
  await fetch(S2.base + "/api/freeze", { method: "POST", headers: { "Cf-Access-Jwt-Assertion": S2.ownerToken(), "Content-Type": "application/json", "X-Review": "1", "X-Test-Now": "2027-03-14T21:36:00Z" }, body: JSON.stringify({ kind: "final" }) });
  await cdp("Network.setExtraHTTPHeaders", { headers: { "Cf-Access-Jwt-Assertion": S2.ownerToken(), "X-Test-Now": "2027-03-14T21:37:00Z" } });
  await cdp("Page.navigate", { url: S2.base + "/" }); await sleep(1800); await shot("11-incomplete-final-warning");
  await js(`document.querySelector('[data-tab="snaps"]').click()`); await sleep(400); await shot("12-incomplete-final-snapshots", true);
  ws.close(); chrome.kill("SIGKILL");
} finally { await S.stop(); }
