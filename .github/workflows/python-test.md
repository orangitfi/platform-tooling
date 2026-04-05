# python-test

Reusable workflow that installs Python dependencies with uv and runs pytest.

uv resolves the Python version from the project's `pyproject.toml` or `.python-version` file automatically. `uv sync --frozen` installs all dependencies from the committed lockfile without modifying it.

> Replace `<current-sha>` with the current SHA from the [root README](../../README.md#current-sha).

## Usage

### Minimal — run pytest from the repo root

```yaml
on: [push, pull_request]

jobs:
  test:
    uses: orangitfi/platform-tooling/.github/workflows/python-test.yml@<current-sha>
```

### Custom test command with extra output

```yaml
jobs:
  test:
    uses: orangitfi/platform-tooling/.github/workflows/python-test.yml@<current-sha>
    with:
      test-command: "pytest tests/ -v --tb=short"
```

### Install test-only extras declared in pyproject.toml

```yaml
jobs:
  test:
    uses: orangitfi/platform-tooling/.github/workflows/python-test.yml@<current-sha>
    with:
      uv-sync-args: "--extra test"
```

### Backend in a subdirectory

```yaml
jobs:
  test:
    uses: orangitfi/platform-tooling/.github/workflows/python-test.yml@<current-sha>
    with:
      working-directory: ./backend
      uv-sync-args: "--extra test --extra dev"
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
| `working-directory` | `.` | Directory containing `pyproject.toml` |
| `test-command` | `pytest` | Command to run via `uv run` |
| `uv-sync-args` | `""` | Extra arguments passed to `uv sync` (e.g. `--extra test`) |

## What it does

1. Installs uv v0.11.3 with SHA-256 verification
2. Runs `uv sync --frozen [uv-sync-args]` — installs all dependencies from the committed lockfile, including the correct Python version
3. Runs `uv run <test-command>` in the working directory

## When it has value

- `uv sync --frozen` is strict: if `pyproject.toml` has changed since the last `uv lock`, the sync fails with a clear error. This enforces that the lockfile is always kept up to date.
- `uv run` activates the project venv automatically — no manual `source .venv/bin/activate` or `PYTHONPATH` configuration needed
- uv downloads and manages the Python interpreter itself, so the test always runs on the exact Python version the project declares, regardless of what the runner has pre-installed

## Tips

- To run only a subset of tests (e.g. fast unit tests on PR, full suite nightly), use different `test-command` values in different workflow triggers.
- Add `--cov` and `--cov-report=xml` to `test-command` to generate a coverage report. Upload it as an artifact or send it to a coverage service as a subsequent step.
- The `uv-sync-args` input is useful when test dependencies are declared as optional extras in `pyproject.toml` (e.g. `[project.optional-dependencies] test = ["pytest", "httpx"]`). Pass `--extra test` to install them.
- If tests require environment variables (database URLs, API keys), pass them as `env:` on the calling job. Reusable workflows inherit the caller's environment.
