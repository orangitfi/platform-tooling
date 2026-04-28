# php-security-scan

Reusable workflow that runs three security scans **in parallel** against PHP / Symfony repositories before build or test steps run. All three jobs must pass for the workflow to succeed.

> Replace `<current-sha>` with the current SHA from the [root README](../../README.md#current-sha).

## Jobs

| Job | Tool | What it checks |
|-----|------|----------------|
| `gitleaks` | gitleaks v8.24.3 | Secrets and credentials committed to git history |
| `composer-audit` | composer audit (built-in, Composer ≥ 2.8) | Known CVEs in PHP dependencies (via composer.lock) |
| `guarddog-php` | guarddog ⚠️ experimental | Supply-chain threats in Packagist packages (typosquatting, exfiltration, malicious code) |

## Usage

### Minimal — run on every push and PR

```yaml
on: [push, pull_request]

jobs:
  security:
    uses: orangitfi/platform-tooling/.github/workflows/php-security-scan.yml@<current-sha>
```

### With custom options

```yaml
jobs:
  security:
    uses: orangitfi/platform-tooling/.github/workflows/php-security-scan.yml@<current-sha>
    with:
      working-directory: ./app
      fail-on-findings: false    # warn but don't block while onboarding
```

### Recommended position in a pipeline

```yaml
jobs:
  security:
    uses: orangitfi/platform-tooling/.github/workflows/php-security-scan.yml@<current-sha>

  test:
    needs: security
    uses: orangitfi/platform-tooling/.github/workflows/php-ci.yml@<current-sha>
```

## Parameters

| Input | Default | Description |
|-------|---------|-------------|
| `working-directory` | `.` | Directory containing `composer.json` and `composer.lock` |
| `fail-on-findings` | `true` | Fail the workflow if any scan detects issues |
| `ignore-severity` | `""` | Space-separated severity levels to ignore in composer audit: `low`, `medium`, `high`, `critical`. Inverted compared to npm's `audit-level` — you list what to ignore rather than the minimum to fail on. Example: `"low medium"` fails only on high/critical. |

## What it does

- **gitleaks**: checks full git history (`fetch-depth: 0`) for leaked API keys, tokens, passwords, and other secrets
- **composer-audit**: reads the committed `composer.lock` and queries the GitHub Security Advisory database and Packagist security advisories feed for known CVEs — no packages are installed
- **guarddog-php**: checks each package in `composer.json` against heuristic rules for supply-chain attack indicators — no packages are installed

All three jobs run on separate runners and produce output in the GitHub Actions job summary.

## ⚠️ Note on guarddog Packagist support

The `guarddog-php` job uses guarddog's `packagist` subcommand, which exists but has received less real-world testing than the `npm` and `pypi` equivalents. False positives or unexpected failures are possible. It is strongly recommended to run the workflow with `fail-on-findings: false` initially and manually inspect guarddog output before enabling hard failures. See the [guarddog-php-scan action README](../actions/guarddog-php-scan/README.md) for details.

## When it has value

- **Pre-install gate**: both `composer-audit` and `guarddog-php` run before any `composer install`. A malicious or vulnerable package is caught before it ever executes on your runner.
- **Complementary coverage**: `composer-audit` finds CVE-tracked vulnerabilities (entries in the GitHub Advisory database); guarddog finds behavioural threats that have no CVE entry yet (obfuscated code, suspicious registry metadata, typosquatted names). Together they cover both vectors.
- **Parallel execution**: all three scans run simultaneously — total wall-clock time is the slowest scan (~30–60 s), not the sum.

## Tips

- `composer.lock` must be committed. `composer audit` operates against the lockfile and will fail with a clear error if it is missing. Generate it with `composer install` or `composer update`.
- If gitleaks flags a test fixture as a false positive, add an allowlist entry to `.gitleaks.toml` in the consuming repo. See the [gitleaks-scan action README](../actions/gitleaks-scan/README.md#handling-false-positives).
- To suppress a specific `composer-audit` advisory, add it to the `config.audit.ignored` list in `composer.json`. See the [composer-audit action README](../actions/composer-audit/README.md#notes).
- To tighten or loosen the vulnerability threshold, use `ignore-severity` (e.g. `"low medium"` to fail only on high/critical). Note the inverted logic compared to npm's `audit-level` — Composer requires you to specify which severities to suppress rather than a minimum failing level.
- Start with `fail-on-findings: false` when adding to an existing repository to understand the current baseline before enabling hard failures.
