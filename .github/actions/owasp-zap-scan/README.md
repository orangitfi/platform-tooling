# OWASP ZAP Scan

Composite action that runs an [OWASP ZAP](https://www.zaproxy.org/) dynamic application security test (DAST) against a live URL. ZAP is pulled directly from the official Docker image at a pinned digest — no marketplace actions are used.

If `target-url` is left empty the scan is **skipped cleanly** with a notice. This makes it safe to wire into any pipeline even when no live URL is available (e.g. on feature branches without a preview environment).

## Usage

> Replace `<current-sha>` with the current SHA from the [root README](../../../README.md#current-sha).

### Nightly baseline scan

```yaml
jobs:
  dast:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4

      - uses: orangitfi/platform-tooling/.github/actions/owasp-zap-scan@<current-sha>
        with:
          target-url: https://staging.myapp.com
```

### Skip gracefully when URL is not set

```yaml
      - uses: orangitfi/platform-tooling/.github/actions/owasp-zap-scan@<current-sha>
        with:
          target-url: ${{ vars.STAGING_URL }}   # empty string → scan skipped, job passes
```

### Active full scan against staging

```yaml
      - uses: orangitfi/platform-tooling/.github/actions/owasp-zap-scan@<current-sha>
        with:
          target-url:       https://staging.myapp.com
          scan-type:        full
          fail-on-findings: "true"
          artifact-name:    zap-full-report
```

### API scan (FastAPI / OpenAPI)

```yaml
      - uses: orangitfi/platform-tooling/.github/actions/owasp-zap-scan@<current-sha>
        with:
          target-url:   https://staging.myapp.com
          scan-type:    api
          openapi-spec: https://staging.myapp.com/openapi.json
```

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `target-url` | No | `""` | URL of the running application to scan. Empty = skip |
| `scan-type` | No | `baseline` | `baseline` (passive), `full` (active), or `api` (OpenAPI-aware) |
| `openapi-spec` | No | `{target-url}/openapi.json` | URL or file path of OpenAPI spec — used only for `api` scan type |
| `fail-on-findings` | No | `true` | Fail the step if ZAP reports any alerts |
| `artifact-name` | No | `zap-report` | Name of the uploaded HTML + JSON report artifact |

## Scan types

| Type | What it does | Typical duration | When to use |
|------|-------------|-----------------|-------------|
| `baseline` | Passive scan — spiders the app, inspects responses, no attack traffic | ~2 min | Nightly against staging, PRs with preview URLs |
| `full` | Active scan — sends crafted attack payloads (XSS, SQLi probes, etc.) | 10–30 min | Scheduled nightly, pre-release |
| `api` | OpenAPI-spec-aware passive scan — tests every declared endpoint | ~3 min | REST APIs with Swagger/FastAPI auto-docs |

## What ZAP finds

The baseline and full scans cover:

- Missing or misconfigured HTTP security headers (`Strict-Transport-Security`, `X-Frame-Options`, `Content-Security-Policy`, `X-Content-Type-Options`)
- Insecure cookie flags (`HttpOnly`, `Secure`, `SameSite`)
- Information disclosure (stack traces, server version banners, verbose error pages)
- Open redirects and CORS misconfigurations
- *Full scan additionally*: basic XSS, SQL injection, path traversal, command injection probes

## When it has value

DAST fills the gap that static analysis cannot cover. No amount of code scanning can tell you whether your deployed app actually sends `Strict-Transport-Security` headers — only a live HTTP scan can.

Concrete scenarios:
- You changed a Nginx config or middleware — did you accidentally drop a security header?
- You added a new cookie — is it flagged `HttpOnly`?
- Your third-party auth SDK changed — does it now set `SameSite=None` without `Secure`?
- You want evidence for a compliance audit that you actively test the running application

## Tips

- The report artifact (`zap-report.html` and `zap-report.json`) is uploaded on every scan regardless of pass/fail. Open the HTML report in a browser for a readable findings list with links to the ZAP wiki for each alert type.
- Start with `scan-type: baseline` and `fail-on-findings: false` for your first few runs to understand the baseline noise level before enabling hard failures.
- ZAP alert IDs are stable — you can suppress specific false-positive alert types by providing a custom rules file via `-z "-config rules.csv=/zap/wrk/rules.csv"`. Mount the file and pass the `-z` option if you need this level of control.
- For `api` scan type, FastAPI auto-generates an OpenAPI spec at `/openapi.json` and `/docs`. Point `openapi-spec` at the spec URL and ZAP will test every declared endpoint systematically.

## Docker image pinning

Pinned to `ghcr.io/zaproxy/zaproxy@sha256:c4da4c234258d444d9988fce9d034b00323724818daa4c91ca46f09aa04b46db` (stable, 2025-01).

To update: pull `ghcr.io/zaproxy/zaproxy:stable`, run `docker inspect --format='{{index .RepoDigests 0}}' ghcr.io/zaproxy/zaproxy:stable`, and replace both digest references in `action.yml`.
