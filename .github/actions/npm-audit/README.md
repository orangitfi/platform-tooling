# npm Audit

Composite action that runs `npm audit` against a project's lockfile to detect known vulnerabilities in dependencies.

`NPM_CONFIG_IGNORE_SCRIPTS=true` is set for the entire step, preventing npm lifecycle scripts from executing — this stops malicious `postinstall` or `preinstall` scripts from running in CI before a vulnerability check completes.

## Usage

> Replace `<current-sha>` with the current SHA from the [root README](../../../README.md#current-sha).

```yaml
jobs:
  npm-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4

      - uses: orangitfi/platform-tooling/.github/actions/npm-audit@<current-sha>
        with:
          working-directory: ./src
          audit-level: high
```

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `working-directory` | No | `.` | Directory containing `package.json` and `package-lock.json` |
| `audit-level` | No | `high` | Minimum severity to fail on: `low`, `moderate`, `high`, `critical` |
| `fail-on-findings` | No | `true` | Fail the job if vulnerabilities are found |

## Outputs

| Output | Description |
|--------|-------------|
| `result` | `passed` or `failed` |
| `vulnerabilities-found` | Total number of vulnerabilities found |

## Requirements

- A `package-lock.json` must exist in the working directory. The action fails immediately with a clear error if it is missing. `npm audit` operates against the lockfile — it does not install dependencies.
- `npm` must be available on the runner. It is pre-installed on all GitHub-hosted runners.

## Why `NPM_CONFIG_IGNORE_SCRIPTS=true`

npm lifecycle scripts (`preinstall`, `postinstall`, etc.) can execute arbitrary code. Setting this variable ensures that even if npm performs any internal resolution steps, no scripts are invoked. This is especially important in supply chain attack scenarios where a dependency may ship a malicious install script.

## Handling false positives

If `npm audit` flags a vulnerability that does not apply to your usage (e.g. a dev-only dependency, a vulnerability in a code path you do not exercise), use the npm audit resolution workflow to suppress it:

```bash
npm audit fix          # auto-fix where possible
npm audit fix --force  # upgrade breaking changes (review carefully)
```

For vulnerabilities that cannot be fixed immediately and are accepted as known risk, create an `.npmrc` or use `npm audit --omit=dev` to exclude development dependencies from the audit:

```yaml
- uses: ./.github/actions/npm-audit
  with:
    audit-level: critical   # raise threshold temporarily while tracking the fix
```

## Notes

- The action writes a summary table and, on failure, a collapsible audit output block to the GitHub Actions job summary.
- `npm audit` queries the npm registry. Ensure outbound HTTPS access to `registry.npmjs.org` is permitted on your runner.
