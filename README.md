# platform-tooling

Centralized reusable GitHub Actions workflows and composite actions for Node.js / React / Next.js and Python / uv repositories. Consuming repos call a single `uses:` line; this repository controls how every job runs.

**Consuming repo controls _when_ · platform-tooling controls _how_**

## Usage

There are two ways to use this repository:

**Option A — reference from the shared repo (recommended)**
Reference workflows and actions directly from this repository using the latest SHA from `main`. Always use the SHA shown in [Current SHA](#current-sha) — never use `@main`, as that resolves at runtime and bypasses pinning.

```yaml
jobs:
  ci:
    uses: orangitfi/platform-tooling/.github/workflows/node-ci.yml@<current-sha>
```

**Option B — copy to your own repo**
Copy the relevant workflow or action files into your repository and maintain them independently. This gives you full control but means you receive no updates automatically.

---

## Current SHA

```
36d580d22c46bd543824af243f4e37a95c808d38
```

Use this SHA when referencing any workflow or action from this repository:

```yaml
# Reusable workflow
jobs:
  ci:
    uses: orangitfi/platform-tooling/.github/workflows/node-ci.yml@36d580d22c46bd543824af243f4e37a95c808d38

# Composite action
steps:
  - uses: orangitfi/platform-tooling/.github/actions/slack-notify@36d580d22c46bd543824af243f4e37a95c808d38
```

### Bumping the SHA

Every `uses:` line inside this repository is tagged with a `# pt-sha` comment so they can be found and updated in one command. After committing changes run:

```bash
OLD=36d580d22c46bd543824af243f4e37a95c808d38
NEW=$(git rev-parse HEAD)
sed -i '' "s/${OLD}/${NEW}/g" README.md $(grep -rl "# pt-sha" .github/workflows/)
git add README.md .github/workflows/
git commit -m "chore: bump platform-tooling SHA pins to ${NEW}"
```

---

## Reusable Workflows

Located in `.github/workflows/`. All use `on: workflow_call` and never define their own triggers.

### Node.js / React / Next.js

| Workflow | Doc | Description |
|----------|-----|-------------|
| [`node-ci.yml`](.github/workflows/node-ci.yml) | [📄](.github/workflows/node-ci.md) | Full CI pipeline — security → lint + build + test (parallel) → vulnerability scan. Single `uses:` line replaces an entire CI file. |
| [`node-daily.yml`](.github/workflows/node-daily.yml) | [📄](.github/workflows/node-daily.md) | Nightly pipeline — runs the full CI pipeline and an OWASP ZAP DAST scan in parallel. |
| [`node-security-scan.yml`](.github/workflows/node-security-scan.yml) | [📄](.github/workflows/node-security-scan.md) | Runs gitleaks, npm audit, and guarddog in parallel. Intended as the first gate in any Node.js pipeline. |
| [`node-lint.yml`](.github/workflows/node-lint.yml) | [📄](.github/workflows/node-lint.md) | Runs npm lint and Docker lint (hadolint) in parallel. Docker lint is skipped cleanly when no Dockerfile is found. |
| [`node-build.yml`](.github/workflows/node-build.yml) | [📄](.github/workflows/node-build.md) | Installs dependencies with `npm ci` and runs the npm build script. |
| [`node-test.yml`](.github/workflows/node-test.yml) | [📄](.github/workflows/node-test.md) | Runs unit tests and optional Playwright e2e tests in parallel. Playwright report is uploaded as an artifact on failure. |
| [`node-vulnerability-scan.yml`](.github/workflows/node-vulnerability-scan.yml) | [📄](.github/workflows/node-vulnerability-scan.md) | Runs Syft + Grype vulnerability scans against the source code and the Docker image. Docker scan is optional. |
| [`node-build-and-publish-docker.yml`](.github/workflows/node-build-and-publish-docker.yml) | [📄](.github/workflows/node-build-and-publish-docker.md) | Builds a Docker image and optionally pushes it to GCP Artifact Registry. No push occurs when `publish` is false. |
| [`node-update-visual-snapshots.yml`](.github/workflows/node-update-visual-snapshots.yml) | [📄](.github/workflows/node-update-visual-snapshots.md) | Regenerates Playwright visual baseline screenshots and commits them back to the branch. Triggered manually via `workflow_dispatch`. |

### Python / uv

| Workflow | Doc | Description |
|----------|-----|-------------|
| [`python-ci.yml`](.github/workflows/python-ci.yml) | [📄](.github/workflows/python-ci.md) | Full CI pipeline — security → lint + test (parallel) → vulnerability scan. Single `uses:` line replaces an entire CI file. |
| [`python-daily.yml`](.github/workflows/python-daily.yml) | [📄](.github/workflows/python-daily.md) | Nightly pipeline — runs the full CI pipeline and an OWASP ZAP DAST scan in parallel. |
| [`python-security-scan.yml`](.github/workflows/python-security-scan.yml) | [📄](.github/workflows/python-security-scan.md) | Runs gitleaks, pip-audit, and guarddog in parallel. Intended as the first gate in any Python pipeline. |
| [`python-lint.yml`](.github/workflows/python-lint.yml) | [📄](.github/workflows/python-lint.md) | Runs ruff check + ruff format and Docker lint (hadolint) in parallel. Docker lint is skipped cleanly when no Dockerfile is found. |
| [`python-test.yml`](.github/workflows/python-test.yml) | [📄](.github/workflows/python-test.md) | Installs dependencies with `uv sync --frozen` and runs pytest. Python version is resolved from `pyproject.toml` automatically. |
| [`python-vulnerability-scan.yml`](.github/workflows/python-vulnerability-scan.yml) | [📄](.github/workflows/python-vulnerability-scan.md) | Runs Syft + Grype vulnerability scans against the source code and the Docker image. Docker scan is optional. |
| [`python-build-and-publish-docker.yml`](.github/workflows/python-build-and-publish-docker.yml) | [📄](.github/workflows/python-build-and-publish-docker.md) | Builds a Docker image and optionally pushes it to GCP Artifact Registry. Credentials are read from 1Password at runtime. |

### PHP / Symfony / Composer

| Workflow | Doc | Description |
|----------|-----|-------------|
| [`php-security-scan.yml`](.github/workflows/php-security-scan.yml) | [📄](.github/workflows/php-security-scan.md) | Runs gitleaks, composer-audit, and guarddog in parallel. Intended as the first gate in any PHP pipeline. |
| [`php-lint.yml`](.github/workflows/php-lint.yml) | [📄](.github/workflows/php-lint.md) | Runs PHP_CodeSniffer and PHPStan in parallel. Docker lint is skipped cleanly when no Dockerfile is found. |
| [`php-test.yml`](.github/workflows/php-test.yml) | [📄](.github/workflows/php-test.md) | Installs dependencies with `composer install` and runs PHPUnit. Covers unit tests only. |
| [`php-vulnerability-scan.yml`](.github/workflows/php-vulnerability-scan.yml) | [📄](.github/workflows/php-vulnerability-scan.md) | Runs Syft + Grype vulnerability scans against the source code and the Docker image. Docker scan is optional. |

### Shared

| Workflow | Doc | Description |
|----------|-----|-------------|
| [`dast-scan.yml`](.github/workflows/dast-scan.yml) | [📄](.github/workflows/dast-scan.md) | OWASP ZAP dynamic security scan against a live URL. Supports `baseline` (passive), `full` (active), and `api` (OpenAPI-aware) scan types. Skips cleanly when no URL is provided. |

---

## Composite Actions

Located in `.github/actions/`. Each action has its own `README.md` with full input/output documentation.

### Security

| Action | Description |
|--------|-------------|
| [`gitleaks-scan`](.github/actions/gitleaks-scan/README.md) | Installs gitleaks from a pinned release with SHA-256 verification and scans the repository for leaked secrets across the full git history. |
| [`npm-audit`](.github/actions/npm-audit/README.md) | Runs `npm audit` against the lockfile to detect known CVEs in npm dependencies. `NPM_CONFIG_IGNORE_SCRIPTS=true` prevents lifecycle scripts from running. |
| [`guarddog-npm-scan`](.github/actions/guarddog-npm-scan/README.md) | Runs guarddog against `package.json` to detect supply-chain threats (typosquatting, code injection, exfiltration) before any dependency is installed. |
| [`pip-audit`](.github/actions/pip-audit/README.md) | Exports the uv lockfile and runs pip-audit to detect known CVEs in Python dependencies before any package is installed. Requires `setup-uv`. |
| [`guarddog-scan`](.github/actions/guarddog-scan/README.md) | Exports the uv lockfile and runs guarddog to detect supply-chain threats in PyPI packages before any package is installed. Requires `setup-uv`. |
| [`security-scan-code`](.github/actions/security-scan-code/README.md) | Generates a Syft SBOM for a source directory and scans it with Grype. Requires `scheduled_test_setup`. |
| [`owasp-zap-scan`](.github/actions/owasp-zap-scan/README.md) | Runs an OWASP ZAP DAST scan against a live URL using a pinned Docker digest. Supports baseline, full, and api modes. Skips cleanly when no URL is provided. |

### Docker

| Action | Description |
|--------|-------------|
| [`docker-lint`](.github/actions/docker-lint/README.md) | Lints a Dockerfile with hadolint. |
| [`docker-scan`](.github/actions/docker-scan/README.md) | Builds a Docker image and scans it for vulnerabilities with Syft + Grype. Uploads the SBOM as a workflow artifact. |
| [`docker-build-push`](.github/actions/docker-build-push/README.md) | Builds a Docker image, runs a Syft + Grype vulnerability scan, and pushes to GCP Artifact Registry only if the scan passes. |

### Setup / Tooling

| Action | Description |
|--------|-------------|
| [`setup-uv`](.github/actions/setup-uv/README.md) | Installs uv (v0.11.3) from the official GitHub release with SHA-256 verification. Prerequisite for all Python composite actions and workflows. |
| [`scheduled_test_setup`](.github/actions/scheduled_test_setup/README.md) | Installs Syft and Grype on the runner. Prerequisite for `security-scan-code` and `docker-scan`. |

### Notifications / Publishing

| Action | Description |
|--------|-------------|
| [`slack-notify`](.github/actions/slack-notify/README.md) | Reads a Slack webhook URL from 1Password and posts a workflow status notification with repo, branch, commit, and run link. |
| [`publish-to-confluence`](.github/actions/publish-to-confluence/README.md) | Publishes a `docs/` folder of Markdown files to Confluence Cloud, preserving folder hierarchy as page hierarchy. |

---

## Security disclaimer

This repository is provided **as-is**, without warranty of any kind. The workflows and actions are internal tooling — they are not a security product and do not guarantee that consuming repositories are free of vulnerabilities.

Only the latest commit on `main` is maintained. There are no versioned releases and no backports. When a fix is committed, consuming repositories must update their pinned SHA to receive it. See [SECURITY.md](SECURITY.md) for the full policy.

---

## Design Principles

- **No third-party marketplace actions** — binaries are downloaded directly with SHA-256 verification. `actions/checkout`, `actions/upload-artifact`, and `actions/setup-node` (official GitHub org) are acceptable.
- **All secrets come from 1Password** — only `OP_SERVICE_ACCOUNT_TOKEN` is passed as a secret; all values are read via `op read` and masked with `::add-mask::` before use.
- **Tight version pinning** — SHA pins on all external actions; versioned and checksum-verified binaries.
- **`fail-on-findings` defaults to `true`** on all security actions but is overridable per call site.
- **Consuming repo controls _when_, platform-tooling controls _how_** — no triggers (`push`, `pull_request`) are defined in this repository.
