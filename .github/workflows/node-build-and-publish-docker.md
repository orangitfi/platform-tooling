# node-build-and-publish-docker

Reusable workflow that builds a Docker image and optionally pushes it to GCP Artifact Registry. Credentials are read from 1Password — only `OP_SERVICE_ACCOUNT_TOKEN` is passed as a secret; everything else is fetched and masked at runtime.

> Replace `<current-sha>` with the current SHA from the [root README](../../README.md#current-sha).

## Usage

### Build only — verify the Dockerfile compiles (e.g. on pull requests)

```yaml
on: [pull_request]

jobs:
  docker-build:
    uses: orangitfi/platform-tooling/.github/workflows/node-build-and-publish-docker.yml@<current-sha>
    with:
      image-name: my-app
```

### Build and publish — push to Artifact Registry (e.g. on merge to main)

```yaml
on:
  push:
    branches: [main]

jobs:
  docker-publish:
    uses: orangitfi/platform-tooling/.github/workflows/node-build-and-publish-docker.yml@<current-sha>
    with:
      image-name:        my-app
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
    uses: orangitfi/platform-tooling/.github/workflows/node-build-and-publish-docker.yml@<current-sha>
    with:
      image-name:        my-app
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
1. Validates that no publish-required inputs are set (validation is skipped)
2. Builds the Docker image locally with a `git-<sha>-build` tag
3. Cleans up the local image

**When `publish: true`**:
1. Validates that `project-id`, `registry-repo`, and `gcp-sa-key-op-ref` are provided
2. Reads the GCP service account key from 1Password and masks it immediately
3. Logs in to Artifact Registry using the key
4. Builds the Docker image
5. Tags and pushes both `git-<sha>` (pinned) and `latest`
6. Logs out from the registry
7. Cleans up all local images

## When it has value

- **Same workflow, two modes**: by toggling `publish` on your main branch condition, you get a unified Dockerfile validation on PRs and a full build + push on merge — one workflow definition to maintain
- **Immutable image tags**: `git-<sha>` tags make every pushed image traceable back to the exact commit. You can redeploy any previous version by its SHA tag
- **1Password integration**: the GCP SA key never lives in GitHub Secrets — it is fetched at runtime and masked before use, so it cannot be extracted from logs

## Tips

- The `publish: ${{ github.ref == 'refs/heads/main' }}` pattern lets you reuse the same `with:` block across PR and merge events — only the push changes.
- Local images are cleaned up in an `if: always()` step so a failed scan or push does not leave dangling images on the runner.
- If the `gcp-sa-key-op-ref` value resolves to an empty string (e.g. the 1Password item does not exist), the workflow fails with a clear error before attempting to authenticate.
- To push to a different registry (e.g. Docker Hub), this workflow is not the right tool — it is GCP-specific. Raise a PR to make the registry configurable.
