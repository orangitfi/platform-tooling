# python-security-scan

Reusable workflow that runs three security scans **in parallel** against Python / uv repositories before build or test steps run. All three jobs must pass for the workflow to succeed.

> Replace `<current-sha>` with the current SHA from the [root README](../../README.md#current-sha).

## Jobs

| Job | Tool | What it checks |
|-----|------|----------------|
| `gitleaks` | gitleaks v8.24.3 | Secrets and credentials committed to git history |
| `pip-audit` | pip-audit (via uv tool run) | Known CVEs in Python dependencies (via uv lockfile) |
| `guarddog` | guarddog | Supply-chain threats in PyPI packages (typosquatting, exfiltration, malicious install hooks) |

## Usage

### Minimal — run on every push and PR

```yaml
on: [push, pull_request]

jobs:
  security:
    uses: orangitfi/platform-tooling/.github/workflows/python-security-scan.yml@<current-sha>
```

### With custom options

```yaml
jobs:
  security:
    uses: orangitfi/platform-tooling/.github/workflows/python-security-scan.yml@<current-sha>
    with:
      working-directory: ./backend
      fail-on-findings: false    # warn but don't block while onboarding
```

### Recommended position in a pipeline

```yaml
jobs:
  security:
    uses: orangitfi/platform-tooling/.github/workflows/python-security-scan.yml@<current-sha>

  test:
    needs: security
    uses: orangitfi/platform-tooling/.github/workflows/python-test.yml@<current-sha>
```

## Parameters

| Input | Default | Description |
|-------|---------|-------------|
| `working-directory` | `.` | Directory containing `pyproject.toml` and `uv.lock` |
| `fail-on-findings` | `true` | Fail the workflow if any scan detects issues |

## What it does

- **gitleaks**: checks full git history (`fetch-depth: 0`) for leaked API keys, tokens, passwords, and other secrets
- **pip-audit**: exports the uv lockfile to requirements.txt and queries the PyPA/OSV advisory databases for known CVEs — no packages are installed
- **guarddog**: exports the uv lockfile and checks each package against heuristic rules for supply-chain attack indicators — no packages are installed

Both pip-audit and guarddog install uv at the start of their jobs and operate against the committed lockfile only.

## When it has value

- **Pre-install gate**: both pip-audit and guarddog run before `uv sync`. A malicious or vulnerable package is caught before it ever executes on your runner.
- **Complementary coverage**: pip-audit finds CVE-tracked vulnerabilities (things in the OSV database); guarddog finds behavioural threats that have no CVE entry yet (obfuscated code, suspicious registry metadata, typosquatted names). Together they cover both vectors.
- **Parallel execution**: all three scans run simultaneously — total wall-clock time is the slowest scan (~30–60 s), not the sum.

## Tips

- `uv.lock` must be committed. The export step uses `--frozen` which fails immediately if the lockfile is stale relative to `pyproject.toml`. Fix with `uv lock`.
- If gitleaks flags a test fixture as a false positive, add an allowlist entry to `.gitleaks.toml` in the consuming repo. See the [gitleaks-scan action README](../actions/gitleaks-scan/README.md#handling-false-positives).
- Start with `fail-on-findings: false` when adding to an existing repo to understand the baseline noise before enabling hard failures.
