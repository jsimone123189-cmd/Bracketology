// Season settings. Must match the Python side (review.freeze_deadline, FINAL_DEADLINE_ET, fieldformat); test/parity.test.mjs checks.
// final_deadline stays null until the 2027 selection-show time and the Matrix's final collection time are confirmed (docs/43):
// while null, the final freeze refuses and edits stay open.
export const SEASONS = {
  2027: {
    selection_sunday: "2027-03-14",
    research_cutoff: "2027-03-14T16:00:00Z",      // noon America/New_York (EDT begins that morning)
    final_deadline: null,                          // e.g. "2027-03-14T21:45:00Z" once confirmed
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
