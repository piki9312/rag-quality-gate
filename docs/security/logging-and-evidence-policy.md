# Logging And Evidence Policy

## Purpose

Proof Gate / RAG Quality Gate reports are often reviewed outside the developer's local machine. Logs, reports, and workflow artifacts must not expose customer data, API keys, local paths, CI workspace paths, or internal directory structure.

This policy defines what data can be handled in GitHub Actions and what each report mode means. Sanitizers are defense-in-depth; they are not a reason to place real customer data on GitHub-hosted runners.

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

## `change-event.yml` Data Boundary

`change-event.yml` は release review の補助入力ですが、顧客名、実在文書名、社内パス、target_release、customer-specific summary を入れすぎると、そのまま高リスク metadata になります。

Required handling:

- `change-event.yml` には bounded な ID、version、hash、category、retest reason だけを優先して書く
- CI-safe artifact には raw asset name / raw document name / path / target_release / customer-specific summary を出さない
- safe 版では hash / count / bounded metadata のみを扱う
- full change metadata は local / private runner / customer-controlled 環境のみで扱う
- sanitizer を前提にせず、入力時点で最小情報にする

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

- `gate-report-ci.md`
- `gate-report-ci.json`
- CI-safe `gate-decision.json`
- CI-safe `gate-history-summary.json`
- schema validation summaries generated from sample/mock/dummy data
- test result summaries and coverage summaries without customer source snippets
- sample/mock/demo reports generated from committed sample data

Default denylist:

- raw evaluation logs from real customer runs
- full `gate-report.md` or `gate-report.json` generated from customer data
- raw `QARunRecord` JSONL from customer runs
- `gate-decisions.jsonl`
- `index/meta.json`
- `faiss.index`
- retrieved document chunks
- adapter request/response dumps
- raw connection validation payloads or real customer endpoint URLs
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

## Connection Validation

GitHub-hosted CI must not validate real customer RAG endpoints. Connection validation in GitHub Actions is limited to dummy/sample endpoints or fully sanitized diagnostics. Customer PoC `external_real` runs should execute locally, on a private runner, or in a customer-controlled environment.

`connection-validation.json` must not contain raw endpoint URLs, query text, token values, raw response bodies, retrieved evidence, source paths, or tenant/customer identifiers.

## Notifications And Issue Comments

GitHub issue comments, Slack messages, Teams messages, and webhook payloads from CI must use safe summaries only. They may include gate status, policy status, aggregate pass rates, S1 failure counts, reason codes, run IDs, and safe artifact filenames. They must not include customer/app/tenant names, endpoints, source documents, raw questions, answers, expected answers, evidence text, owner/steward names, internal paths, or token-like strings.

## Review Checklist

Before merging changes that affect logs, reports, CI, or artifact upload, verify:

- GitHub Actions uses only sample/mock/dummy data or aggregate metadata.
- `GITHUB_ACTIONS=true` cannot produce or upload full reports.
- JSON and Markdown reports do not contain local absolute paths or CI workspace paths.
- Artifact uploads are allowlisted.
- New fields do not expose secrets, customer text, or internal directory structure.
