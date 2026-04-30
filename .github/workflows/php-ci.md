# php-ci

Reusable workflow that wires together the full PHP / Composer CI pipeline in a single call. The consuming repo controls **when** it runs; this workflow controls **how**.

> Replace `<current-sha>` with the current SHA from the [root README](../../README.md#current-sha).

## Pipeline shape

```
push / pull_request / workflow_dispatch
        │
        ▼
   ┌──────────┐
   │ security │  gitleaks + composer-audit + guarddog (parallel)
   └─────┬────┘
         │ (gates everything below)
         ├──────────────┐
         ▼              ▼
     ┌──────┐       ┌──────┐
     │ lint │       │ test │
     └──┬───┘       └──┬───┘
        └──────────────┘
                │ (both must pass)
                ▼
      ┌──────────────────┐
      │vulnerability-scan│  Syft + Grype (code + Docker)
      └──────────────────┘
```

## Usage

### Minimal — PHP service, no Dockerfile

```yaml
# .github/workflows/ci.yml  (in your consuming repo)
name: CI

on:
  push:
  pull_request:
  workflow_dispatch:

jobs:
  ci:
    uses: orangitfi/platform-tooling/.github/workflows/php-ci.yml@<current-sha>
    with:
      run-docker-scan: false
```

### PHP service with a Dockerfile

```yaml
jobs:
  ci:
    uses: orangitfi/platform-tooling/.github/workflows/php-ci.yml@<current-sha>
    with:
      image-name: my-app
```

### Custom PHPStan level and test suite

```yaml
jobs:
  ci:
    uses: orangitfi/platform-tooling/.github/workflows/php-ci.yml@<current-sha>
    with:
      phpstan-level: "6"
      test-command:  "vendor/bin/phpunit --testsuite=Unit"
```

### Full example with all options explicit

```yaml
jobs:
  ci:
    uses: orangitfi/platform-tooling/.github/workflows/php-ci.yml@<current-sha>
    with:
      working-directory: .
      run-phpcs:         true
      phpcs-standard:    PSR12
      run-phpstan:       true
      phpstan-level:     "5"
      paths:             src
      dockerfile-path:   Dockerfile
      test-command:      vendor/bin/phpunit
      composer-args:     ""
      fail-on-severity:  high
      run-docker-scan:   true
      image-name:        my-app
```

## Parameters

| Input | Default | Description |
|-------|---------|-------------|
| `working-directory` | `.` | Directory containing `composer.json` |
| `run-phpcs` | `true` | Run PHP_CodeSniffer in the lint job |
| `phpcs-standard` | `PSR12` | Coding standard when no `phpcs.xml` is present |
| `run-phpstan` | `true` | Run PHPStan in the lint job |
| `phpstan-level` | `5` | Analysis level 1–9 when no `phpstan.neon` is present |
| `paths` | `src` | Space-separated paths both lint tools scan (when no config file is present) |
| `dockerfile-path` | `Dockerfile` | Path to the Dockerfile (used by lint and vulnerability scan) |
| `test-command` | `vendor/bin/phpunit` | Full command to run tests |
| `composer-args` | `""` | Extra arguments passed to `composer install` in the test job |
| `fail-on-severity` | `high` | Minimum Grype severity for the vulnerability scan |
| `run-docker-scan` | `true` | Build and scan the Docker image in the vulnerability scan |
| `image-name` | *(repo name)* | Docker image name for the vulnerability scan |

## Jobs reference

| Job | Calls | Condition |
|-----|-------|-----------|
| `security` | `php-security-scan` | always |
| `lint` | `php-lint` | always (after security) |
| `test` | `php-test` | always (after security) |
| `vulnerability-scan` | `php-vulnerability-scan` | after lint and test pass |

## When it has value

- **Single line of CI**: one `uses:` line gives you secret scanning, dependency auditing, static analysis, unit tests, and vulnerability scanning — in the right order, with the right gates.
- **No Dockerfile?** Set `run-docker-scan: false` — the pipeline still runs all PHP-specific quality checks.
- **Scan before install**: composer-audit and guarddog run against `composer.lock` and `composer.json` before any package is installed. A compromised dependency is blocked before it executes.
- **Project config files respected**: if `phpcs.xml` or `phpstan.neon` are committed, the lint job uses them as-is. Workflow inputs only apply as fallbacks.

## Tips

- If phpcs or phpstan are not yet dev dependencies in the project, set `run-phpcs: false` and/or `run-phpstan: false` to skip them until the tools are added.
- Add this workflow as the sole required status check in branch protection rules: one check covers the entire pipeline.
- For nightly DAST scanning of the deployed service, use [`php-daily`](php-daily.md) in a separate scheduled workflow.
