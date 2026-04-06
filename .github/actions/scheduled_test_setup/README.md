# Scheduled Test Setup Action

A composite GitHub Action that installs security scanning tools (Syft and Grype) for use in workflows.

## Purpose

This action simplifies the setup of security scanning tools by providing a single reusable action that can be called from multiple workflows. Instead of repeating installation commands in every workflow, you can simply reference this action.

## What It Installs

- **[Syft](https://github.com/anchore/syft)**: SBOM (Software Bill of Materials) generation tool
- **[Grype](https://github.com/anchore/grype)**: Vulnerability scanner for container images and filesystems

## Usage

### Basic Usage

```yaml
steps:
  - name: Checkout code
    uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4

  - name: Setup Security Tools
    uses: orangitfi/platform-tooling/.github/actions/scheduled_test_setup@<current-sha>

  - name: Use the tools
    run: |
      syft --version
      grype --version
```

### In Security Scanning Workflows

```yaml
jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4

      - name: Setup Security Tools
        uses: orangitfi/platform-tooling/.github/actions/scheduled_test_setup@<current-sha>

      - name: Generate SBOM
        run: syft . -o json > sbom.json

      - name: Scan for vulnerabilities
        run: grype sbom:sbom.json --fail-on high
```

### With Other Actions

This action is designed to be used before other security scanning actions that require Syft and Grype:

```yaml
steps:
  - uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4

  - name: Setup Security Tools
    uses: orangitfi/platform-tooling/.github/actions/scheduled_test_setup@<current-sha>

  - name: Scan codebase
    uses: orangitfi/platform-tooling/.github/actions/security-scan-code@<current-sha>
    with:
      directory: "./src"
```

## When to Use

Use this action when you need to:

- Generate SBOMs with Syft
- Scan for vulnerabilities with Grype
- Run custom security scanning workflows
- Use security-scan-code or similar actions that depend on these tools

## Installation Details

Both tools are installed to `/usr/local/bin` using their official installation scripts:

- **Syft**: `curl -sSfL https://raw.githubusercontent.com/anchore/syft/main/install.sh | sh -s -- -b /usr/local/bin`
- **Grype**: `curl -sSfL https://raw.githubusercontent.com/anchore/grype/main/install.sh | sh -s -- -b /usr/local/bin`

## Inputs

This action has no inputs - it simply installs the tools.

## Outputs

This action has no outputs - it makes the tools available in the PATH for subsequent steps.

## Requirements

- Runs on: `ubuntu-latest` (or any Linux-based runner)
- Network access to download installation scripts from GitHub

## Example Workflows

### Full Security Scan

```yaml
name: Security Scan

on: [push, pull_request]

jobs:
  scan:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4

      - name: Setup Security Tools
        uses: orangitfi/platform-tooling/.github/actions/scheduled_test_setup@<current-sha>

      - name: Generate SBOM for repository
        run: syft . -o json > sbom.json

      - name: Scan SBOM for vulnerabilities
        run: grype sbom:sbom.json --only-fixed --fail-on high -o table

      - name: Upload SBOM
        uses: actions/upload-artifact@ea165f8d65b6e75b540449e92b4886f43607fa02 # v4
        with:
          name: sbom
          path: sbom.json
```

### Container Security Scan

```yaml
name: Container Scan

on: [push]

jobs:
  scan-image:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4

      - name: Build container
        run: docker build -t myapp:latest .

      - name: Setup Security Tools
        uses: orangitfi/platform-tooling/.github/actions/scheduled_test_setup@<current-sha>

      - name: Generate container SBOM
        run: syft myapp:latest -o json > container-sbom.json

      - name: Scan container
        run: grype sbom:container-sbom.json --fail-on critical
```

## Benefits

- **Reusability**: Define once, use in multiple workflows
- **Consistency**: Same tool versions across all workflows
- **Maintainability**: Update installation in one place
- **Simplicity**: Clean, readable workflow files

## Tool Versions

This action always installs the latest stable versions of Syft and Grype from their main installation scripts.

## Troubleshooting

### Installation Fails

If installation fails, check:

1. Runner has network access
2. GitHub.com is accessible
3. Installation scripts are available

### Tools Not Found After Installation

The tools are installed to `/usr/local/bin`, which should be in the PATH. If not found:

- Check runner type (must be Linux-based)
- Verify subsequent steps are in the same job

## References

- [Syft Documentation](https://github.com/anchore/syft)
- [Grype Documentation](https://github.com/anchore/grype)
- [Anchore Open Source Tools](https://anchore.com/opensource/)
