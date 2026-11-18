// Season settings. Must match the Python side (review.freeze_deadline, FINAL_DEADLINE_ET, fieldformat); test/parity.test.mjs checks.
// final_deadline: 5:45 p.m. ET on Selection Sunday (owner, 2026-11-17), 15 minutes before the 6 p.m. selection show, when the Matrix's
// final collection closes. Re-check if CBS announces a different 2027 show time. While null, the final freeze refuses.
export const SEASONS = {
  2027: {
    selection_sunday: "2027-03-14",
    research_cutoff: "2027-03-14T16:00:00Z",      // noon America/New_York (EDT begins that morning)
    final_deadline: "2027-03-14T21:45:00Z",        // 5:45 p.m. EDT (owner, 2026-11-17); must equal FINAL_DEADLINE_ET in review.py
    lines: [4, 4, 4, 4, 4, 4, 4, 4, 4, 4, 6, 8, 4, 4, 6, 8],   // 76-team format
  },
};

export function season(env, y) {
  const s = SEASONS[y];
  if (!s) return null;
  // Tests (and only a local .dev.vars) may override the final deadline; production sets it here, in reviewed code.
  // The override only works when Access points at a 127.0.0.1 test server, which can never authenticate a real request.
  const local = env && /^127\.0\.0\.1:\d+$/.test(env.ACCESS_TEAM_DOMAIN || "");
  const fd = local && env.TEST_FINAL_DEADLINE && env.ALLOW_TEST_OVERRIDES === "local-test-only" ? env.TEST_FINAL_DEADLINE : s.final_deadline;
  return { ...s, final_deadline: fd };
}
