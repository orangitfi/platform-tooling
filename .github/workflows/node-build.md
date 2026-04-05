# node-build

Reusable workflow that installs npm dependencies and runs the project build script.

> Replace `<current-sha>` with the current SHA from the [root README](../../README.md#current-sha).

## Usage

### Minimal

```yaml
on: [push, pull_request]

jobs:
  build:
    uses: orangitfi/platform-tooling/.github/workflows/node-build.yml@<current-sha>
```

### Frontend in a subdirectory, custom build script

```yaml
jobs:
  build:
    uses: orangitfi/platform-tooling/.github/workflows/node-build.yml@<current-sha>
    with:
      working-directory: ./frontend
      build-command: build:prod
```

### As part of a full pipeline

```yaml
jobs:
  security:
    uses: orangitfi/platform-tooling/.github/workflows/node-security-scan.yml@<current-sha>

  build:
    needs: security
    uses: orangitfi/platform-tooling/.github/workflows/node-build.yml@<current-sha>

  test:
    needs: build
    uses: orangitfi/platform-tooling/.github/workflows/node-test.yml@<current-sha>
```

## Parameters

| Input | Default | Description |
|-------|---------|-------------|
| `working-directory` | `.` | Directory containing `package.json` |
| `build-command` | `build` | npm script name to run (`npm run <build-command>`) |

## What it does

1. Checks out the repository
2. Runs `npm ci` — installs exact versions from `package-lock.json` with no lockfile modification
3. Runs `npm run <build-command>`

## When it has value

- Verifies the project compiles on every PR — catches TypeScript errors, missing imports, and broken Vite/webpack configs before they reach main
- Using `npm ci` (not `npm install`) ensures the lockfile is respected and no unexpected dependency upgrades occur in CI

## Tips

- `npm ci` requires `package-lock.json` to be committed. If it is missing the step fails immediately.
- For Next.js projects, `npm run build` also generates the `.next` build output. If you want to reuse this output in a deploy job, consider uploading it as an artifact.
- TypeScript compile errors appear in the build output. If you want them as individual annotations on the PR diff, configure your TypeScript build to output structured diagnostics.
