# dast-scan

Reusable workflow that runs an [OWASP ZAP](https://www.zaproxy.org/) dynamic application security test (DAST) against a live URL. Designed for nightly scheduled runs but can be triggered post-deploy or on-demand.

**If `target-url` is empty the job is skipped cleanly** — safe to wire into any pipeline even when no preview environment is available on the current branch.

ZAP is pulled from the official Docker image at a pinned digest. No marketplace actions are used.

> Replace `<current-sha>` with the current SHA from the [root README](../../README.md#current-sha).

## Usage

### Nightly baseline scan against staging

```yaml
on:
  schedule:
    - cron: "0 3 * * *"   # 03:00 UTC every night

jobs:
  dast:
    uses: orangitfi/platform-tooling/.github/workflows/dast-scan.yml@<current-sha>
    with:
      target-url: https://staging.myapp.com
```

### Skip when no staging URL is configured (safe default)

```yaml
jobs:
  dast:
    uses: orangitfi/platform-tooling/.github/workflows/dast-scan.yml@<current-sha>
    with:
      target-url: ${{ vars.STAGING_URL }}   # empty → entire job skipped with a notice
```

### Nightly full active scan

```yaml
jobs:
  dast:
    uses: orangitfi/platform-tooling/.github/workflows/dast-scan.yml@<current-sha>
    with:
      target-url:       https://staging.myapp.com
      scan-type:        full
      fail-on-findings: true
      artifact-name:    zap-nightly-full
```

### API scan (FastAPI / Express with OpenAPI spec)

```yaml
jobs:
  dast:
    uses: orangitfi/platform-tooling/.github/workflows/dast-scan.yml@<current-sha>
    with:
      target-url:   https://staging.myapp.com
      scan-type:    api
      openapi-spec: https://staging.myapp.com/openapi.json
```

## Parameters

| Input | Default | Description |
|-------|---------|-------------|
| `target-url` | `""` | URL of the running application. Empty = job skipped |
| `scan-type` | `baseline` | `baseline` (passive, ~2 min), `full` (active, 10–30 min), `api` (OpenAPI-aware) |
| `openapi-spec` | `{target-url}/openapi.json` | OpenAPI spec URL or file path — used only for `api` scan type |
| `fail-on-findings` | `true` | Fail the workflow if ZAP reports any alerts |
| `artifact-name` | `zap-report` | Name of the uploaded HTML + JSON report artifact |

## Scan types explained

| Type | Attack traffic? | Duration | Best for |
|------|-----------------|----------|----------|
| `baseline` | No (passive only) | ~2 min | Nightly header/cookie/config checks |
| `full` | Yes (XSS, SQLi probes, etc.) | 10–30 min | Deep nightly security testing |
| `api` | No (passive, spec-guided) | ~3 min | REST APIs with Swagger/FastAPI docs |

## What it finds

- Missing HTTP security headers (`Strict-Transport-Security`, `X-Frame-Options`, `Content-Security-Policy`, `X-Content-Type-Options`, `Referrer-Policy`)
- Insecure cookie attributes (`HttpOnly`, `Secure`, `SameSite` missing)
- Information disclosure (server version headers, stack traces in error responses, verbose 404 pages)
- Open redirects, CORS misconfigurations
- *Full scan additionally:* basic XSS, SQL injection, path traversal, and command injection probes

## When it has value

DAST is the only tool in this stack that tests the *running application*. Static analysis, dependency scanning, and container scanning all operate on source or binary artefacts — none of them can tell you that your deployed app forgot to set `Strict-Transport-Security`.

Concrete value scenarios:
- A middleware or reverse-proxy configuration change silently dropped a security header
- A new cookie was added without `HttpOnly` or `Secure` flags
- A third-party auth library update changed a `SameSite` policy
- You need evidence for a security audit or compliance review that the live application is actively tested

## Tips

- The HTML report is always uploaded as an artifact even when the scan fails — download it for a human-readable findings list with descriptions and remediation links for each alert type.
- Run `baseline` scan first and set `fail-on-findings: false` for a few nights to understand the noise profile of your app before switching to hard failures.
- ZAP exit code `1` means warnings found, exit code `2` means fail-level findings. The workflow treats any non-zero exit as findings and applies `fail-on-findings`.
- For the `full` scan, ensure the target is a **staging** environment — the active scan sends real attack payloads which can pollute data or trigger rate limits in production.
- FastAPI auto-generates an OpenAPI spec at `/openapi.json` with no extra configuration. Point `openapi-spec` there and the `api` scan will exercise every declared endpoint.
