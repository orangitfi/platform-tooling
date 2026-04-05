# Hadolint Composite Action

This GitHub Action provides a simple way to lint Dockerfiles using [Hadolint](https://github.com/hadolint/hadolint), a Dockerfile linter that helps you write best practice Docker images.

## Usage

```yaml
- uses: orangitfi/platform-tooling/.github/actions/docker-lint@<current-sha>
  with:
    dockerfile: './Dockerfile'
    working-directory: '.'
```

> Replace `<current-sha>` with the current SHA from the [root README](../../../README.md#current-sha).

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `dockerfile` | Yes | `./Dockerfile` | Path to the Dockerfile to be linted |
| `working-directory` | No | `.` | Working directory where Hadolint will be executed |

## Example

Here's a complete example of how to use this action in your workflow:

```yaml
name: Lint Dockerfile

on:
  push:
    paths:
      - '**/Dockerfile'
  pull_request:
    paths:
      - '**/Dockerfile'

jobs:
  lint:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      
      - uses: orangitfi/platform-tooling/.github/actions/docker-lint@<current-sha>
        with:
          dockerfile: './Dockerfile'
          working-directory: '.'
```

## What is Hadolint?

Hadolint is a Dockerfile linter that helps you write best practice Docker images. It parses the Dockerfile into an AST and performs rules on top of the AST. It stands on the shoulders of ShellCheck to lint the Bash code inside RUN instructions.

## License

This action is part of the orangit-template project. See the main project's LICENSE file for details.
