# ADR 0009: CI Logging And Evidence Policy

## Title

CI Logging And Evidence Policy

## Status

Proposed

## Date

2026-05-02

## Context

Proof Gate / RAG Quality Gate produces machine-readable and human-readable reports for RAG and FAQ quality checks. These reports can include case-level questions, answers, retrieved evidence, failure reasons, artifact paths, and operational metadata.

The repository also uses GitHub Actions for validation. CI is a shared automation environment and must not become a place where customer documents, production answers, secrets, local developer paths, or internal workspace paths are exposed through logs or uploaded artifacts.

The project needs a stable policy that separates:

- CI-safe aggregate output
- redacted review output
- trusted local full diagnostic output

This policy is documented in [Logging And Evidence Policy](../security/logging-and-evidence-policy.md).

## Decision

### 1. GitHub Actions data is limited to sample/mock/dummy data and aggregate metadata

GitHub Actions may use sample, mock, dummy, or synthetic inputs. It may also handle aggregate metadata such as pass rates, counts, severity mix, policy status, and failure category totals.

GitHub Actions must not process or upload real customer documents, production RAG answers, real user questions, secrets, raw adapter payloads, or unredacted evidence text.

### 2. Report modes are `ci`, `redacted`, and `full`

`ci` mode is the default for GitHub Actions and shared automation. It may include aggregate metrics, schema validation results, redacted failure summaries, and relative artifact references.

`redacted` mode may include limited diagnostic context that has been scrubbed of customer-identifying text, secrets, local paths, and workspace paths.

`full` mode is reserved for trusted local operator use. It may include full questions, answers, retrieved evidence, and detailed case diagnostics.

### 3. `GITHUB_ACTIONS=true` prohibits `full` report mode

When `GITHUB_ACTIONS=true`, `full` report mode is prohibited. CI must reject, downgrade, or otherwise avoid full report generation and upload.

This rule applies even for private repositories because CI logs and artifacts are copied, retained, and reviewed differently from local operator files.

### 4. CI artifact uploads must use an allowlist

GitHub Actions should upload only artifacts that are safe by construction, such as validation summaries, test summaries, redacted gate summaries, aggregate report variants, and sample/mock/demo reports.

Raw customer run logs, full customer reports, raw JSONL histories, retrieved chunks, adapter dumps, temporary internal directories, and files containing local or CI absolute paths are denied by default.

### 5. Evidence fields are sensitive by default

Retrieved evidence and embedded prompt evidence must be treated as sensitive unless explicitly known to be sample/mock/dummy content.

CI-safe outputs should prefer evidence IDs, source document IDs, aggregate evidence recall metrics, and redacted snippets only when necessary.

## Consequences

### Good

- CI remains usable for validation without becoming a customer-data handling surface.
- Report mode semantics are explicit and reviewable.
- Artifact upload decisions have a clear allowlist policy.
- Path and evidence leakage can be checked consistently in future PRs.

### Trade-offs

- Full report debugging must happen locally or in a trusted operator environment.
- Some CI diagnostics will be less detailed by design.
- Future report fields must be reviewed against this policy before being added to CI artifacts.

## Alternatives Considered

### 1. Allow full reports in private GitHub Actions

Rejected.

Private repository visibility does not remove the risk of logs, artifacts, and job output being retained, copied, or viewed outside the intended customer context.

### 2. Rely only on developer judgment

Rejected.

The repository needs a clear default for CI and customer-facing artifacts. Review-by-convention is too weak for evidence, answer, and path leakage.

### 3. Remove all case-level diagnostics from every report

Rejected.

Full local diagnostics remain useful for trusted operators. The policy separates local full output from CI-safe and redacted output instead of removing diagnostics entirely.

## Open Questions

- Whether report mode should become an explicit CLI option in a future implementation PR.
- Whether CI should include a dedicated artifact scanner for absolute paths, `.tmp` paths, and common secret patterns.
- Which existing reports should receive first-class redacted variants.
