// Starts the daily-update GitHub workflow on time. GitHub's own schedule runs hours late, so it is only the backup.
// Needs secret DISPATCH_TOKEN: a fine-grained GitHub token for this repo only, with Actions read and write.
const URL = "https://api.github.com/repos/jsimone123189-cmd/Bracketology/actions/workflows/daily-update.yml/dispatches";

export default {
  async scheduled(controller, env) {
    const r = await fetch(URL, {
      method: "POST",
      headers: { Authorization: `Bearer ${env.DISPATCH_TOKEN}`, Accept: "application/vnd.github+json", "X-GitHub-Api-Version": "2022-11-28", "User-Agent": "jays-bracket-plays-trigger" },
      body: JSON.stringify({ ref: "master" }),
    });
    if (r.status !== 204) throw new Error(`GitHub dispatch failed for ${controller.cron}: ${r.status} ${await r.text()}`);
  },
};
