# node-daily

Reusable workflow for a daily security status run against a Node.js project. Combines the full CI pipeline with an OWASP ZAP DAST scan running in parallel — together they give a complete picture of the current security posture of both the codebase and the running application.

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
│ build  │         │ (or full │
│ test   │         │  or api) │
│vuln    │         │          │
│ scan   │         │ skipped  │
└────────┘         │ if no    │
                   │ target   │
                   └──────────┘
```

Both jobs run in **parallel**. `ci` checks the code and dependencies; `dast` checks the live deployed environment. A broken build does not block the DAST scan — they are independent signals.

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
    uses: orangitfi/platform-tooling/.github/workflows/node-daily.yml@<current-sha>
    with:
      image-name: my-app
      # target-url not set → DAST job is skipped
```

### Full daily run — CI + DAST baseline scan

```yaml
jobs:
  daily:
    uses: orangitfi/platform-tooling/.github/workflows/node-daily.yml@<current-sha>
    with:
      image-name: my-app
      target-url: https://staging.myapp.com
```

### Nightly full active ZAP scan (deeper, slower)

```yaml
jobs:
  daily:
    uses: orangitfi/platform-tooling/.github/workflows/node-daily.yml@<current-sha>
    with:
      image-name: my-app
      target-url: https://staging.myapp.com
      scan-type:  full
```

### API project with OpenAPI spec

```yaml
jobs:
  daily:
    uses: orangitfi/platform-tooling/.github/workflows/node-daily.yml@<current-sha>
    with:
      image-name:   my-api
      target-url:   https://staging.myapi.com
      scan-type:    api
      openapi-spec: https://staging.myapi.com/openapi.json
```

### Use a repo variable for the staging URL (safe when URL is not always set)

```yaml
jobs:
  daily:
    uses: orangitfi/platform-tooling/.github/workflows/node-daily.yml@<current-sha>
    with:
      image-name: my-app
      target-url: ${{ vars.STAGING_URL }}   # empty → DAST skipped, CI still runs
```

## Parameters

### CI parameters

| Input | Default | Description |
|-------|---------|-------------|
| `working-directory` | `.` | Directory containing `package.json` |
| `audit-level` | `high` | Minimum npm audit severity |
| `dockerfile-path` | `Dockerfile` | Path to the Dockerfile |
| `build-command` | `build` | npm build script |
| `test-command` | `test:unit` | npm unit test script |
| `run-playwright` | `true` | Run Playwright in the CI test job |
| `playwright-command` | `test:e2e` | npm Playwright script |
| `image-name` | *(repo name)* | Docker image name for vulnerability scan |
| `run-docker-scan` | `true` | Scan the Docker image in the vulnerability scan |
| `fail-on-severity` | `high` | Minimum Grype severity for vulnerability scan |

### DAST parameters

| Input | Default | Description |
|-------|---------|-------------|
| `target-url` | `""` | URL to scan. Empty = DAST job skipped |
| `scan-type` | `baseline` | `baseline` (passive), `full` (active), `api` (OpenAPI-aware) |
| `openapi-spec` | `{target-url}/openapi.json` | OpenAPI spec — used only for `api` scan type |
| `dast-fail-on-findings` | `true` | Fail the DAST job if ZAP finds alerts |

## What it covers

| Layer | Tool | What it checks |
|-------|------|----------------|
| Secrets in code | gitleaks | Committed credentials and tokens |
| npm dependencies | npm audit | Known CVEs in lockfile |
| Supply chain | guarddog | Malicious npm packages |
| Code style | ESLint / Prettier | Lint and format violations |
| TypeScript | npm build | Compile errors |
| Unit tests | npm test | Regressions in logic |
| e2e tests | Playwright | UI and integration regressions |
| OS + container CVEs | Syft + Grype | Vulnerabilities in image layers |
| Live app behaviour | OWASP ZAP | Runtime security headers, cookies, misconfigs |

## When it has value

- **Complete daily picture**: static analysis tells you about the code; DAST tells you about what's actually running. Both together mean you don't miss a class of vulnerability in either direction.
- **CVE early warning**: dependency and container vulnerability databases are updated daily. Running nightly ensures new CVEs are caught within 24 hours even with no code changes.
- **Regression detection**: a nightly CI run catches broken tests or lint failures introduced by dependency updates (Dependabot / Renovate) even when no developer pushed code.
- **Compliance evidence**: the combination of a full vulnerability scan and a DAST scan provides the evidence trail that most security frameworks (SOC 2, ISO 27001) require for continuous monitoring.

## Tips

- Use `${{ vars.STAGING_URL }}` (a repository variable, not a secret) for the target URL. When the variable is empty the DAST job is skipped automatically — no workflow changes needed for repos that don't have a staging environment yet.
- Start with `scan-type: baseline` and `dast-fail-on-findings: false` for the first week to understand the noise profile before enabling hard failures.
- For the `full` active scan, ensure `target-url` points to a **staging** environment — the active scan sends real attack payloads that can pollute data or trigger rate limiting in production.
- The ZAP report is uploaded as an artifact named `zap-daily-report` on every scan run regardless of pass/fail. Download the HTML report for a human-readable findings list.
- Pair this with a Slack notification: add `slack-notify` as a final job with `needs: [ci, dast]` and `if: always()` in the consuming repo's caller workflow to get a daily status message.
