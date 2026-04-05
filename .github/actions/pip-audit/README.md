# pip-audit

Composite action that exports the [uv](https://docs.astral.sh/uv/) lockfile to `requirements.txt` and runs [pip-audit](https://github.com/pypa/pip-audit) to detect known CVEs in Python dependencies **before any package is installed**.

pip-audit queries the Python Packaging Advisory Database (PyPA) and the OSV database for vulnerabilities. Scanning happens against the lockfile only — nothing is installed or executed.

> **Requires uv in PATH.** Call the [`setup-uv`](../setup-uv/README.md) action in the same job before this one.

## Usage

> Replace `<current-sha>` with the current SHA from the [root README](../../../README.md#current-sha).

```yaml
jobs:
  pip-audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: orangitfi/platform-tooling/.github/actions/setup-uv@<current-sha>

      - uses: orangitfi/platform-tooling/.github/actions/pip-audit@<current-sha>
        with:
          working-directory: .
```

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `working-directory` | **Yes** | — | Directory containing `pyproject.toml` and `uv.lock` |
| `fail-on-findings` | No | `true` | Fail the job if vulnerabilities are found |

## What it does

1. Runs `uv export --format requirements-txt --no-hashes --frozen` to produce a flat requirements list from the lockfile
2. Appends the exported dependency list to the GitHub Actions job summary
3. Runs `uv tool run pip-audit -r requirements.txt` (pip-audit is installed ephemerally — nothing is left on the runner)
4. On findings: appends the full pip-audit output to the job summary and either fails or warns depending on `fail-on-findings`
5. Cleans up temporary files

## When it has value

- **CVE detection before install**: catches packages with known exploits before `uv sync` runs and before any code executes
- **Lockfile-based**: uses the committed `uv.lock` rather than the live registry state, so results are reproducible and don't change between runs unless you update the lockfile
- Complements [`guarddog-scan`](../guarddog-scan/README.md) — pip-audit finds CVE-tracked vulnerabilities, guarddog finds behavioural/heuristic supply-chain threats; together they cover both vectors

## Handling findings

When pip-audit reports a vulnerability:

1. Check the advisory link in the output for severity and fix version
2. Update the dependency in `pyproject.toml` and run `uv lock` to refresh the lockfile
3. If no fix is available yet, you can set `fail-on-findings: false` temporarily and track the issue

## Tips

- `uv tool run pip-audit` installs pip-audit in a temporary isolated environment — it never pollutes your project's venv
- The `--frozen` flag on the export step ensures the lockfile is used as-is. If the lockfile is stale (`pyproject.toml` changed without `uv lock`), the export step will fail with a clear error
- pip-audit checks the OSV database which covers CVEs across PyPI. It is advisory-based — it will not catch zero-days or malicious-but-not-CVE'd packages (use guarddog for that)

## Requirements

- `uv` must be installed and in PATH. Use the [`setup-uv`](../setup-uv/README.md) action.
- The working directory must contain both `pyproject.toml` and `uv.lock`.
