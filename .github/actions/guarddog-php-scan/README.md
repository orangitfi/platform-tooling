# Guarddog Packagist Supply-Chain Scan

Composite action that installs [guarddog](https://github.com/DataDog/guarddog) and verifies all PHP packages declared in `composer.json` for supply-chain threats **before any dependency is installed**.

Guarddog detects malicious packages through static heuristics including typosquatting, code injection, data exfiltration, and other indicators of compromise.

## ⚠️ Experimental Warning

> **guarddog's Packagist (PHP) support exists but has received less production testing than its npm and PyPI equivalents.** Before enabling `fail-on-findings: true` in production pipelines, manually run `guarddog packagist verify composer.json` against your own project to validate that results are meaningful and noise levels are acceptable. Report unexpected behaviour to the [guarddog issue tracker](https://github.com/DataDog/guarddog/issues).
>
> It is strongly recommended to start with `fail-on-findings: false` to observe guarddog output before treating failures as blocking.

## Usage

> Replace `<current-sha>` with the current SHA from the [root README](../../../README.md#current-sha).

```yaml
jobs:
  guarddog-php:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@de0fac2e4500dabe0009e67214ff5f5447ce83dd # v6.0.2

      - uses: orangitfi/platform-tooling/.github/actions/guarddog-php-scan@<current-sha>
        with:
          working-directory: .
          fail-on-findings: false   # recommended until behaviour is verified
```

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `working-directory` | No | `.` | Directory containing `composer.json` |
| `fail-on-findings` | No | `true` | Fail the job if supply-chain threats are detected |

## Requirements

- `composer.json` must exist in the working directory. The action fails immediately with a clear error if it is missing. The scan runs against the manifest only — no dependencies are installed.
- `pipx` must be available on the runner. It is pre-installed on all GitHub-hosted `ubuntu-latest` runners. guarddog is installed at runtime via `pipx install guarddog`.

## Notes

- The action writes a summary table and an experimental caveat to `$GITHUB_STEP_SUMMARY` on every run. When threats are detected, a collapsible block containing the full guarddog output is appended.
- guarddog queries the Packagist registry to retrieve package metadata. Ensure outbound HTTPS access to `packagist.org` is permitted on your runner.
