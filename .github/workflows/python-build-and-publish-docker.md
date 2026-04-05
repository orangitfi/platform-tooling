# python-build-and-publish-docker

Reusable workflow that builds a Docker image from a Python / uv project and optionally pushes it to GCP Artifact Registry. Credentials are read from 1Password — only `OP_SERVICE_ACCOUNT_TOKEN` is passed as a secret; everything else is fetched and masked at runtime.

> Replace `<current-sha>` with the current SHA from the [root README](../../README.md#current-sha).

## Usage

### Build only — verify the Dockerfile compiles (e.g. on pull requests)

```yaml
on: [pull_request]

jobs:
  docker-build:
    uses: orangitfi/platform-tooling/.github/workflows/python-build-and-publish-docker.yml@<current-sha>
    with:
      image-name: my-api
```

### Build and publish — push to Artifact Registry (e.g. on merge to main)

```yaml
on:
  push:
    branches: [main]

jobs:
  docker-publish:
    uses: orangitfi/platform-tooling/.github/workflows/python-build-and-publish-docker.yml@<current-sha>
    with:
      image-name:        my-api
      project-id:        my-gcp-project
      registry-repo:     my-repo
      gcp-sa-key-op-ref: op://my-vault/gcp-sa/service-account-key
      publish:           true
    secrets:
      op-service-account-token: ${{ secrets.OP_SERVICE_ACCOUNT_TOKEN }}
```

### Full pipeline: PR builds, main publishes

```yaml
jobs:
  docker:
    uses: orangitfi/platform-tooling/.github/workflows/python-build-and-publish-docker.yml@<current-sha>
    with:
      image-name:        my-api
      project-id:        my-gcp-project
      registry-repo:     my-repo
      gcp-sa-key-op-ref: op://my-vault/gcp-sa/service-account-key
      publish:           ${{ github.ref == 'refs/heads/main' }}
    secrets:
      op-service-account-token: ${{ secrets.OP_SERVICE_ACCOUNT_TOKEN }}
```

## Parameters

| Input | Default | Description |
|-------|---------|-------------|
| `image-name` | **required** | Image name without registry prefix or tag |
| `working-directory` | `.` | Docker build context directory |
| `dockerfile-path` | `Dockerfile` | Path to the Dockerfile relative to `working-directory` |
| `region` | `europe-north1` | GCP region of the Artifact Registry |
| `project-id` | — | GCP project ID — required when `publish: true` |
| `registry-repo` | — | Artifact Registry repository name — required when `publish: true` |
| `gcp-sa-key-op-ref` | — | 1Password reference to the GCP SA key JSON — required when `publish: true` |
| `publish` | `false` | Push the image to Artifact Registry after a successful build |

| Secret | Description |
|--------|-------------|
| `op-service-account-token` | 1Password service account token — required when `publish: true` |

## What it does

**When `publish: false`** (default):
1. Builds the Docker image locally with a `git-<sha>-build` tag
2. Cleans up the local image

**When `publish: true`**:
1. Validates that `project-id`, `registry-repo`, and `gcp-sa-key-op-ref` are all provided
2. Reads the GCP service account key from 1Password and masks it immediately with `::add-mask::`
3. Logs in to Artifact Registry
4. Builds the Docker image
5. Tags and pushes both `git-<sha>` (pinned, immutable) and `latest`
6. Logs out from the registry
7. Cleans up all local images

## When it has value

- **Unified Dockerfile validation**: the same workflow validates the Dockerfile on PRs (build only) and publishes on merge — one definition to maintain
- **Immutable image tags**: `git-<sha>` tags make every pushed image fully traceable back to the exact commit. You can redeploy any version by its SHA tag without guessing
- **1Password integration**: the GCP SA key is never stored in GitHub Secrets — it is fetched at runtime and masked before use, invisible in logs

## Tips

- The `publish: ${{ github.ref == 'refs/heads/main' }}` pattern is the recommended way to enable push only on the main branch while reusing the same `with:` block.
- For FastAPI / Django projects, ensure the Dockerfile does `uv sync --frozen` (not `pip install -r requirements.txt`) so the Docker image also uses the committed lockfile.
- Images are cleaned up in an `if: always()` step so a failed scan or push never leaves dangling images on the runner.
- The `gcp-sa-key-op-ref` follows the 1Password CLI secret reference format: `op://<vault>/<item>/<field>`. Example: `op://ci-secrets/gcp-artifact-registry/service-account-key`.
