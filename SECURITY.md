# Security Policy

## Supported versions

Only the latest commit on `main` is maintained. There are no versioned releases, no stable branches, and no backports. If a vulnerability is found in a workflow or action, a fix will be committed to `main`. Consuming repositories are responsible for updating their pinned SHA to pick up the fix.

No hotfixes are issued for older commits. There is no support for pinned SHAs that are no longer at HEAD.

## No warranty

This repository is provided **as-is**, without warranty of any kind. The workflows and actions are internal tooling. They are not a security product and do not guarantee that consuming repositories are free of vulnerabilities. Security scan results (gitleaks, npm audit, guarddog, pip-audit, Grype, ZAP) reflect the state of the scanned artefacts at the time of the run and the completeness of the underlying tool databases — not a certification of security.

## Reporting a vulnerability

If you identify a security issue in this repository's own code (a workflow, composite action, or script), report it by emailing **admin@orangit.fi**. Do not open a public GitHub issue.

Include:

- Which file or action is affected
- A description of the issue and how it could be exploited
- The commit SHA where the issue is present

We will review the report and commit a fix to `main` on a best-effort basis. There are no guaranteed response times or disclosure timelines.
