# node-lint

Reusable workflow that runs lint checks **in parallel** against Node.js / React / Next.js repositories. Both jobs run independently — a Dockerfile lint failure does not block the npm lint result.

> Replace `<current-sha>` with the current SHA from the [root README](../../README.md#current-sha).

## Jobs

| Job | Tool | What it checks |
|-----|------|----------------|
| `npm-lint` | Your project's npm lint script | Code style, formatting, and static analysis (ESLint, Prettier, etc.) |
| `docker-lint` | hadolint | Dockerfile best-practice violations — skipped cleanly if no Dockerfile is found |

## Usage

### Minimal

```yaml
on: [push, pull_request]

jobs:
  lint:
    uses: orangitfi/platform-tooling/.github/workflows/node-lint.yml@<current-sha>
```

### Frontend in a subdirectory, custom lint script

```yaml
jobs:
  lint:
    uses: orangitfi/platform-tooling/.github/workflows/node-lint.yml@<current-sha>
    with:
      working-directory: ./frontend
      lint-command: lint:ci
      dockerfile-path: ./frontend/Dockerfile
```

### Repo without a Dockerfile (docker-lint skips automatically)

```yaml
jobs:
  lint:
    uses: orangitfi/platform-tooling/.github/workflows/node-lint.yml@<current-sha>
    # No dockerfile-path needed — if Dockerfile is not found the job is skipped, not failed
```

## Parameters

| Input | Default | Description |
|-------|---------|-------------|
| `working-directory` | `.` | Directory containing `package.json` |
| `lint-command` | `lint` | npm script name to run for linting (`npm run <lint-command>`) |
| `dockerfile-path` | `Dockerfile` | Path to the Dockerfile relative to the repo root |

## When it has value

- Enforces a consistent code style gate on every PR without depending on individual developer tooling
- The Dockerfile lint job catches common security and maintainability issues (pinned base image versions, `COPY` vs `ADD`, `apt-get` best practices) without any extra setup
- Repositories that have no Dockerfile still get the npm lint job — the docker-lint job exits with a notice rather than failing

## Tips

- The npm lint script must be defined in `package.json`. Common names: `lint`, `lint:check`, `lint:ci`. If your script name differs, set `lint-command`.
- hadolint rules can be suppressed with inline comments in the Dockerfile: `# hadolint ignore=DL3008`. For project-wide suppressions, add a `.hadolint.yaml` file to the repo root.
- Add this workflow as a required status check in your branch protection rules so PRs cannot be merged with lint failures.
