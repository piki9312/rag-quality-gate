# Evidence Boundary Artifact Inventory

## Purpose

This document records the output boundary for Proof Gate artifacts after the
Evidence Boundary hardening phase. It is a development and operations reference:
new artifacts should be reviewed against this inventory before they are exposed
to CI, notifications, customer-facing reports, GitHub Issues, or long-term
history.

The key split is:

- `ReportModePolicy` decides which report mode is allowed for the run.
- `ArtifactExposurePolicy` decides which fields can appear in a given artifact.
- External-facing and long-term artifacts stay safe even when the run uses
  `full` mode.

## Classification Terms

| Class | Meaning |
| --- | --- |
| internal | Intended for local/private/customer-controlled investigation. |
| external-facing | May leave the local runner through CI, notification, issue payload, email, or shared export. |
| long-term | May be retained for trend analysis, audit, backup, monthly/weekly rollups, or dashboards. |
| customer-facing | Intended for customer-visible delivery or summary use. |

Raw customer data includes raw question text, AI answer text, expected answers,
expected evidence, retrieved evidence, raw source document names/paths, raw
target docs, raw case IDs, free-form failure reasons, customer-authored change
text, endpoint URLs, secrets, tokens, and API key values.

## Artifact Inventory

| Artifact | Class | Raw customer data allowed? | Safe projection in full mode? | Retention notes | Shareable? | Main generation point |
| --- | --- | --- | --- | --- | --- | --- |
| `gate-report.md` | internal unless generated in `redacted`/`ci` mode | Yes in `full`; no in `redacted`/`ci` | No for internal full report | Short retention; do not upload full customer reports from CI | Only `redacted`/`ci` output is shareable | `src/rqg/cli/check.py`, `src/rqg/quality/check.py` |
| `gate-report.json` | internal bundle; includes safe public review packet and optional internal packet | Yes in full case rows and `internal_review_packet`; safe `review_packet` remains safe | Partially: public `review_packet` is safe even in full | Store full bundles only in local/private/customer-controlled storage | Share only after confirming no full/internal sections are included | `src/rqg/quality/reporting.py` |
| `customer-summary.md` | customer-facing | No | Yes | Short to medium retention under customer agreement | Yes | `src/rqg/quality/check.py` |
| `gate-decision.json` | CI/report decision artifact | Safe metadata only by policy intent | Yes when emitted for CI/customer-facing paths | Short to medium retention | Yes if generated from safe mode | `src/rqg/cli/check.py`, `src/rqg/quality/check.py` |
| `gate-decisions.jsonl` | internal compatibility history | Existing schema may contain internal details | No; kept for backward compatibility | Treat as restricted internal log | No | `src/rqg/quality/reporting.py` |
| `gate-decisions-safe.jsonl` | long-term, audit-safe history | No | Yes | Preferred source for rollups, audit export, and shared analytics | Yes | `src/rqg/quality/reporting.py` |
| `gate-history-summary.json` | long-term summary | No | Yes | 30-90 days or customer-agreed retention | Yes | `src/rqg/quality/history.py`, `src/rqg/cli/check.py` |
| `monthly-summary.json` | long-term external-facing summary | No when safe history is available | Yes | 30-90 days or customer-agreed retention | Yes | `src/rqg/quality/monthly_summary.py` |
| `monthly-summary.md` | long-term external-facing summary | No when safe history is available | Yes | 30-90 days or customer-agreed retention | Yes | `src/rqg/quality/monthly_summary.py` |
| Weekly-review issue payload | external-facing GitHub Issue payload | No | Yes | Use project retention rules for issues | Yes | `src/rqg/quality/weekly_review.py`, `src/rqg/cli/export_weekly_review.py` |
| Notification payload | external-facing webhook/Slack/Issue/email payload | No | Yes | Keep short; avoid raw evidence in notification systems | Yes | `src/rqg/quality/notifications.py` |
| `review_packet` | external-facing safe review packet | No | Yes | Same as shared report/review artifact | Yes | `src/rqg/quality/reporting.py` |
| `internal_review_packet` | internal human review packet | Yes, except secrets/endpoints/tokens/API key values | No | Restricted; local/private/customer-controlled only | No | `src/rqg/quality/reporting.py` |
| Dashboard-consumed artifacts | internal operational view unless explicitly published | Depends on source artifact | Not guaranteed in this phase | Treat dashboard raw sources as restricted | Not by default | `src/rqg/serving/dashboard.py`, history/report files |
| Raw eval JSONL | internal evaluation run log | Yes in full/local contexts; non-full should avoid raw answers | No | Restricted; do not upload from CI | No | `src/rqg/quality/runner.py`, `src/rqg/cli/eval.py` |

## Policy Matrix

| Context | ReportModePolicy result | ArtifactExposurePolicy effect |
| --- | --- | --- |
| `full` requested locally | Allows `full` unless blocked by GitHub Actions or customer-facing constraints | Internal reports may include raw evidence; external-facing and long-term artifact types still use safe allowlists. |
| `redacted` requested | Uses `redacted`; downgrades to `ci` in GitHub Actions | Case rows preserve shape but replace raw identifiers/details with hashes, redaction markers, or safe reason codes. |
| `ci` requested | Always `ci` | CI case rows, stdout-oriented payloads, notifications, and history summaries expose only bounded safe fields and hashes. |
| No requested mode in GitHub Actions | Defaults to `ci` | Full evidence artifacts are not allowed for CI paths. |
| Customer-facing run | Defaults to `redacted`; explicit `full` fails fast | Customer-facing artifacts use redacted/safe projections and must not expose raw customer-authored identifiers. |
| External real/external RAG run | Defaults to `redacted` when unspecified | External endpoint and response details must remain bounded or hashed; raw endpoint URLs and raw response bodies are forbidden. |
| Mock/simulation plus customer-facing | Fails unless simulation output is explicitly allowed; warning is attached when allowed | Allowed simulation output must not become less restrictive than `redacted`. |

## Regression Checklist For New Artifacts

Before adding or exposing an artifact, verify:

- It has an explicit artifact class: internal, external-facing, long-term, or customer-facing.
- Unknown fields default to deny.
- Raw question is not exposed unless the artifact is internal-only.
- Raw AI answer is not exposed unless the artifact is internal-only.
- `expected_answer` and `expected_evidence` are not exposed unless internal-only.
- Retrieved evidence text, source document names/paths, and target docs are hashed or removed.
- Raw `case_id` is hashed for external-facing and long-term artifacts.
- Free-form `fail_reason` is mapped to a safe reason code or failure taxonomy value.
- `full` mode does not weaken external-facing or long-term artifact projection.
- Absolute local paths and CI workspace paths are not included.
- Endpoint URLs, API key environment values, tokens, and secrets are forbidden.
- Notification, GitHub Issue, weekly review, monthly summary, and customer summary payloads are built from safe projections.
- Raw JSONL and full bundles are not added to CI artifact upload allowlists.
- Retention and deletion expectations are documented before customer data is used.

## Extension Notes

Raw evidence may still be needed for human investigation. Keep that capability
in internal-only artifacts such as `internal_review_packet` or a future
restricted Raw Evidence Vault. Do not route internal raw evidence into
notifications, weekly/monthly exports, CI artifacts, or customer-facing reports.

The next governance phase should centralize reliability and human-review
decisions separately from presentation policy. That work should not change the
field exposure rules documented here without an explicit Evidence Boundary
review.
