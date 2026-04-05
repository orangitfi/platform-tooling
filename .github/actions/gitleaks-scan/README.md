# Gitleaks Secret Scan

Composite action that installs [gitleaks](https://github.com/gitleaks/gitleaks) from a pinned release and scans the repository for leaked secrets.

No third-party marketplace actions are used. The binary is downloaded directly from the official GitHub release and verified against a hardcoded SHA-256 checksum before execution.

## Usage

> Replace `<current-sha>` with the current SHA from the [root README](../../../README.md#current-sha).

```yaml
jobs:
  secrets-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # required for full git history scan

      - uses: orangitfi/platform-tooling/.github/actions/gitleaks-scan@<current-sha>
        with:
          config-path: .gitleaks.toml
```

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `config-path` | No | `.gitleaks.toml` | Path to the gitleaks configuration file |
| `scan-path` | No | `.` | Directory to scan |
| `fail-on-findings` | No | `true` | Fail the job if secrets are detected |
| `no-git` | No | `false` | Scan the filesystem directly instead of git history |

## Outputs

| Output | Description |
|--------|-------------|
| `result` | `passed` or `failed` |
| `findings-count` | Number of findings detected |

## Version pinning

The action is pinned to **gitleaks v8.24.3**. The SHA-256 checksum for each supported platform is hardcoded in `action.yml` and verified before the binary is executed.

To upgrade:
1. Update `GITLEAKS_VERSION` in `action.yml`
2. Download the new `gitleaks_<version>_checksums.txt` from the release page
3. Replace **all four** checksum values (`CHECKSUM_LINUX_AMD64`, `CHECKSUM_LINUX_ARM64`, `CHECKSUM_DARWIN_AMD64`, `CHECKSUM_DARWIN_ARM64`)

## Supported platforms

| Runner OS | Architecture |
|-----------|-------------|
| `ubuntu-latest` | `x86_64` (amd64) |
| `ubuntu-latest` (ARM) | `aarch64` (arm64) |
| `macos-latest` | `x86_64` |
| `macos-latest` (M-series) | `arm64` |

## Handling false positives

If the scan flags a value that is not a real secret (e.g. a placeholder, test fixture, or example value), create a `.gitleaks.toml` file in the root of the consuming repository and add an allowlist entry.

**Suppress a specific string:**

```toml
[extend]
useDefault = true

[allowlist]
description = "Known safe patterns in this repository"
regexes = [
  '''MY_PLACEHOLDER_VALUE''',
]
```

**Suppress a specific file:**

```toml
[extend]
useDefault = true

[allowlist]
description = "Known safe patterns in this repository"
paths = [
  '''tests/fixtures/fake-credentials\.json''',
]
```

`useDefault = true` keeps the full built-in ruleset active and only adds your exceptions on top of it.

Once the file exists at the default path (`.gitleaks.toml`), the action picks it up automatically on the next run — no changes to the workflow are needed.

## Notes

- `fetch-depth: 0` is required in the checkout step when scanning git history (the default). Without it, only the most recent commit is available.
- Set `no-git: true` to scan the working tree only (e.g. when the repo has no git history available).
- The action writes a summary table and, on failure, a collapsible scan output block to the GitHub Actions job summary.
