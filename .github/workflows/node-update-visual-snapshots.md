# node-update-visual-snapshots

Reusable workflow for regenerating Playwright visual baseline screenshots. Designed to be triggered manually (`workflow_dispatch`) from the consuming repo whenever the UI changes intentionally and the baselines need refreshing.

Runs on `ubuntu-latest` — the same OS as CI visual-test jobs — so the committed `*-chromium-linux.png` files always match what CI compares against. After generating new screenshots the workflow commits them back to the branch with `[skip ci]` to avoid a CI loop.

> Replace `<current-sha>` with the current SHA from the [root README](../../README.md#current-sha).

## Usage

Add this file to the consuming repo (the entire workflow — it is intentionally short):

```yaml
# .github/workflows/update-visual-snapshots.yml  (in your consuming repo)
name: Update Visual Snapshots

on:
  workflow_dispatch:
    inputs:
      branch:
        description: 'Branch to update snapshots on (leave blank for current branch)'
        required: false
        default: ''

jobs:
  update-snapshots:
    uses: orangitfi/platform-tooling/.github/workflows/node-update-visual-snapshots.yml@<current-sha>
    with:
      branch: ${{ github.event.inputs.branch }}
    permissions:
      contents: write
```

That's it. All defaults match a standard Vite + Playwright setup. Override only what differs.

### Monorepo with frontend in a subdirectory

```yaml
jobs:
  update-snapshots:
    uses: orangitfi/platform-tooling/.github/workflows/node-update-visual-snapshots.yml@<current-sha>
    with:
      working-directory: ./frontend
      snapshot-path: frontend/e2e/visual/__snapshots__/
    permissions:
      contents: write
```

### Custom npm scripts

```yaml
jobs:
  update-snapshots:
    uses: orangitfi/platform-tooling/.github/workflows/node-update-visual-snapshots.yml@<current-sha>
    with:
      build-command:             build:preview
      update-snapshots-command:  e2e:update
    permissions:
      contents: write
```

## Parameters

| Input | Default | Description |
|-------|---------|-------------|
| `branch` | (triggering ref) | Branch to check out and push updated snapshots to |
| `node-version` | `20` | Node.js version |
| `working-directory` | `.` | Directory containing `package.json` |
| `build-command` | `build` | npm script that builds the frontend |
| `update-snapshots-command` | `test:e2e:update-snapshots` | npm script that runs Playwright with `--update-snapshots` |
| `snapshot-path` | `e2e/visual/__snapshots__/` | Repo-relative path containing generated snapshot files |
| `vite-api-base-url` | `http://localhost:3001` | Value for `VITE_API_BASE_URL` baked into the Vite bundle |
| `playwright-base-url` | `http://localhost:4173` | Base URL Playwright navigates to (must match the preview server port) |

## Typical lifecycle

1. **First-time setup**: run this workflow manually on the main branch to generate initial baselines
2. **After an intentional UI change**: run it on your feature branch _after_ the change is committed but before merging — the new screenshots will be committed to the branch automatically
3. **CI comparison**: the CI visual-test job uses `--snapshot-path` pointing at the committed files and diffs the live render against them

## When it has value

- Ensures baselines are always generated on Linux/Chromium — the same environment as CI. Snapshots generated on macOS or Windows have pixel-level differences that cause CI false failures.
- The `[skip ci]` commit message prevents the snapshot commit from triggering another CI run, which would otherwise cause an infinite loop.
- Uploading the snapshots as an artifact lets you inspect the generated images in the GitHub Actions UI _before_ they are committed, useful for reviewing the baseline visually.

## Tips

- The `PLAYWRIGHT_WEB_SERVER: true` environment variable tells `playwright.config.ts` to start `vite preview` automatically before tests. Ensure your Playwright config honours this variable.
- `VITE_API_BASE_URL` is baked into the Vite bundle at build time. All API calls in the Playwright tests should be intercepted by `page.route()` so the actual host does not matter — it only needs to be a syntactically valid URL.
- If `git diff --staged --quiet` is true after `git add`, the workflow exits with a success message and no commit. This is correct — it means the existing baselines already match the current render.
- Run this workflow on a feature branch before raising a PR. The reviewer can then see the new snapshots alongside the code change as part of the PR diff.
