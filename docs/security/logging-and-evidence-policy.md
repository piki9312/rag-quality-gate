# Logging And Evidence Policy

## Purpose

Proof Gate / RAG Quality Gate reports are often reviewed outside the developer's local machine. Logs, reports, and workflow artifacts must not expose customer data, API keys, local paths, CI workspace paths, or internal directory structure.

This policy defines what data can be handled in GitHub Actions and what each report mode means.

## GitHub Actions Data Boundary

GitHub Actions may handle only:

- sample, mock, dummy, or synthetic documents
- sample, mock, dummy, or synthetic cases
- aggregate metadata such as counts, pass rates, severity mix, policy status, and failure category totals
- redacted examples that cannot identify a real customer, employee, user, tenant, repository secret, or internal system

GitHub Actions must not handle:

- real customer documents
- production RAG answers from customer systems
- real user questions or tickets
- API keys, tokens, credentials, or secret-derived values
- local absolute paths such as `C:\...`, `/Users/...`, or `/home/...`
- CI workspace paths such as `/home/runner/work/...`
- unredacted full report artifacts containing customer text

## Report Modes

### `ci`

`ci` mode is for GitHub Actions and other shared automation.

Allowed content:

- mock/sample/dummy inputs
- aggregate metrics
- schema validation results
- redacted failure summaries
- artifact filenames and relative paths only

Disallowed content:

- full prompts, full answers, full retrieved chunks, or full evidence text from real customer runs
- any secret, credential, token, or internal absolute path

### `redacted`

`redacted` mode is for reviewable artifacts that may leave the local operator environment but still need some diagnostic context.

Allowed content:

- aggregate metrics
- case IDs
- severity, risk domain, eval mode, and pass/fail state
- redacted question/answer/evidence snippets when needed for debugging
- relative artifact references

Disallowed content:

- secrets
- customer-identifying text
- local or CI absolute paths
- raw full retrieved evidence from customer documents

### `full`

`full` mode is for trusted local operator use only.

Allowed content:

- full questions
- full answers
- full retrieved evidence
- detailed case-level diagnostics

Restrictions:

- `full` mode must not run when `GITHUB_ACTIONS=true`.
- `full` mode artifacts must not be uploaded from CI.
- `full` mode artifacts must not be included in customer-facing bundles unless the customer has explicitly approved the exact content.

## `GITHUB_ACTIONS=true` Rule

When `GITHUB_ACTIONS=true`, report generation and artifact upload must behave as CI-safe output.

Required behavior:

- treat the environment as `ci` mode unless an explicit safer mode exists
- reject or downgrade `full` report mode
- avoid local absolute paths and CI workspace paths in JSON, Markdown, logs, and artifact names
- upload only allowlisted artifacts

`full` mode in GitHub Actions is prohibited even for private repositories.

## Artifact Upload Allowlist

GitHub Actions should upload only artifacts that are safe by construction.

Default allowlist:

- schema validation summaries
- test result summaries
- coverage summaries without source snippets containing customer data
- redacted gate summaries
- aggregate `gate-report.json` variants that contain only relative artifact paths and aggregate metadata
- sample/mock/demo reports generated from committed sample data

Default denylist:

- raw evaluation logs from real customer runs
- full `gate-report.md` or `gate-report.json` generated from customer data
- raw `QARunRecord` JSONL from customer runs
- retrieved document chunks
- adapter request/response dumps
- files under temporary internal directories such as `.tmp`
- files containing absolute local or CI workspace paths

When a new artifact type is introduced, it must be reviewed against this policy before being added to the allowlist.

## Evidence Handling

Evidence fields should be treated as sensitive by default. Even when evidence comes from internal policy or FAQ material, it may contain customer-specific wording, employee data, private process details, or regulated information.

CI-safe outputs should prefer:

- evidence IDs
- source document IDs
- aggregate evidence recall metrics
- redacted snippets only when necessary

CI-safe outputs should avoid:

- full retrieved chunks
- full source documents
- raw adapter payloads
- raw model prompts containing embedded evidence

## Review Checklist

Before merging changes that affect logs, reports, CI, or artifact upload, verify:

- GitHub Actions uses only sample/mock/dummy data or aggregate metadata.
- `GITHUB_ACTIONS=true` cannot produce or upload full reports.
- JSON and Markdown reports do not contain local absolute paths or CI workspace paths.
- Artifact uploads are allowlisted.
- New fields do not expose secrets, customer text, or internal directory structure.
