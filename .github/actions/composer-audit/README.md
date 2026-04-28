# Composer Audit

Composite action that runs `composer audit` against a project's `composer.lock` to detect known vulnerabilities in PHP dependencies. `composer audit` is a built-in Composer command (available since Composer 2.4; severity filtering requires 2.8) that queries the GitHub Security Advisory database and the Packagist security advisories feed — no binary download or extra installation is required.

## Usage

> Replace `<current-sha>` with the current SHA from the [root README](../../../README.md#current-sha).

```yaml
jobs:
  composer-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6.0.2

      - uses: orangitfi/platform-tooling/.github/actions/composer-audit@<current-sha>
        with:
          working-directory: .
          fail-on-findings: true
```

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `working-directory` | No | `.` | Directory containing `composer.json` and `composer.lock` |
| `fail-on-findings` | No | `true` | Fail the job if vulnerabilities are found |
| `ignore-severity` | No | `""` | Space-separated severity levels to ignore: `low`, `medium`, `high`, `critical`. Unlike npm's `audit-level` (minimum threshold), this is inverted — you specify what to *ignore*. To fail only on high and critical, set `"low medium"`. Leave empty to report all severities. |

## Outputs

| Output | Description |
|--------|-------------|
| `result` | `passed` or `failed` |
| `vulnerabilities-found` | Total number of vulnerabilities found |

## Requirements

- `composer.lock` must exist in the working directory. The action fails immediately with a clear error if it is missing. `composer audit` reads the lockfile only — it does not install dependencies.
- Composer ≥ 2.8 must be available on the runner. It is pre-installed on all GitHub-hosted `ubuntu-latest` runners. The action verifies the version at runtime and exits with a clear error if the requirement is not met.
- No packages are installed during the scan — `composer audit` operates against the committed lockfile.

## Notes

- The action writes a summary table to `$GITHUB_STEP_SUMMARY` on every run. When vulnerabilities are found, a collapsible block containing the full human-readable `composer audit` output is appended.
- `composer audit` requires outbound HTTPS access to `packagist.org` and the GitHub Advisory API (`api.github.com`). Ensure these endpoints are reachable from your runner.
- To suppress a specific advisory that does not apply to your usage (e.g. a vulnerability in a code path you do not exercise), add it to the `ignored-security-advisories` list in your `composer.json`:

```json
{
  "config": {
    "audit": {
      "ignored": ["CVE-2024-12345"]
    }
  }
}
```

- Start with `fail-on-findings: false` when adding this action to an existing repository to understand the current baseline before enabling hard failures.
