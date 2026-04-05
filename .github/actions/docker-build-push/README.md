# Docker Build & Push

Composite action that builds a Docker image, scans it for vulnerabilities with Syft + Grype, and pushes it to GCP Artifact Registry. The scan must pass before the image is pushed — a vulnerable image is never promoted.

> **Note:** This action assumes the caller has already authenticated to Artifact Registry (e.g. via `docker login` with a GCP service account key). Authentication is intentionally kept outside this action so it can be managed centrally in the calling workflow.

## Usage

> Replace `<current-sha>` with the current SHA from the [root README](../../../README.md#current-sha).

```yaml
jobs:
  build-and-push:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      # Authenticate to Artifact Registry first (example using a key file)
      - name: Log in to Artifact Registry
        run: |
          echo "$GCP_SA_KEY" | docker login \
            -u _json_key --password-stdin \
            https://europe-north1-docker.pkg.dev
        env:
          GCP_SA_KEY: ${{ secrets.GCP_SA_KEY }}

      - uses: orangitfi/platform-tooling/.github/actions/docker-build-push@<current-sha>
        with:
          project_id: my-gcp-project
          sha:        ${{ github.sha }}
```

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `project_id` | **Yes** | — | GCP project ID |
| `sha` | **Yes** | — | Git commit SHA used for the pinned image tag |
| `region` | No | `europe-north1` | GCP region of the Artifact Registry |
| `image_name` | No | `invoicing-migrator` | Image name without registry prefix or tag |
| `registry_repo` | No | `invoicing-migrator` | Artifact Registry repository name |
| `context` | No | `src/sevendos_invoicing_migrator` | Docker build context path relative to repo root |

## What it does

1. Computes image tag variables: `IMAGE_SHA` (`git-<sha>`), `IMAGE_LATEST`, `IMAGE_TEST` (`git-<sha>-test`)
2. Builds the Docker image using the test tag
3. Installs Syft (SBOM generation) and Grype (vulnerability scanning)
4. Generates an SBOM for the built image
5. Scans the SBOM with Grype — fails on `high` or above severity with a fix available
6. On scan success: tags and pushes both `git-<sha>` and `latest` to Artifact Registry
7. Cleans up the test image and SBOM file

## When it has value

- Enforcing a **scan-before-push** gate: the image is never pushed to the registry if it contains known exploitable vulnerabilities, eliminating a class of "ship it and fix later" risk
- **Audit trail**: every pushed image has a `git-<sha>` tag, so you can trace any registry image back to the exact commit that produced it
- **Release pipelines** that deploy directly from Artifact Registry can trust that all images in the registry have passed at least a baseline vulnerability check

## Tips

- The action currently hard-fails on `high` severity vulnerabilities that have a fix available (`--only-fixed --fail-on high`). This avoids noise from unfixable vulnerabilities in base images. If you need a different threshold, fork the action or raise a PR to make `fail-on-severity` an input.
- Keep the `IMAGE_TEST` tag distinct from `IMAGE_SHA` so that a partially-built or unscanned image is never confused with a production tag.
- If the Grype scan fails, download the `sbom.json` artifact (or check logs) to see which CVEs blocked the push. Updating the base image in your Dockerfile often resolves the majority of findings.

## Version pinning

Grype is pinned to **v0.109.0** with SHA-256 verification. Syft is pinned via the `anchore/sbom-action` action at a specific commit SHA. To upgrade either tool, update the version and checksum in `action.yml`.
