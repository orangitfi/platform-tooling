# Docker Security Scan Action

A GitHub Action that builds a Docker image and scans it for security vulnerabilities using [Grype](https://github.com/anchore/grype) and generates a Software Bill of Materials (SBOM) using [Syft](https://github.com/anchore/syft).

## Features

- 🔨 **Build Docker Image**: Builds your Docker image locally
- 📋 **SBOM Generation**: Creates multiple SBOM formats (JSON, SPDX, CycloneDX) using Syft
- 🔍 **Vulnerability Scanning**: Scans for security vulnerabilities using Grype
- � **Artifact Upload**: Saves SBOM as workflow artifacts
- ⚙️ **Configurable Severity**: Choose minimum severity level to fail the build
- 🧹 **Automatic Cleanup**: Removes temporary files and images after scan

## Inputs

### Required

| Input               | Description                                                 | Example                                |
| ------------------- | ----------------------------------------------------------- | -------------------------------------- |
| `working-directory` | Path to the directory containing Dockerfile and source code | `.` or `./backend`                     |
| `dockerfile-path`   | Relative path to the Dockerfile (from working directory)    | `./Dockerfile`                         |
| `image-name`        | Name of the Docker image (local only, not pushed)           | `myapp`                                |
| `image-tag`         | Docker image tag                                            | `latest`, `1.0.0`, `${{ github.sha }}` |

### Optional

| Input              | Description                                                                                            | Default |
| ------------------ | ------------------------------------------------------------------------------------------------------ | ------- |
| `fail-on-severity` | Fail on vulnerabilities of this severity or higher (`critical`, `high`, `medium`, `low`, `negligible`) | `high`  |

## Outputs

| Output                  | Description                                     |
| ----------------------- | ----------------------------------------------- |
| `scan-result`           | Result of the security scan (`passed`/`failed`) |
| `vulnerabilities-found` | Number of vulnerabilities found                 |

## Usage Examples

### Basic Usage

```yaml
name: Container Security Scan

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Scan Docker image
        uses: orangitfi/platform-tooling/.github/actions/docker-scan@<current-sha>
        with:
          working-directory: "."
          dockerfile-path: "./Dockerfile"
          image-name: "myapp"
          image-tag: ${{ github.sha }}
```

### Advanced Usage with Custom Settings

```yaml
name: Container Security Scan

on:
  pull_request:
  push:
    branches: [main, develop]

jobs:
  security-scan:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v4

      - name: Scan Docker image
        uses: orangitfi/platform-tooling/.github/actions/docker-scan@<current-sha>
        with:
          working-directory: "./backend"
          dockerfile-path: "./Dockerfile"
          image-name: "backend-service"
          image-tag: ${{ github.sha }}
          fail-on-severity: "critical" # Only fail on critical vulnerabilities
          upload-sarif: "true"
```

### Multiple Images

```yaml
name: Multi-Image Security Scan

on:
  pull_request:
    branches: [main]

jobs:
  scan-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: orangitfi/platform-tooling/.github/actions/docker-scan@<current-sha>
        with:
          working-directory: "./frontend"
          dockerfile-path: "./Dockerfile"
          image-name: "frontend"
          image-tag: ${{ github.sha }}

  scan-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: orangitfi/platform-tooling/.github/actions/docker-scan@<current-sha>
        with:
          working-directory: "./backend"
          dockerfile-path: "./Dockerfile"
          image-name: "backend"
          image-tag: ${{ github.sha }}
```

## What Gets Scanned

Grype scans for vulnerabilities in:

- Operating system packages (APK, DEB, RPM, etc.)
- Language-specific packages (npm, pip, gem, maven, etc.)
- Application dependencies
- Base image vulnerabilities

## SBOM Formats Generated

The action generates three SBOM formats:

- **JSON**: Native Syft format
- **SPDX-JSON**: Software Package Data Exchange format
- **CycloneDX-JSON**: CycloneDX format for supply chain security

All SBOM files are uploaded as workflow artifacts and retained for 90 days.

## Artifacts

The action uploads SBOM artifacts in multiple formats:

- **JSON**: Native Syft format
- **SPDX-JSON**: Software Package Data Exchange format
- **CycloneDX-JSON**: CycloneDX format for supply chain security

Artifacts are retained for 90 days and can be downloaded from the workflow run.

## Severity Levels

Grype supports the following severity levels:

- `critical`: Only critical vulnerabilities fail the build
- `high`: High and critical vulnerabilities fail the build
- `medium`: Medium, high, and critical vulnerabilities fail the build
- `low`: Low, medium, high, and critical vulnerabilities fail the build
- `negligible`: All vulnerabilities fail the build

## Best Practices

1. **Run on Pull Requests**: Catch vulnerabilities before they reach main branch
2. **Fail on High Severity**: Use `fail-on-severity: high` as a good balance
3. **Review Scan Logs**: Check workflow logs for vulnerability details
4. **Keep Base Images Updated**: Use recent base images to minimize vulnerabilities
5. **Use Multi-Stage Builds**: Reduce attack surface by minimizing image contents
6. **Download SBOM Artifacts**: Review generated SBOMs for supply chain visibility

## Troubleshooting

### Action Fails Due to Vulnerabilities

If the scan fails due to vulnerabilities:

1. Check the workflow logs for detailed vulnerability information
2. Update dependencies or base images to versions with fixes
3. Review SBOM artifacts to understand dependencies
4. If needed, temporarily lower `fail-on-severity` while fixing issues

### Large Image Scan Times

Scanning large images can take time. Consider:

- Using multi-stage builds to reduce image size
- Caching Docker layers
- Running scans less frequently (e.g., on main branch only)

## References

- [Grype Documentation](https://github.com/anchore/grype)
- [Syft Documentation](https://github.com/anchore/syft)
- [GitHub Code Scanning](https://docs.github.com/en/code-security/code-scanning)
- [SARIF Format](https://sarifweb.azurewebsites.net/)
