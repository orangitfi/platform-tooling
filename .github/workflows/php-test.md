# php-test

Reusable workflow that installs Composer dependencies and runs PHPUnit unit tests.

This covers **unit tests only** — tests that run without external services (no database, no Redis, no message queue). Integration and end-to-end tests that require a live environment or `docker-compose` are out of scope for this baseline workflow.

> Replace `<current-sha>` with the current SHA from the [root README](../../README.md#current-sha).

## Usage

### Minimal — run PHPUnit from the repo root

```yaml
on: [push, pull_request]

jobs:
  test:
    uses: orangitfi/platform-tooling/.github/workflows/php-test.yml@<current-sha>
```

### Run a specific test suite

```yaml
jobs:
  test:
    uses: orangitfi/platform-tooling/.github/workflows/php-test.yml@<current-sha>
    with:
      test-command: "vendor/bin/phpunit --testsuite=Unit"
```

### Verbose output with short backtrace

```yaml
jobs:
  test:
    uses: orangitfi/platform-tooling/.github/workflows/php-test.yml@<current-sha>
    with:
      test-command: "vendor/bin/phpunit -v"
```

### Backend in a subdirectory

```yaml
jobs:
  test:
    uses: orangitfi/platform-tooling/.github/workflows/php-test.yml@<current-sha>
    with:
      working-directory: ./backend
```

### Recommended position in a pipeline

```yaml
jobs:
  security:
    uses: orangitfi/platform-tooling/.github/workflows/php-security-scan.yml@<current-sha>

  lint:
    uses: orangitfi/platform-tooling/.github/workflows/php-lint.yml@<current-sha>

  test:
    needs: security
    uses: orangitfi/platform-tooling/.github/workflows/php-test.yml@<current-sha>
```

## Parameters

| Input | Default | Description |
|-------|---------|-------------|
| `working-directory` | `.` | Directory containing `composer.json` |
| `test-command` | `vendor/bin/phpunit` | Full command to run tests |
| `composer-args` | `""` | Extra arguments passed to `composer install` |

## What it does

1. Checks out the repository
2. Runs `composer install --no-interaction --prefer-dist --optimize-autoloader [composer-args]` — installs all dependencies including dev
3. Runs `<test-command>` in the working directory

## Prerequisites

PHPUnit must be installed as a Composer dev dependency:

```bash
composer require --dev phpunit/phpunit
```

PHPUnit configuration (`phpunit.xml` or `phpunit.xml.dist`) in the project root is used automatically when running `vendor/bin/phpunit` without extra arguments.

## When it has value

- Catches regressions in pure logic (domain objects, services, utilities) without spinning up a full environment
- Fast feedback on every PR — unit tests typically complete in seconds
- A useful baseline even for projects where integration tests require `docker-compose`: run unit tests in CI and integration tests separately or on a schedule

## Tips

- Use `--testsuite=Unit` to target only tests that have no environment dependencies, especially in projects that mix unit and integration tests in the same PHPUnit config.
- Pass environment variables the tests need via `env:` on the calling job — reusable workflows inherit the caller's environment.
- To generate a code coverage report, set `test-command` to `vendor/bin/phpunit --coverage-clover coverage.xml` and upload `coverage.xml` as a workflow artifact in a subsequent step.
