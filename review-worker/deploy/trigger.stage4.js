// STAGE 4 draft (inactive): replaces trigger/worker.js after approval. Adds a service binding REVIEW -> jbp-review (ReviewOps)
// and replaces the Selection Sunday cron line with "1-56/5 15-22 14 3 *" (minutes :01, :06, ...; cron count unchanged).
// Daily cron: unchanged (dispatch daily-update). Selection Sunday, every 5 minutes from 11:01 a.m. to 6:56 p.m. EDT:
//   15:01 and 15:41 UTC    dispatch daily-update (builds and uploads pre-noon reviews; the freeze uses the newest collected by noon)
//   16:01 UTC (12:01 ET)   research freeze (owner decision): strict noon cutoff for collected data and logged edits; retried
//                          every 5 min until frozen; the Worker refuses it before 12:01
//   16:11 and 16:31 UTC    verify research
//   from 19:01 UTC         every 10 min: dispatch daily-update (fresh review with the latest finals) until the final is frozen;
//                          every 5 min: freeze("final") -> "waiting" until every conference final is in, or until the last
//                          10 minutes before the deadline (then frozen INCOMPLETE and labelled)
//   once final is frozen   dispatch daily-update once more (site shows the final), then verify final
const DISPATCH = "https://api.github.com/repos/jsimone123189-cmd/Bracketology/actions/workflows/daily-update.yml/dispatches";
async function dispatch(env, why) {
  const r = await fetch(DISPATCH, { method: "POST", headers: { Authorization: `Bearer ${env.DISPATCH_TOKEN}`, Accept: "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "jays-bracket-plays-trigger" }, body: JSON.stringify({ ref: "master" }) });
  if (r.status !== 204) throw new Error(`GitHub dispatch failed (${why}): ${r.status}`);
}
async function freezeAll(env, season, kind) {
  for (let i = 0; i < 20; i++) { const r = await env.REVIEW.freeze(season, kind); if (r.status !== "in_progress") return r; }
  return { status: "in_progress" };
}
export default {
  async scheduled(controller, env) {
    if (controller.cron !== "1-56/5 15-22 14 3 *") return dispatch(env, "daily");
    const t = new Date(controller.scheduledTime), m = t.getUTCHours() * 60 + t.getUTCMinutes(), season = 2027;
    if (m === 15 * 60 + 1 || m === 15 * 60 + 41) return dispatch(env, "pre-noon review");
    if (m >= 16 * 60 + 1 && m < 17 * 60) { await freezeAll(env, season, "research"); if (m === 16 * 60 + 11 || m === 16 * 60 + 31) await env.REVIEW.verify(season, "research"); return; }
    if (m >= 19 * 60) {
      const before = await env.REVIEW.freeze(season, "final");          // "already_frozen" once done
      if (before.status === "already_frozen") return;
      const r = before.status === "in_progress" ? await freezeAll(env, season, "final") : before;
      if (r.status === "frozen") { await env.REVIEW.verify(season, "final"); return dispatch(env, "publish final"); }
      if (m % 10 === 1) return dispatch(env, "fresh review for the finals");
    }
  },
};
