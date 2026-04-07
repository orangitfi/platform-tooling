# Slack Notify

Composite action that reads a Slack webhook URL from 1Password and posts a workflow status notification.

Workflow name, repository, branch, commit SHA, and a link to the run are populated automatically from the GitHub environment. The caller only needs to pass in the status and optionally a custom message.

## Usage

The action expects `OP_SERVICE_ACCOUNT_TOKEN` to be set in the calling step's `env`. All values fetched from 1Password are masked before use.

> Replace `<current-sha>` with the current SHA from the [root README](../../../README.md#current-sha).

### Notify at the end of a workflow

```yaml
jobs:
  build:
    # ... your jobs ...

  notify:
    name: Notify Slack
    runs-on: ubuntu-latest
    needs: [build, test, deploy]
    if: always()
    steps:
      - uses: actions/checkout@34e114876b0b11c390a56381ad16ebd13914f8d5 # v4

      - uses: orangitfi/platform-tooling/.github/actions/slack-notify@<current-sha>
        env:
          OP_SERVICE_ACCOUNT_TOKEN: ${{ secrets.OP_SERVICE_ACCOUNT_TOKEN }}
        with:
          slack-webhook-op-ref: op://my-vault/slack/webhook-url
          status: ${{ contains(needs.*.result, 'failure') && 'failure' || contains(needs.*.result, 'cancelled') && 'cancelled' || 'success' }}
```

### With an optional custom message

```yaml
      - uses: orangitfi/platform-tooling/.github/actions/slack-notify@<current-sha>
        env:
          OP_SERVICE_ACCOUNT_TOKEN: ${{ secrets.OP_SERVICE_ACCOUNT_TOKEN }}
        with:
          slack-webhook-op-ref: op://my-vault/slack/webhook-url
          status: ${{ job.status }}
          message: "Deployed version `${{ github.sha }}` to production"
```

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `slack-webhook-op-ref` | Yes | — | 1Password reference to the Slack webhook URL |
| `status` | Yes | — | Workflow status: `success`, `failure`, or `cancelled` |
| `message` | No | `""` | Optional extra text (e.g. deploy version, PR title) |

## Status colours

| Status | Emoji | Sidebar colour |
|--------|-------|---------------|
| `success` | ✅ | Green |
| `failure` | ❌ | Red |
| `cancelled` | ⚠️ | Yellow |
| anything else | ℹ️ | Grey |

## What the notification contains

- Status emoji and workflow name
- Repository (linked to GitHub)
- Branch name
- Short commit SHA
- Optional custom message (only shown when provided)
- **View Run** button linking to the GitHub Actions run

## How status is passed in

Composite actions cannot read `job.status` themselves. The calling workflow must pass it explicitly.

**Single job** — pass the job's own status:
```yaml
status: ${{ job.status }}
```

**Multiple jobs** — aggregate from `needs` context (run in a final `notify` job with `if: always()`):
```yaml
status: ${{ contains(needs.*.result, 'failure') && 'failure' || contains(needs.*.result, 'cancelled') && 'cancelled' || 'success' }}
```

## Requirements

- `jq` must be available on the runner. It is pre-installed on all GitHub-hosted runners.
- `curl` must be available. It is pre-installed on all GitHub-hosted runners.
- `OP_SERVICE_ACCOUNT_TOKEN` must be set in the step environment.
