# node-security-scan

Reusable workflow that runs three security scans **in parallel** against Node.js / React / Next.js repositories before build or test steps run. All three jobs must pass for the workflow to succeed.

> Replace `<current-sha>` with the current SHA from the [root README](../../README.md#current-sha).

## Jobs

| Job | Tool | What it checks |
|-----|------|----------------|
| `gitleaks` | gitleaks v8.24.3 | Secrets and credentials committed to git history |
| `npm-audit` | npm audit | Known CVEs in npm dependencies (via lockfile) |
| `guarddog` | guarddog | Supply-chain threats in npm packages (typosquatting, malicious install scripts, exfiltration) |

## Usage

### Minimal — run on every push and PR

```yaml
on: [push, pull_request]

jobs:
  security:
    uses: orangitfi/platform-tooling/.github/workflows/node-security-scan.yml@<current-sha>
```

### With custom options

```yaml
jobs:
  security:
    uses: orangitfi/platform-tooling/.github/workflows/node-security-scan.yml@<current-sha>
    with:
      working-directory: ./frontend
      audit-level: critical        # only fail on critical CVEs
      fail-on-findings: false      # warn but don't block — useful while onboarding
```

### Recommended position in a pipeline

```yaml
jobs:
  security:
    uses: orangitfi/platform-tooling/.github/workflows/node-security-scan.yml@<current-sha>

  build:
    needs: security
    uses: orangitfi/platform-tooling/.github/workflows/node-build.yml@<current-sha>

  test:
    needs: security
    uses: orangitfi/platform-tooling/.github/workflows/node-test.yml@<current-sha>
```

## Parameters

| Input | Default | Description |
|-------|---------|-------------|
| `working-directory` | `.` | Directory containing `package.json` and `package-lock.json` |
| `audit-level` | `high` | Minimum npm audit severity to fail on: `low`, `moderate`, `high`, `critical` |
| `fail-on-findings` | `true` | Fail the workflow if any scan detects issues |

## When it has value

- **Pre-merge gate**: catches leaked API keys, vulnerable dependencies, and supply-chain attacks before code reaches the main branch
- **Separation of concerns**: security scans run in their own dedicated jobs; a failure here blocks build/test/deploy without cluttering those jobs
- **Parallel execution**: all three scans run simultaneously — total wall-clock time is dominated by the slowest scan (~30–60 s), not the sum

## Tips

- `fetch-depth: 0` is set automatically in the gitleaks job. Without it, only the most recent commit would be scanned — older committed secrets would go undetected.
- If gitleaks flags a test fixture or placeholder value as a false positive, add an allowlist entry to `.gitleaks.toml` in the consuming repo. See the [gitleaks-scan action README](../actions/gitleaks-scan/README.md#handling-false-positives).
- Start with `fail-on-findings: false` when adding this to an existing repo to understand the baseline noise before hard-failing.
- `npm audit` operates against `package-lock.json` — no packages are installed. If `package-lock.json` is missing the audit step will fail with a clear error.
