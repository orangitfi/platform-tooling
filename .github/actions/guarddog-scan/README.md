# Guarddog PyPI Supply-Chain Scan

Composite action that exports the [uv](https://docs.astral.sh/uv/) lockfile to `requirements.txt` and runs [guarddog](https://github.com/DataDog/guarddog) to verify all PyPI packages for supply-chain threats **before any dependency is installed**.

Guarddog detects malicious packages through static heuristics including typosquatting, obfuscated code, credential exfiltration, suspicious install hooks, and other indicators of compromise. Scanning happens against the lockfile — the actual packages are never downloaded or executed.

> **Requires uv in PATH.** Call the [`setup-uv`](../setup-uv/README.md) action in the same job before this one.

## Usage

> Replace `<current-sha>` with the current SHA from the [root README](../../../README.md#current-sha).

```yaml
jobs:
  guarddog:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4

      - uses: orangitfi/platform-tooling/.github/actions/setup-uv@<current-sha>

      - uses: orangitfi/platform-tooling/.github/actions/guarddog-scan@<current-sha>
        with:
          working-directory: .
```

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `working-directory` | **Yes** | — | Directory containing `pyproject.toml` and `uv.lock` |
| `fail-on-findings` | No | `true` | Fail the job if supply-chain threats are detected |

## What it does

1. Runs `uv export --format requirements-txt --no-hashes --frozen` to produce a flat requirements list from the lockfile without downloading anything
2. Appends the exported dependency list to the GitHub Actions job summary
3. Installs guarddog via `pipx install guarddog` (pipx is pre-installed on all GitHub-hosted runners)
4. Runs `guarddog pypi verify requirements-exported.txt`
5. On findings: appends the guarddog output to the job summary and either fails or warns depending on `fail-on-findings`
6. Cleans up the temporary files

## When it has value

- **Pre-install supply-chain gate**: catches malicious packages before `uv sync` runs, so compromised packages never execute on your runner
- **Pinned lockfiles**: combined with `uv.lock`, gives you a precise record of exactly which package versions were scanned
- Complements `pip-audit` (which checks for known CVEs) — guarddog looks for *behavioural* red flags that CVE databases do not cover

## Tips

- Always run this scan **before** `uv sync`. The whole point is to reject malicious code before it runs.
- If guarddog flags a package you have reviewed and trust, you can suppress it with a `guarddog` config file (`.guarddog.yml`). See the [guarddog docs](https://github.com/DataDog/guarddog#configuration) for the format.
- The `--frozen` flag ensures the export uses the committed lockfile exactly. If the lockfile is out of sync with `pyproject.toml` the step will fail — fix it with `uv lock`.

## Requirements

- `uv` must be installed and in PATH. Use the [`setup-uv`](../setup-uv/README.md) action.
- `pipx` must be available. It is pre-installed on all GitHub-hosted `ubuntu-latest` runners.
- The working directory must contain both `pyproject.toml` and `uv.lock`.
