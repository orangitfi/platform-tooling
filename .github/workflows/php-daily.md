# php-daily

Reusable workflow for a daily security status run against a PHP / Symfony project. Combines the full CI pipeline with an OWASP ZAP DAST scan running in parallel — together they give a complete picture of the current security posture of both the codebase and the running application.

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

Both jobs run in **parallel**. `ci` checks the code and dependencies; `dast` checks the live deployed environment. A test or lint failure does not block the DAST scan — they are independent signals.

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
    uses: orangitfi/platform-tooling/.github/workflows/php-daily.yml@<current-sha>
    with:
      run-docker-scan: false
      # target-url not set → DAST job is skipped
```

### Full daily run — CI + DAST baseline scan

```yaml
jobs:
  daily:
    uses: orangitfi/platform-tooling/.github/workflows/php-daily.yml@<current-sha>
    with:
      image-name: my-app
      target-url: https://staging.myapp.com
```

### Symfony API with OpenAPI spec

```yaml
jobs:
  daily:
    uses: orangitfi/platform-tooling/.github/workflows/php-daily.yml@<current-sha>
    with:
      image-name:  my-app
      target-url:  https://staging.myapp.com
      scan-type:   api
      openapi-spec: https://staging.myapp.com/api/doc.json
```

### Use a repo variable for the staging URL

```yaml
jobs:
  daily:
    uses: orangitfi/platform-tooling/.github/workflows/php-daily.yml@<current-sha>
    with:
      image-name: my-app
      target-url: ${{ vars.STAGING_URL }}   # empty → DAST skipped, CI still runs
```

## Parameters

### CI parameters

| Input | Default | Description |
|-------|---------|-------------|
| `working-directory` | `.` | Directory containing `composer.json` |
| `run-phpcs` | `true` | Run PHP_CodeSniffer in the lint job |
| `phpcs-standard` | `PSR12` | Coding standard when no `phpcs.xml` is present |
| `run-phpstan` | `true` | Run PHPStan in the lint job |
| `phpstan-level` | `5` | Analysis level 1–9 when no `phpstan.neon` is present |
| `paths` | `src` | Space-separated paths both lint tools scan (when no config file is present) |
| `dockerfile-path` | `Dockerfile` | Path to the Dockerfile |
| `test-command` | `vendor/bin/phpunit` | Full command to run tests |
| `composer-args` | `""` | Extra arguments passed to `composer install` |
| `run-docker-scan` | `true` | Scan the Docker image in the vulnerability scan |
| `image-name` | *(repo name)* | Docker image name for the vulnerability scan |
| `fail-on-severity` | `high` | Minimum Grype severity for the vulnerability scan |

### DAST parameters

| Input | Default | Description |
|-------|---------|-------------|
| `target-url` | `""` | URL to scan. Empty = DAST job skipped |
| `scan-type` | `baseline` | `baseline` (passive), `full` (active), `api` (OpenAPI-aware) |
| `openapi-spec` | `""` | OpenAPI spec URL — used only for `api` scan type |
| `dast-fail-on-findings` | `true` | Fail the DAST job if ZAP finds alerts |

## What it covers

| Layer | Tool | What it checks |
|-------|------|----------------|
| Secrets in code | gitleaks | Committed credentials and tokens |
| PHP dependencies | composer audit | Known CVEs in `composer.lock` |
| Supply chain | guarddog | Malicious Packagist packages |
| Code style | PHP_CodeSniffer | PSR-12 violations and formatting |
| Static analysis | PHPStan | Type errors, undefined variables, dead code |
| Unit tests | PHPUnit | Regressions in logic |
| OS + container CVEs | Syft + Grype | Vulnerabilities in image layers |
| Live app behaviour | OWASP ZAP | Runtime security headers, cookies, API misconfigs |

## When it has value

- **Complete daily picture**: static analysis tells you about the code; DAST tells you about what's actually running. Both together mean you don't miss a class of vulnerability in either direction.
- **CVE early warning**: dependency and OS vulnerability databases are updated daily. Running nightly ensures new CVEs are caught within 24 hours even with no code changes.
- **Symfony APIs**: the `api` scan type is valuable for Symfony backend projects — ZAP uses the OpenAPI spec to exercise every declared endpoint, catching misconfigurations a passive scan would miss.

## Tips

- Use `${{ vars.STAGING_URL }}` (a repository variable) for `target-url`. When the variable is empty the DAST job is skipped automatically — no workflow changes needed for repos without a staging environment yet.
- Start with `dast-fail-on-findings: false` for the first week to understand the baseline noise before enabling hard failures.
- The ZAP report is uploaded as an artifact named `zap-daily-report` on every scan run.
- Pair with `slack-notify`: add it as a final job with `needs: [ci, dast]` and `if: always()` in the consuming repo's caller workflow to get a daily status message in your security channel.
