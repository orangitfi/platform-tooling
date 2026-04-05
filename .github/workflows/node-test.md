# node-test

Reusable workflow that runs unit tests and Playwright end-to-end tests. Both jobs are optional and run **in parallel** when both are enabled.

> Replace `<current-sha>` with the current SHA from the [root README](../../README.md#current-sha).

## Jobs

| Job | When | What it does |
|-----|------|-------------|
| `unit-tests` | `run-unit-tests: true` (default) | Runs `npm run <test-command>` (jest, vitest, mocha, etc.) |
| `playwright` | `run-playwright: true` (opt-in) | Installs Chromium, runs Playwright, uploads the HTML report on failure |

## Usage

### Unit tests only (default)

```yaml
jobs:
  test:
    uses: orangitfi/platform-tooling/.github/workflows/node-test.yml@<current-sha>
```

### Unit tests + Playwright e2e

```yaml
jobs:
  test:
    uses: orangitfi/platform-tooling/.github/workflows/node-test.yml@<current-sha>
    with:
      run-playwright: true
```

### Playwright only (e.g. a dedicated e2e workflow)

```yaml
jobs:
  e2e:
    uses: orangitfi/platform-tooling/.github/workflows/node-test.yml@<current-sha>
    with:
      run-unit-tests:   false
      run-playwright:   true
      playwright-command: test:e2e
```

### Custom working directory and test commands

```yaml
jobs:
  test:
    uses: orangitfi/platform-tooling/.github/workflows/node-test.yml@<current-sha>
    with:
      working-directory: ./frontend
      test-command: test:unit
      run-playwright: true
      playwright-command: test:e2e:ci
```

## Parameters

| Input | Default | Description |
|-------|---------|-------------|
| `working-directory` | `.` | Directory containing `package.json` |
| `run-unit-tests` | `true` | Enable the unit test job |
| `test-command` | `test` | npm script for unit tests |
| `run-playwright` | `false` | Enable the Playwright job |
| `playwright-command` | `test:e2e` | npm script for Playwright tests |

## When it has value

- Unit tests run fast and catch regressions in business logic immediately
- Playwright catches UI regressions and integration issues that unit tests cannot — broken routing, failed API integration, rendered output divergence
- Running them in parallel keeps the total feedback time close to the slower of the two rather than their sum

## Tips

- The Playwright HTML report is uploaded as an artifact named `playwright-report` when the job fails. Download it from the Actions run to get a full breakdown of which tests failed, including screenshots and traces.
- `npx playwright install --with-deps chromium` installs only Chromium to keep install time short. If your tests need Firefox or WebKit, add them to the install command via a custom `playwright-command` wrapper or override this workflow.
- For visual regression tests (screenshot diffs), use the [`node-update-visual-snapshots`](node-update-visual-snapshots.md) workflow to regenerate baselines on Linux so they match what this CI job compares against.
- If Playwright tests are flaky in CI, try adding `--retries=2` to the playwright command. A retried pass still marks the job green.
