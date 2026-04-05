# node-ci

Reusable workflow that wires together the full Node.js CI pipeline in a single call. The consuming repo controls **when** it runs; this workflow controls **how**.

> Replace `<current-sha>` with the current SHA from the [root README](../../README.md#current-sha).

## Pipeline shape

```
push / pull_request / workflow_dispatch
        │
        ▼
   ┌─────────┐
   │security │  gitleaks + npm-audit + guarddog (parallel)
   └────┬────┘
        │ (gates everything below)
        ├──────────────┬──────────────┬──────────────────┬─────────────────┐
        ▼              ▼              ▼                  ▼                 ▼
    ┌──────┐       ┌───────┐      ┌──────┐      ┌───────────────┐  ┌────────────┐
    │ lint │       │ build │      │ test │      │functional-e2e │  │visual-test │
    └──┬───┘       └───┬───┘      └──┬───┘      │  (optional)   │  │ (optional) │
       │               │             │           └───────┬───────┘  └──────┬─────┘
       └───────────────┴─────────────┴───────────────────┴──────────────────┘
                                     │ (all must pass or be skipped)
                                     ▼
                           ┌──────────────────┐
                           │vulnerability-scan│  Syft + Grype (code + Docker)
                           └──────────────────┘
```

`functional-e2e` and `visual-test` are opt-in. When disabled they are skipped and the vulnerability scan still runs.

## Usage

### Minimal — mirrors the defaults of the original consuming-repo workflow

```yaml
# .github/workflows/ci.yml  (in your consuming repo)
name: CI

on:
  push:
  pull_request:
  workflow_dispatch:

jobs:
  ci:
    uses: orangitfi/platform-tooling/.github/workflows/node-ci.yml@<current-sha>
    with:
      image-name: my-app
```

### Full example with all optional jobs enabled

```yaml
jobs:
  ci:
    uses: orangitfi/platform-tooling/.github/workflows/node-ci.yml@<current-sha>
    with:
      working-directory:        .
      audit-level:              high
      dockerfile-path:          Dockerfile
      lint-command:             lint
      build-command:            build
      test-command:             test:unit
      run-playwright:           true
      playwright-command:       test:e2e
      run-functional-e2e:       true
      functional-e2e-command:   test:e2e:functional
      run-visual-test:          true
      visual-test-command:      test:e2e:visual
      fail-on-severity:         high
      run-docker-scan:          true
      image-name:               my-app
```

### Repo without a Dockerfile

```yaml
jobs:
  ci:
    uses: orangitfi/platform-tooling/.github/workflows/node-ci.yml@<current-sha>
    with:
      image-name:       my-app
      run-docker-scan:  false
```

### Unit tests only, no Playwright

```yaml
jobs:
  ci:
    uses: orangitfi/platform-tooling/.github/workflows/node-ci.yml@<current-sha>
    with:
      image-name:      my-app
      run-playwright:  false
```

## Parameters

| Input | Default | Description |
|-------|---------|-------------|
| `working-directory` | `.` | Directory containing `package.json` |
| `audit-level` | `high` | Minimum npm audit severity to fail on: `low`, `moderate`, `high`, `critical` |
| `dockerfile-path` | `Dockerfile` | Path to the Dockerfile (used by lint and vulnerability scan) |
| `lint-command` | `lint` | npm script name for linting |
| `build-command` | `build` | npm script name for the build |
| `test-command` | `test:unit` | npm script name for unit tests |
| `run-playwright` | `true` | Run Playwright tests in the `test` job |
| `playwright-command` | `test:e2e` | npm script for Playwright in the `test` job |
| `run-functional-e2e` | `false` | Enable the `functional-e2e` job (opt-in) |
| `functional-e2e-command` | `test:e2e:functional` | npm script for functional e2e tests |
| `run-visual-test` | `false` | Enable the `visual-test` job (opt-in) |
| `visual-test-command` | `test:e2e:visual` | npm script for visual regression tests |
| `fail-on-severity` | `high` | Minimum Grype severity for vulnerability scan |
| `run-docker-scan` | `true` | Build and scan the Docker image in vulnerability scan |
| `image-name` | *(repo name)* | Docker image name for the vulnerability scan |

## Jobs reference

| Job | Calls | Condition |
|-----|-------|-----------|
| `security` | `node-security-scan` | always |
| `lint` | `node-lint` | always (after security) |
| `build` | `node-build` | always (after security) |
| `test` | `node-test` | always (after security) |
| `functional-e2e` | `node-test` | only when `run-functional-e2e: true` |
| `visual-test` | `node-test` | only when `run-visual-test: true` |
| `vulnerability-scan` | `node-vulnerability-scan` | after all above pass or are skipped |

## When it has value

- **Single line of CI**: the consuming repo needs one `uses:` line to get a fully opinionated, security-first CI pipeline. No copy-pasting individual job blocks.
- **Pipeline updates for free**: when platform-tooling improves a scan or adds a job, consuming repos get the change by bumping the SHA pin — no edits to their own workflow files.
- **Optional jobs are safe to skip**: `functional-e2e` and `visual-test` are off by default. They are only enabled in repos that have the corresponding npm scripts and environments set up.

## Tips

- For visual regression tests, baselines must first be generated on Linux/Chromium using the [`node-update-visual-snapshots`](node-update-visual-snapshots.md) workflow before `visual-test` will pass.
- The `functional-e2e` job is intended for tests that require a live backend. If your backend is a separate service, start it in a separate job and ensure it is reachable before this job runs — or keep `run-functional-e2e: false` and handle it in a post-deploy workflow instead.
- All five quality jobs (`lint`, `build`, `test`, `functional-e2e`, `visual-test`) run in parallel after `security` passes. Total wall-clock time is dominated by the slowest parallel job.
- Add this workflow as the sole required status check in your branch protection rules: one check name covers the entire pipeline.
