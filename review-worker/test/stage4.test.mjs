// The stage-4 timer draft, run against a fake review Worker and a fake GitHub over a simulated Selection Sunday.
import { test } from "node:test";
import assert from "node:assert/strict";
import timer from "../deploy/trigger.stage4.js";

function simulate({ finalsDoneAt }) {
  const log = [], frozen = {}; let researchCalls = 0;
  globalThis.fetch = async () => { log.push(["dispatch", now]); return new Response(null, { status: 204 }); };
  let now = "";
  const env = { DISPATCH_TOKEN: "x", REVIEW: {
    async freeze(season, kind) {
      if (frozen[kind]) return { status: "already_frozen" };
      if (kind === "research") { researchCalls++; if (researchCalls === 1) return { status: "in_progress" }; frozen.research = now; log.push(["freeze research", now]); return { status: "frozen" }; }
      if (now >= finalsDoneAt || now >= "21:35") { frozen.final = now; log.push(["freeze final", now]); return { status: "frozen", final_results_complete: now >= finalsDoneAt }; }
      return { status: "waiting" };
    },
    async verify(season, kind) { log.push([`verify ${kind}`, now]); return { ok: true }; },
  } };
  return { log, frozen, run: async () => {
    for (let m = 15 * 60; m < 23 * 60; m += 5) {
      now = `${String(Math.floor(m / 60)).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
      await timer.scheduled({ cron: "*/5 15-22 14 3 *", scheduledTime: Date.UTC(2027, 2, 14, Math.floor(m / 60), m % 60) }, env);
    }
  } };
}

test("Selection Sunday timer: build 11:00, research freeze 11:30, verify, final as soon as the finals end, then publish", async () => {
  const s = simulate({ finalsDoneAt: "21:20" }); await s.run();
  const at = (what) => s.log.filter((x) => x[0] === what).map((x) => x[1]);
  assert.deepEqual(at("freeze research"), ["15:30"]);                  // first call was "in progress"; the same run repeats until frozen
  assert.deepEqual(at("verify research"), ["16:05", "16:30"]);
  assert.deepEqual(at("freeze final"), ["21:20"]);
  assert.deepEqual(at("verify final"), ["21:20"]);
  const d = at("dispatch"); assert.equal(d[0], "15:00"); assert.ok(d.includes("21:20"), "site republished with the final"); assert.ok(d.filter((x) => x >= "19:00" && x < "21:20").length >= 10, "fresh reviews every 10 min while waiting");
  assert.ok(!d.some((x) => x > "21:20"), "nothing after the final");
});

test("finals run late: the final is frozen (incomplete) only in the last minutes, and the site is republished", async () => {
  const s = simulate({ finalsDoneAt: "99:99" }); await s.run();
  const fin = s.log.filter((x) => x[0] === "freeze final").map((x) => x[1]);
  assert.deepEqual(fin, ["21:35"]);
});

test("ordinary days: the daily cron only dispatches the daily update", async () => {
  const log = []; globalThis.fetch = async () => { log.push(1); return new Response(null, { status: 204 }); };
  await timer.scheduled({ cron: "17 10 * 11-12,1-4 *", scheduledTime: Date.UTC(2027, 0, 5, 10, 17) }, { DISPATCH_TOKEN: "x", REVIEW: { freeze() { throw new Error("must not be called"); } } });
  assert.equal(log.length, 1);
});
