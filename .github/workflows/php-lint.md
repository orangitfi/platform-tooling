# php-lint

Reusable workflow that runs PHP code quality checks **in parallel** against PHP / Symfony repositories.

> Replace `<current-sha>` with the current SHA from the [root README](../../README.md#current-sha).

## Jobs

| Job | Tool | What it checks |
|-----|------|----------------|
| `phpcs` | PHP_CodeSniffer | Code style violations and formatting (PSR-12 by default) |
| `phpstan` | PHPStan | Type errors, undefined variables, unreachable code, and other static analysis findings |
| `docker-lint` | hadolint | Dockerfile best-practice violations — skipped cleanly if no Dockerfile is found |

## Usage

### Minimal

```yaml
on: [push, pull_request]

jobs:
  lint:
    uses: orangitfi/platform-tooling/.github/workflows/php-lint.yml@<current-sha>
```

### Backend in a subdirectory

```yaml
jobs:
  lint:
    uses: orangitfi/platform-tooling/.github/workflows/php-lint.yml@<current-sha>
    with:
      working-directory: ./backend
      dockerfile-path: ./backend/Dockerfile
```

### phpcs only (disable PHPStan)

```yaml
jobs:
  lint:
    uses: orangitfi/platform-tooling/.github/workflows/php-lint.yml@<current-sha>
    with:
      run-phpstan: false
```

### PHPStan only (disable phpcs)

```yaml
jobs:
  lint:
    uses: orangitfi/platform-tooling/.github/workflows/php-lint.yml@<current-sha>
    with:
      run-phpcs: false
```

### Custom PHPStan level and paths (no phpstan.neon in the project)

```yaml
jobs:
  lint:
    uses: orangitfi/platform-tooling/.github/workflows/php-lint.yml@<current-sha>
    with:
      phpstan-level: "6"
      paths: "src tests"
```

### Repos without a Dockerfile (docker-lint skips automatically)

```yaml
jobs:
  lint:
    uses: orangitfi/platform-tooling/.github/workflows/php-lint.yml@<current-sha>
    # No dockerfile-path needed — if Dockerfile is not found the job is skipped, not failed
```

## Parameters

| Input | Default | Description |
|-------|---------|-------------|
| `working-directory` | `.` | Directory containing `composer.json` |
| `run-phpcs` | `true` | Run PHP_CodeSniffer |
| `phpcs-standard` | `PSR12` | Coding standard (used only when no `phpcs.xml` is present) |
| `run-phpstan` | `true` | Run PHPStan |
| `phpstan-level` | `5` | Analysis level 1–9 (used only when no `phpstan.neon` is present) |
| `paths` | `src` | Space-separated paths both tools scan (used only when no tool config file is present) |
| `dockerfile-path` | `Dockerfile` | Path to the Dockerfile relative to the repo root |

## Prerequisites

Both phpcs and phpstan must be installed as Composer dev dependencies in the project. The workflow runs `composer install` before each job.

```bash
composer require --dev squizlabs/php_codesniffer phpstan/phpstan
```

If either binary is missing from `vendor/bin/`, the job fails immediately with a clear error message pointing to the missing dependency.

## Project config files take precedence

When a project-level config file is found, it is used as-is and the workflow inputs for paths/standard/level are ignored:

| Tool | Config files |
|------|-------------|
| phpcs | `phpcs.xml`, `phpcs.xml.dist` |
| phpstan | `phpstan.neon`, `phpstan.neon.dist` |

This means teams that already have these config files committed get exactly the same behaviour locally and in CI — no duplication.

## When it has value

- Enforces a consistent style gate on every PR without depending on developer tooling or IDE settings
- PHPStan catches bugs that unit tests often miss: wrong method signatures, missing return types, null-safety violations
- Running phpcs and phpstan in parallel keeps the job fast — neither blocks the other
- Dockerfile quality is checked in the same pipeline at no extra cost

## Tips

- Start with PHPStan level 1 or 2 on an existing codebase and increase the level gradually. Level 5 is a reasonable starting point for new projects.
- Commit a `phpstan.neon` to the project root to lock the level and paths so developers get the same analysis locally (`vendor/bin/phpstan analyse`) as in CI.
- phpcs auto-fixes are not available via this workflow — run `vendor/bin/phpcbf` locally to fix style violations.
- hadolint rules can be suppressed inline with `# hadolint ignore=DL3008` or globally via `.hadolint.yaml` in the repo root.
- Add this workflow as a required status check in branch protection rules so PRs cannot be merged with lint failures.
