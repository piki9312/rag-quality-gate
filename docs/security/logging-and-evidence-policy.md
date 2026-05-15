# Logging and Evidence Policy

## Purpose

Define safe handling for Proof Gate logs, reports, evidence, CI artifacts, and external RAG error information.

Proof Gate may handle customer documents, AI answers, expected answers, retrieved evidence, external RAG endpoints, and operational metadata. These fields are sensitive by default. This policy defines what data can be handled in GitHub Actions and what each report mode means. Sanitizers are defense-in-depth; they are not a reason to place real customer data on GitHub-hosted runners.

`ci` mode and sanitizer behavior reduce exposure risk. They do not guarantee that every possible secret, customer phrase, or private detail has been removed. Treat GitHub-hosted Actions as safe-metadata-only even when sanitizers are enabled.

## Core Principles

- GitHub Actions on GitHub-hosted runners must use sample/mock/dummy data only.
- Customer confidential data must not be processed on GitHub-hosted runners.
- Full reports with raw questions, expected answers, AI answers, retrieved evidence, or chunk text are allowed only in local, private runner, or customer-controlled environments.
- CI artifacts must contain only safe summaries.
- GitHub-hosted CI must not upload full evidence, vector indexes, raw JSONL logs, or full report bundles.
- Secrets must never be printed to stdout, logs, reports, GitHub Issues, Slack notifications, or artifacts.
- Sanitizers are a final guardrail, not a DLP system or permission to process customer confidential data in GitHub-hosted CI.

## Report Modes

### ci

Use `ci` mode for GitHub Actions and automated CI.

`ci` mode emits safe summary only.

Allowed:

- gate status
- policy_status
- pass rate
- S1 failed count
- fixed-taxonomy reason_code / failure_type
- safe artifact path
- safe gate-decision summary
- safe history summary

Forbidden:

- question
- expected_answer
- answer / ai_answer
- retrieved_evidence
- chunk_text
- source_path
- free-form failure reason
- customer-derived reason category
- raw endpoint
- token
- full markdown report
- full gate-report.json
- JSONL logs
- faiss.index
- index/meta.json

### redacted

Use `redacted` mode for customer sharing and review when the report structure is useful but text bodies are not safe to expose.

Policy:

- structure is preserved
- sensitive text fields are replaced with `[REDACTED]`
- metadata such as `answer_present` and `answer_hash` is allowed
- relative safe artifact paths are allowed
- secrets, raw endpoint values, raw evidence text, and raw customer documents are forbidden

### full

Use `full` mode only in local, private runner, or customer-controlled environments.

Full mode may include raw evidence and full answer traces.

Restrictions:

- GitHub Actions with `GITHUB_ACTIONS=true` must fail immediately if `--report-mode full` is requested.
- The error message must clearly say full reports are local/private runner only.
- Full mode artifacts must not be uploaded from GitHub-hosted CI.
- Full reports must not be attached to GitHub Issues, Slack notifications, or shared artifacts unless the customer-controlled environment and agreement explicitly allow it.

## GitHub Actions Policy

- GitHub-hosted Actions must not process customer production data.
- GitHub Actions should use mock/local/demo data by default.
- External RAG gates in Actions must use staging/test/read-only endpoints only.
- Full artifacts are forbidden in Actions.
- Artifacts must be uploaded by allowlist, not by uploading the whole `log_dir`.
- Workflow outputs should prefer status, aggregate metrics, and safe relative artifact paths.
- CI-safe outputs should use aggregate values and fixed taxonomy reason codes. They must not pass through customer-derived categories or free-form failure text.

## Artifact Allowlist

Allowed:

- `gate-report-ci.md`
- `gate-report-ci.json`
- CI-safe `gate-decision.json`
- CI-safe `gate-history-summary.json`
- safe `pack-validation.json`
- safe `connection-validation.json`
- schema validation summaries generated from sample/mock/dummy data
- test result summaries and coverage summaries without customer source snippets
- sample/mock/demo reports generated from committed sample data

Forbidden:

- `*.jsonl`
- full gate-report.json
- full gate-report.md
- index/meta.json
- faiss.index
- raw retrieved evidence
- raw external RAG response body
- raw customer documents
- raw `cases.csv`
- raw `gate.yml`
- raw `quality-pack.yml`
- whole `log_dir` uploads

New artifact types must be reviewed against this policy before being added to any workflow upload list.

## Stdout Policy

`ci` mode stdout must include only:

- gate status
- policy_status
- overall pass rate
- S1 failed count
- fixed-taxonomy reason_code / failure_type
- safe artifact path

