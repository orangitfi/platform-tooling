# python-daily

Reusable workflow for a daily security status run against a Python / uv project. Combines the full CI pipeline with an OWASP ZAP DAST scan running in parallel — together they give a complete picture of the current security posture of both the codebase and the running application.

> Replace `<current-sha>` with the current SHA from the [root README](../../README.md#current-sha).

## Pipeline shape

```
schedule (03:00 UTC) / workflow_dispatch
              │
    ┌─────────┴──────────┐
    ▼                    ▼
┌────────┐         ┌──────────┐
│   ci   │         │   dast   │
│        │         │          │
│security│         │ OWASP ZAP│
│ lint   │         │ baseline │
│ test   │         │ (or full │
│vuln    │         │  or api) │
│ scan   │         │          │
└────────┘         │ skipped  │
                   │ if no    │
                   │ target   │
                   └──────────┘
```

Both jobs run in **parallel**. `ci` checks the code and dependencies; `dast` checks the live deployed environment. A failing test or lint error does not block the DAST scan — they are independent signals.

The `dast` job is **skipped cleanly** when `target-url` is empty.

## Usage

### Minimal nightly run — code checks only, no live URL yet

```yaml
# .github/workflows/daily.yml  (in your consuming repo)
name: Daily Security

on:
  schedule:
    - cron: "0 3 * * *"   # 03:00 UTC every night
  workflow_dispatch:

jobs:
  daily:
    uses: orangitfi/platform-tooling/.github/workflows/python-daily.yml@<current-sha>
    with:
      image-name: my-api
      # target-url not set → DAST job is skipped
```

### Full daily run — CI + DAST baseline scan

```yaml
jobs:
  daily:
    uses: orangitfi/platform-tooling/.github/workflows/python-daily.yml@<current-sha>
    with:
      image-name: my-api
      target-url: https://staging.myapi.com
```

### FastAPI service with auto-generated OpenAPI spec

```yaml
jobs:
  daily:
    uses: orangitfi/platform-tooling/.github/workflows/python-daily.yml@<current-sha>
    with:
      image-name:   my-api
      target-url:   https://staging.myapi.com
      scan-type:    api
      # FastAPI auto-generates the spec at /openapi.json — no openapi-spec input needed
```

### Nightly full active ZAP scan against staging

```yaml
jobs:
  daily:
    uses: orangitfi/platform-tooling/.github/workflows/python-daily.yml@<current-sha>
    with:
      image-name: my-api
      target-url: https://staging.myapi.com
      scan-type:  full
```

### Use a repo variable for the staging URL (safe when URL is not always set)

```yaml
jobs:
  daily:
    uses: orangitfi/platform-tooling/.github/workflows/python-daily.yml@<current-sha>
    with:
      image-name: my-api
      target-url: ${{ vars.STAGING_URL }}   # empty → DAST skipped, CI still runs
```

### With test extras and Dockerfile validation

```yaml
jobs:
  daily:
    uses: orangitfi/platform-tooling/.github/workflows/python-daily.yml@<current-sha>
    with:
      image-name:       my-api
      uv-sync-args:     "--extra test"
      run-docker-build: true
      target-url:       https://staging.myapi.com
```

## Parameters

### CI parameters

| Input | Default | Description |
|-------|---------|-------------|
| `working-directory` | `.` | Directory containing `pyproject.toml` and `uv.lock` |
| `test-command` | `pytest` | Command passed to `uv run` for tests |
| `uv-sync-args` | `""` | Extra arguments for `uv sync` (e.g. `--extra test`) |
| `run-ruff-lint` | `true` | Run `ruff check` in the lint job |
| `run-ruff-format` | `true` | Run `ruff format --check` in the lint job |
| `dockerfile-path` | `Dockerfile` | Path to the Dockerfile |
| `run-docker-build` | `false` | Validate the Dockerfile builds as an early quality gate |
| `image-name` | *(repo name)* | Docker image name for docker-build and vulnerability scan |
| `run-docker-scan` | `true` | Scan the Docker image in the vulnerability scan |
| `fail-on-severity` | `high` | Minimum Grype severity for vulnerability scan |

### DAST parameters

| Input | Default | Description |
|-------|---------|-------------|
| `target-url` | `""` | URL to scan. Empty = DAST job skipped |
| `scan-type` | `baseline` | `baseline` (passive), `full` (active), `api` (OpenAPI-aware) |
| `openapi-spec` | `{target-url}/openapi.json` | OpenAPI spec — used only for `api` scan type. FastAPI provides this at `/openapi.json` automatically. |
| `dast-fail-on-findings` | `true` | Fail the DAST job if ZAP finds alerts |

## What it covers

| Layer | Tool | What it checks |
|-------|------|----------------|
| Secrets in code | gitleaks | Committed credentials and tokens |
| Python dependencies | pip-audit | Known CVEs in uv lockfile |
| Supply chain | guarddog | Malicious PyPI packages |
| Code style | ruff check | Lint rule violations |
| Formatting | ruff format | Formatting drift |
| Unit tests | pytest | Regressions in logic |
| OS + container CVEs | Syft + Grype | Vulnerabilities in image layers |
| Live app behaviour | OWASP ZAP | Runtime security headers, cookies, API misconfigs |

## When it has value

- **Complete daily picture**: static analysis tells you about the code; DAST tells you about what's actually running. Both together mean you don't miss a class of vulnerability in either direction.
- **FastAPI / Django REST**: the `api` scan type is particularly valuable for Python backends — ZAP uses the OpenAPI spec to exercise every declared endpoint, catching misconfigurations that a passive scan might miss.
- **CVE early warning**: dependency and OS vulnerability databases are updated daily. Running nightly ensures new CVEs are caught within 24 hours even with no code changes.
- **Lockfile drift detection**: `uv sync --frozen` fails immediately if `pyproject.toml` was changed without running `uv lock`. A nightly run catches this before the next developer picks up the branch.

## Tips

- Use `${{ vars.STAGING_URL }}` (a repository variable) for `target-url`. When the variable is empty the DAST job is skipped automatically — no workflow changes needed for repos that don't have a staging environment yet.
- For FastAPI projects, `scan-type: api` with no `openapi-spec` input will default to `{target-url}/openapi.json` — FastAPI serves this automatically. This gives a more thorough scan than `baseline` in roughly the same time (~3 min).
- Start with `dast-fail-on-findings: false` for the first week to understand the baseline noise profile before enabling hard failures.
- The ZAP report is uploaded as an artifact named `zap-daily-report` on every scan run. Download the HTML report for a human-readable findings list with remediation links.
- Pair with `slack-notify`: add it as a final job with `needs: [ci, dast]` and `if: always()` in the consuming repo's caller workflow to get a daily status message in your security channel.
