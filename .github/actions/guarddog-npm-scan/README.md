# Guarddog npm Supply-Chain Scan

Composite action that installs [guarddog](https://github.com/DataDog/guarddog) and verifies all npm packages declared in `package.json` for supply-chain threats **before any dependency is installed**.

Guarddog detects malicious packages through static heuristics including typosquatting, code injection, data exfiltration, and other indicators of compromise.

## Usage

> Replace `<current-sha>` with the current SHA from the [root README](../../../README.md#current-sha).

```yaml
- uses: orangitfi/platform-tooling/.github/actions/guarddog-npm-scan@<current-sha>
  with:
    working-directory: ./src
```

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `working-directory` | No | `.` | Directory containing `package.json` |
| `fail-on-findings` | No | `true` | Fail the job if threats are detected |

## Requirements

- `package.json` must exist in the working directory.
- `pipx` must be available on the runner. It is pre-installed on all GitHub-hosted runners.
- Guarddog is installed at runtime via `pipx install guarddog`. No dependencies are installed from `package.json` — the scan runs against the package manifest only.

## Notes

- The action writes a summary table and, on failure, a collapsible guarddog output block to the GitHub Actions job summary.
- Guarddog queries the npm registry to retrieve package metadata. Ensure outbound HTTPS access to the npm registry is permitted on your runner.
