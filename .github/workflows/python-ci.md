# python-ci

Reusable workflow that wires together the full Python / uv CI pipeline in a single call. The consuming repo controls **when** it runs; this workflow controls **how**.

> Replace `<current-sha>` with the current SHA from the [root README](../../README.md#current-sha).

## Pipeline shape

```
push / pull_request / workflow_dispatch
        │
        ▼
   ┌──────────┐
   │ security │  gitleaks + pip-audit + guarddog (parallel)
   └─────┬────┘
         │ (gates everything below)
         ├──────────────┬──────────────────────────┐
         ▼              ▼                          ▼
     ┌──────┐       ┌──────┐             ┌──────────────┐
     │ lint │       │ test │             │ docker-build │
     └──┬───┘       └──┬───┘             │  (optional)  │
        │              │                 └──────┬───────┘
        └──────────────┴─────────────────────────┘
                        │ (all must pass or be skipped)
                        ▼
              ┌──────────────────┐
              │vulnerability-scan│  Syft + Grype (code + Docker)
              └──────────────────┘
```

`docker-build` is opt-in. When disabled it is skipped and the vulnerability scan still runs.

## Usage

### Minimal — pure Python service, no Dockerfile

```yaml
# .github/workflows/ci.yml  (in your consuming repo)
name: CI

on:
  push:
  pull_request:
  workflow_dispatch:

jobs:
  ci:
    uses: orangitfi/platform-tooling/.github/workflows/python-ci.yml@<current-sha>
    with:
      run-docker-scan: false
```

### Python service with a Dockerfile

```yaml
jobs:
  ci:
    uses: orangitfi/platform-tooling/.github/workflows/python-ci.yml@<current-sha>
    with:
      image-name:       my-api
      run-docker-build: true
```

### Full example with all options explicit

```yaml
jobs:
  ci:
    uses: orangitfi/platform-tooling/.github/workflows/python-ci.yml@<current-sha>
    with:
      working-directory:  .
      test-command:       pytest tests/ -v --tb=short
      uv-sync-args:       --extra test
      run-ruff-lint:      true
      run-ruff-format:    true
      dockerfile-path:    Dockerfile
      run-docker-build:   true
      image-name:         my-api
      fail-on-severity:   high
      run-docker-scan:    true
```

### Tests in a separate extras group, strict format check

```yaml
jobs:
  ci:
    uses: orangitfi/platform-tooling/.github/workflows/python-ci.yml@<current-sha>
    with:
      uv-sync-args:  "--extra test --extra dev"
      test-command:  "pytest tests/ -x --tb=short"
```

## Parameters

| Input | Default | Description |
|-------|---------|-------------|
| `working-directory` | `.` | Directory containing `pyproject.toml` and `uv.lock` |
| `test-command` | `pytest` | Command passed to `uv run` for tests |
| `uv-sync-args` | `""` | Extra arguments for `uv sync` (e.g. `--extra test`) |
| `run-ruff-lint` | `true` | Run `ruff check` in the lint job |
| `run-ruff-format` | `true` | Run `ruff format --check` in the lint job |
| `dockerfile-path` | `Dockerfile` | Path to the Dockerfile (used by lint, docker-build, and vulnerability scan) |
| `run-docker-build` | `false` | Validate the Dockerfile builds as an early quality gate (opt-in) |
| `image-name` | *(repo name)* | Docker image name for docker-build and vulnerability scan |
| `fail-on-severity` | `high` | Minimum Grype severity for the vulnerability scan |
| `run-docker-scan` | `true` | Build and scan the Docker image in the vulnerability scan |

## Jobs reference

| Job | Calls | Condition |
|-----|-------|-----------|
| `security` | `python-security-scan` | always |
| `lint` | `python-lint` | always (after security) |
| `test` | `python-test` | always (after security) |
| `docker-build` | `python-build-and-publish-docker` (`publish: false`) | only when `run-docker-build: true` |
| `vulnerability-scan` | `python-vulnerability-scan` | after all above pass or are skipped |

## Differences from node-ci

| | node-ci | python-ci |
|---|---|---|
| Build step | `npm run build` (always) | no transpile step — `uv sync` happens inside `test` |
| Optional parallel jobs | `functional-e2e`, `visual-test` | `docker-build` |
| Playwright | configurable | not applicable |
| Linter | npm lint script | ruff (check + format), both toggleable |
| Dependency install | `npm ci` | `uv sync --frozen` |

## When it has value

- **Single line of CI**: the consuming repo needs one `uses:` line to get security scanning, linting, testing, and vulnerability scanning — in the right order, with the right gates.
- **No Dockerfile?** Set `run-docker-scan: false` and `run-docker-build: false` — the pipeline still runs all the Python-specific quality checks.
- **Lockfile enforced**: `uv sync --frozen` fails immediately if `uv.lock` is out of sync with `pyproject.toml`, catching drift before tests run.
- **Scan before install**: security and guarddog/pip-audit scans run against the lockfile before `uv sync` installs anything. A compromised package is blocked before it executes.

## Tips

- The `docker-build` job calls `python-build-and-publish-docker` with `publish: false` — it just validates the Dockerfile compiles. No credentials or 1Password access needed. Enable it on repos where a broken Dockerfile would be a surprise.
- The `uv-sync-args` input is the right place to install optional dependency groups: `--extra test`, `--extra dev`, or `--group test` if using uv's dependency groups.
- ruff is installed ephemerally via `uvx` in the lint job — it does not need to be in `pyproject.toml`. The lint job will work on a fresh project that hasn't added ruff yet.
- Add this workflow as the sole required status check in branch protection rules: one check covers the entire pipeline.
- For nightly DAST scanning of the deployed service, pair this workflow with [`dast-scan`](dast-scan.md) in a separate scheduled workflow.
