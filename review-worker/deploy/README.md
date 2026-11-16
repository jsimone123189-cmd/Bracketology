# Deployment drafts (inactive)

These files are **not** in `.github/workflows`, so GitHub never runs them. Each one is moved into place only after the owner
approves its stage (docs/45). Nothing here holds a secret; secrets are referenced by name only.

| File | Stage | What it does once activated |
|---|---|---|
| `review-deploy.yml` (moved to `.github/workflows/`, active) | 1 | Applies the D1 migrations and deploys `jbp-review` to `review.jaysbracketplays.com`, setting its four settings as Worker secrets |
| `review-upload-once.yml` | 2 | Builds one review in Actions and uploads it, so the page has data for acceptance testing |
| `daily-update.stage3.md` | 3 | The exact steps to add to `daily-update.yml` (upload the review; fetch the published lines) |
| `trigger.stage4.js` | 4 | The timer's Selection Sunday logic: build, research freeze after noon, verify, then poll the finals and freeze/publish the final |
