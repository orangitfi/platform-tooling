# python-lint

Reusable workflow that runs code quality checks **in parallel** against Python / uv repositories.

> Replace `<current-sha>` with the current SHA from the [root README](../../README.md#current-sha).

## Jobs

| Job | Tool | What it checks |
|-----|------|----------------|
| `ruff` | ruff (via `uvx`) | Code style violations (`ruff check`) and formatting (`ruff format --check`) |
| `docker-lint` | hadolint | Dockerfile best-practice violations — skipped cleanly if no Dockerfile is found |

## Usage

### Minimal

```yaml
on: [push, pull_request]

jobs:
  lint:
    uses: orangitfi/platform-tooling/.github/workflows/python-lint.yml@<current-sha>
```

### Backend in a subdirectory

```yaml
jobs:
  lint:
    uses: orangitfi/platform-tooling/.github/workflows/python-lint.yml@<current-sha>
    with:
      working-directory: ./backend
      dockerfile-path: ./backend/Dockerfile
```

### Format check only (disable lint rules)

```yaml
jobs:
  lint:
    uses: orangitfi/platform-tooling/.github/workflows/python-lint.yml@<current-sha>
    with:
      run-ruff-lint: false
```

### Repos without a Dockerfile (docker-lint skips automatically)

```yaml
jobs:
  lint:
    uses: orangitfi/platform-tooling/.github/workflows/python-lint.yml@<current-sha>
    # No dockerfile-path — if Dockerfile is not found the job is skipped, not failed
```

## Parameters

| Input | Default | Description |
|-------|---------|-------------|
| `working-directory` | `.` | Directory containing `pyproject.toml` |
| `run-ruff-lint` | `true` | Run `ruff check .` (lint rules) |
| `run-ruff-format` | `true` | Run `ruff format --check .` (formatting) |
| `dockerfile-path` | `Dockerfile` | Path to the Dockerfile relative to the repo root |

## What it does

- **ruff check**: runs ruff's lint rules (replaces flake8, isort, pyupgrade, and many others). Ruff is installed ephemerally via `uvx` — no project dependency required.
- **ruff format --check**: checks formatting without modifying files (replaces black). Reports a non-zero exit if any file would be reformatted.
- **docker-lint**: runs hadolint on the Dockerfile, skipped with a notice if the file doesn't exist.

## When it has value

- ruff is extremely fast (Rust-based) — the lint + format check typically completes in under 10 seconds even on large codebases
- Using `uvx ruff` means ruff does not need to be in `pyproject.toml` or `uv.lock` — it runs in an isolated environment, so you get linting even on new repos that haven't added ruff yet
- Enforcing a style gate on every PR eliminates style debates in code review

## Tips

- Configure ruff rules in `pyproject.toml` under `[tool.ruff]`. All ruff configuration (line length, enabled rules, per-file ignores) is read from the project automatically.
- To fix ruff issues locally: `uvx ruff check --fix .` and `uvx ruff format .`
- hadolint rules can be suppressed inline with `# hadolint ignore=DL3008` or globally via `.hadolint.yaml` in the repo root.
- Add this workflow as a required status check in your branch protection rules so PRs cannot be merged with lint or formatting failures.