`ci` stdout must not include:

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
- question
- expected_answer
- answer
- ai_answer
- retrieved_evidence
- chunk_text
- source_path
- free-form failure reason
- customer-derived reason category
- endpoint
- token-like strings

## Reason Code Policy

CI-safe reports, stdout, notification payloads, and gate-decision artifacts must use a fixed taxonomy for reason codes and failure categories.

Allowed examples:

- `s1_case_failed`
- `s2_case_failed`
- `overall_threshold_not_met`
- `expected_evidence_recall_below_threshold`
- `keyword_match_below_threshold`
- `answer_quality_below_threshold`
- `judge_fallback_used`
- `judge_unavailable`
- `needs_human_review`
- `configuration_error`
- `evaluation_error`
- `unknown_failure`

Free-form or customer-specific values must not be normalized and passed through. For example, a raw category such as `ACME special refund`, `VIP cancellation exception`, or an internal plan name must be mapped to `unknown_failure` or another approved taxonomy code in CI-safe outputs.

## External RAG Error Policy

- 4xx/5xx response body must not be logged directly.
- Error output should include `status_code`, `reason_code`, request ID/hash if available, and sanitized issue type.
- Raw external error bodies are forbidden in stdout, JSON report, Slack, GitHub Issue payload, and CI artifacts.
- Connection validation reports should expose only safe status, reason code, timing, and redacted diagnostics.

## JSONL Policy

- `ci` / `redacted` mode must not persist raw `QARunRecord.answer`.
- Instead use:
  - `answer_hash`
  - `answer_present: true`
  - `answer_redacted: true`
- `full` mode may persist raw answer only in local/private/customer-controlled environments.
- Raw JSONL logs from real customer runs must not be uploaded as GitHub Actions artifacts.

## Notifications Policy

- Slack notifications and GitHub Issue payloads must use safe summaries only.
- They must not include raw question, answer, expected_answer, evidence text, chunk text, source path, endpoint, or tokens.
- Notifications should link to safe summaries or customer-controlled review locations, not raw evidence bundles.

## Retention and Deletion

- CI safe artifacts: short retention, recommended 7 days.
- Weekly/monthly safe summaries: 30-90 days depending on customer agreement.
- Full reports: not stored in GitHub Actions.
- Full reports should be stored only in local/private/customer-controlled storage.
- Customer PoC completion should include deletion or rotation of secrets and deletion/archival of full evidence according to agreement.
- Deletion evidence should be recorded when applicable.
- Before customer data is used, agree on storage location, access scope, retention period, and deletion or archival procedure.

## Acceptance Criteria

- `GITHUB_ACTIONS=true --report-mode full` must fail.
- `ci` stdout must not contain question, expected_answer, answer, ai_answer, retrieved_evidence, chunk_text, source_path.
- `ci` artifacts must not include `*.jsonl`, full gate-report.json, index/meta.json, faiss.index.
- `redacted` mode must replace sensitive text fields with `[REDACTED]`.
- Non-full mode must not persist `QARunRecord.answer`.
- External RAG error body must not appear in logs/reports/artifacts.
- Slack / GitHub Issue payload must contain safe summary only.
- Existing GateDecision contract must remain backward compatible.

## Implementation Order

1. docs
2. report-mode guard
3. stdout safe summary
4. artifact allowlist
5. safe bundle split
6. sanitizer
7. JSONL control
8. evidence_refs / audit_events

## Connection Validation

GitHub-hosted CI must not validate real customer RAG endpoints. Connection validation in GitHub Actions is limited to dummy/sample endpoints or fully sanitized diagnostics. Customer PoC `external_real` runs should execute locally, on a private runner, or in a customer-controlled environment.

`connection-validation.json` must not contain raw endpoint URLs, query text, token values, raw response bodies, retrieved evidence, source paths, or tenant/customer identifiers.

## Notifications And Issue Comments

GitHub issue comments, Slack messages, Teams messages, and webhook payloads from CI must use safe summaries only. They may include gate status, policy status, aggregate pass rates, S1 failure counts, reason codes, run IDs, and safe artifact filenames. They must not include customer/app/tenant names, endpoints, source documents, raw questions, answers, expected answers, evidence text, owner/steward names, internal paths, or token-like strings.

## Review Checklist

Before merging changes that affect logs, reports, CI, notifications, external adapters, or artifact upload, verify:

- GitHub Actions uses only sample/mock/dummy data or aggregate metadata.
- `GITHUB_ACTIONS=true` cannot produce or upload full reports.
- CI stdout is a safe summary.
- JSON and Markdown reports do not contain local absolute paths or CI workspace paths.
- Artifact uploads are allowlisted.
- New fields do not expose secrets, customer text, raw evidence, source paths, endpoint values, or internal directory structure.
