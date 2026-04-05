# Setup uv

Composite action that installs [uv](https://docs.astral.sh/uv/) from the official GitHub release with SHA-256 verification. No marketplace actions are used — the binary is downloaded directly, checksum-verified, and placed in `/usr/local/bin`.

## Usage

> Replace `<current-sha>` with the current SHA from the [root README](../../../README.md#current-sha).

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - uses: orangitfi/platform-tooling/.github/actions/setup-uv@<current-sha>

      - run: uv sync --frozen
```

## Inputs

This action has no inputs. It always installs the pinned version of uv.

## What it does

1. Downloads `uv-x86_64-unknown-linux-gnu.tar.gz` from the GitHub releases CDN
2. Verifies the download against a hardcoded SHA-256 checksum
3. Extracts `uv` and `uvx` binaries to `/usr/local/bin`
4. Prints `uv --version` to confirm a successful install

## When it has value

This action is a prerequisite for all Python / uv composite actions and reusable workflows in this repository:

- [`pip-audit`](../pip-audit/README.md) — needs `uv export`
- [`guarddog-scan`](../guarddog-scan/README.md) — needs `uv export`
- [`python-test`](../../workflows/python-test.md) — needs `uv sync` and `uv run`
- [`python-lint`](../../workflows/python-lint.md) — needs `uvx ruff`

Call it once per job before any other uv-dependent step.

## Version pinning

Pinned to **uv v0.11.3**, `uv-x86_64-unknown-linux-gnu.tar.gz`.  
SHA-256: `c0f3236f146e55472663cfbcc9be3042a9f1092275bbe3fe2a56a6cbfd3da5ce`

To upgrade:
1. Find the new release at [github.com/astral-sh/uv/releases](https://github.com/astral-sh/uv/releases)
2. Download `uv-x86_64-unknown-linux-gnu.tar.gz` and its `.sha256` file
3. Update `GITLEAKS_VERSION` and the `echo "... | sha256sum -c"` line in `action.yml`

## Notes

- Only `x86_64` Linux is supported (matches `ubuntu-latest` GitHub-hosted runners)
- `uvx` is also installed — it is the shorthand for `uv tool run` and is used by the ruff lint steps
