# Security Scan GitHub Action

This GitHub Action performs security scanning on your codebase using Syft and Grype. It generates a Software Bill of Materials (SBOM) and then runs a security vulnerability scan against it.

## Features

- Generates a Software Bill of Materials (SBOM) using Syft
- Performs security vulnerability scanning using Grype
- Fails the workflow if high-severity vulnerabilities are found
- Only reports vulnerabilities that have available fixes

## Usage

```yaml
- name: Security Scan
  uses: orangitfi/platform-tooling/.github/actions/security-scan-code@<current-sha>
  with:
    directory: '.'  # The directory to scan
```

## Inputs

| Input | Required | Description |
|-------|----------|-------------|
| `directory` | Yes | The directory path to scan for security vulnerabilities |

## What it does

1. Checks out your repository code
2. Generates an SBOM (Software Bill of Materials) using Syft in JSON format
3. Runs Grype to scan for security vulnerabilities:
   - Only reports vulnerabilities that have available fixes (`--only-fixed`)
   - Fails the workflow if high-severity vulnerabilities are found (`--fail-on high`)

## Requirements

This action requires Syft and Grype to be available in the GitHub Actions runner environment. Make sure these tools are installed before running the action.

## Output

- Generates `sbom.json` in the specified directory
- Provides security scan results in the GitHub Actions logs
- Fails the workflow if high-severity vulnerabilities are found 
