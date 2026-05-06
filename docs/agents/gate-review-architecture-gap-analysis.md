# Gate Review Architecture Gap Analysis

## 1. Purpose

This document analyzes how closely the current Proof Gate implementation, docs, and templates align with the target model that separates `gate_history` as the machine-readable source of truth, `Gate Review` as the human decision layer, and `Investigation` / `Action Item` as supporting records.

The goal is not to make large implementation changes immediately, but to clarify the current gaps and fix the next architectural priorities in an explicit design document.

## 2. Target Architecture

The target state is a clean separation between machine-readable execution history and the human layers for decision-making, root-cause investigation, and follow-up action tracking.

```text
gate_history (machine-readable source of truth)
  - gate-decision.json
  - gate-report.json
  - gate-history-summary.json
  - gate-decisions.jsonl
  - artifact refs / run metadata
        ↓
Gate Review (human decision layer)
  - customer-facing primary review document
  - PASS / BLOCK / REVIEW / CONDITIONAL
  - links back to gate_history
        ↓
Investigation (only when needed)
  - root cause analysis for BLOCK / REVIEW / CONDITIONAL
        ↓
Action Item
  - execution task tracking tied to review/investigation
```

```text
gate_history = machine-readable source of truth
reviews/ = human decision and response layer
```

## 3. Current Implementation Summary

### `weekly_review.py`

- `src/rqg/quality/weekly_review.py` generates a GitHub Issue payload from `gate-history-summary.json`.
- The output concept is `Weekly Review issue`, not `Gate Review`, and the default title prefix is `[Phase2.5][Weekly Review]`.
- The payload is body-centric and does not carry structured review metadata such as `review_id`, `gate_history_ref`, or `decision`.

### `export-weekly-review`

- `src/rqg/cli/export_weekly_review.py` reads `history_summary` from `gate-history-summary.json` or `gate-report.json` and writes `weekly-review-issue.json`.
- Both the CLI name and the export target assume a `weekly review issue`, so it is not a Gate Review generator.

### gate history generation

- `src/rqg/cli/check.py` generates `gate-report.md`, `gate-report.json`, `gate-decision.json`, `gate-history-summary.json`, and `gate-decisions.jsonl`.
- `src/rqg/quality/history.py` structures recent history summary, comparison, coverage, stale case review, and reliability into `gate-history-summary.json`.
- The bundle in `src/rqg/quality/reporting.py` includes `artifact_paths` and aggregates `decision`, `history_summary`, and `report_markdown` into `gate-report.json`.

### phase2-5 workflows

- `.github/workflows/phase2-5-weekly-review-issue.yml` and `.github/workflows/phase2-5-weekly-metrics.yml` implement the internal weekly-issue workflow.
- Their naming, labels, body content, and related docs are tightly coupled to `Phase2.5`, `weekly review`, and `ops`.

### `templates/github/rqg-gate-weekly-review.yml`

- Even in the customer-facing template, the downstream automation is designed to upsert a `weekly review issue`.
- There are optional GitHub Project and Slack integrations, but the template does not establish Gate Review as the primary customer-facing artifact.

### customer template

- `templates/customer-rqg-template/` includes `cases.csv`, `documents/`, `adapter/`, and `reports/`, but it does not include `reviews/`.
- The README points readers to `gate-report.md` as the main human review artifact.

### tests

- `tests/test_weekly_review_export.py` locks the current contract around the `weekly review issue`.
- `tests/test_github_templates.py` verifies `[Phase2.5][Weekly Review]` and `phase2-5` labels as part of the repository/workflow contract.

## 4. Gap Analysis

| Area | Current State | Target State | Gap | Priority |
|---|---|---|---|---|
| Naming | `Weekly Review`, `Phase2.5`, and `issue` are front and center | Customer-facing terminology should be `Gate Review`, while internal operations use separate naming | Customer-facing concepts are mixed with internal operating terms | P0 |
| Gate History relation | History artifacts already exist and the bundle includes artifact refs | `gate_history` should be explicitly framed as the source of truth and referenced from the review layer | Review-side link metadata and conceptual guidance are missing | P0 |
| Gate Review concept | Not implemented as an independent concept; the weekly issue acts as a substitute | Gate Review should exist as the primary human decision artifact | The decision layer is buried inside issue body text | P0 |
| Customer review burden | The README centers on reports, and the boundary between raw artifacts, weekly review, and internal docs is unclear | Customer-facing review should be centered on Gate Review | Customers do not have a single clear starting point | P0 |
| file-based `reviews/` | Missing from the customer template | Early PoC operation should standardize a file-based `reviews/` layer | There is no lightweight operating model yet | P0 |
| GitHub Issues automation | Weekly issue automation assumes Phase2.5/internal naming | A generic customer-facing workflow should be offered as an optional extension | The current workflow is hard to expose directly in customer repositories | P1 |
| Metadata for LLM search | History summary is partially structured | Review, investigation, and action item layers should carry structured IDs, links, and status | Metadata for search, audit, and traceability is missing | P1 |
| Customer template | Reports exist, but there is no reviews layer | The template should show both `gate_history` and the reviews layer | There is no dedicated home for the decision layer | P0 |
| Docs | Internal ops docs are rich, but customer-facing review architecture guidance is limited | Docs should clearly define the role of each artifact type | Internal terminology leaks into customer-facing guidance | P0 |

## 5. Recommended Design

- `gate_history` remains the source of truth. `gate-decision.json`, `gate-report.json`, `gate-history-summary.json`, and `gate-decisions.jsonl` should not be replaced.
- `Gate Review` becomes the primary customer-facing decision artifact. The main go/no-go conversation for production use should be concentrated there.
- `Gate Report` should remain supporting evidence for Gate Review rather than becoming the default customer-facing artifact set.
- `Investigation` and `Action Item` should remain supporting records that are created only when needed.
- Early PoC operation should not require GitHub Issues and should support a file-based flow through the `reviews/` directory.
- For longer-running or more mature customers, GitHub Issues, Project Boards, and Slack notifications can be offered as optional extensions.
- The existing `Phase2.5` workflows should remain for internal operations, but should not be exposed in customer-facing docs, templates, or naming.
- Customer-facing workflows should use `ProofGate` / `Gate Review` naming instead of `Phase2.5`.

## 6. Proposed Directory Structure

Recommended structure for `templates/customer-rqg-template/`:

```text
reviews/
  README.md
  gate_reviews/
    .gitkeep
  investigations/
    .gitkeep
  action_items/
    .gitkeep
  templates/
    gate_review.md
    investigation.md
    action_item.md
```

Notes:

- `reports/` can remain the storage location for gate-history-related outputs.
- `reviews/` should be added as the human layer for customer decisions, investigations, and follow-up actions.
- `logs/` and `runs/` are execution artifacts and should not become the primary customer review location.

## 7. Proposed Metadata Schema

### Gate Review Metadata

- `review_id`
- `client_id`
- `gate_run_id`
- `gate_history_ref`
- `decision`
- `risk_areas`
- `severity`
- `pack_version`
- `gate_policy_version`
- `source_report`
- `status`

### Investigation Metadata

- `investigation_id`
- `client_id`
- `linked_gate_review`
- `gate_run_id`
- `gate_history_ref`
- `failure_category`
- `root_cause_type`
- `severity`
- `status`
- `owner`

### Action Item Metadata

- `action_id`
- `client_id`
- `linked_gate_review`
- `linked_investigation`
- `gate_run_id`
- `gate_history_ref`
- `risk_area`
- `status`
- `owner`
- `due_date`

## 8. Implementation Plan

### P0

- Define `gate_history`, `Gate Review`, `Investigation`, and `Action Item` clearly in docs.
- Add `reviews/` to the customer template.
- Update the customer template README to explain how Gate Review differs from the other artifacts.
- Add a clear path that centers the customer-facing primary artifact on Gate Review.

### P1

- Separate the customer-facing GitHub Issues workflow from `Phase2.5`.
- Use `[ProofGate][Gate Review]` as the title prefix.
- Use `proofgate`, `gate-review`, and `ops` labels.
- Document GitHub Projects and Slack notifications as optional extensions.

### P2

- Add a Gate Review payload exporter.
- Generate a Gate Review draft from `gate_history`.
- Evaluate a metadata index for reviews, investigations, and action items.
- Evaluate a structured export for the review layer that supports LLM search.

## 9. Risks and Non-goals

- Do not break the existing `Phase2.5` workflows. Internal operating flow must remain compatible.
- This work does not implement cross-customer LLM search.
- Do not place customer-specific information or secrets in the shared repository.
- The goal is not to create more review artifacts for their own sake; decision-making should stay concentrated in Gate Review.
- Do not break existing contracts such as `gate-report.json`, `GateDecision`, `QARunRecord`, or `cases.csv` without a migration plan.

## 10. TODO Issues

- Add customer template `reviews/` directory
- Add `reviews/README.md` and review/investigation/action item markdown templates
- Add customer-facing Gate Review architecture doc to template README
- Add customer weekly review workflow without `Phase2.5` naming
- Add Gate Review metadata fields and sample frontmatter
- Add Gate Review exporter that links to `gate_history`
- Align `gate_history` artifact paths with review metadata references
- Add tests for `reviews/` template presence
- Add docs that distinguish Gate Review / Gate Report / Investigation / Action Item / raw artifacts
- Add anonymization guidance for reusable failure-pattern knowledge

## Current State by Review Lens

### A. Naming and concept gap

**Current state**

- The implementation, CLI, workflows, and tests are all framed around `Weekly Review`.
- `Gate Review` is not yet defined as an independent concept.
- `Phase2.5`, `hardening`, `weekly review`, and `issue` are exposed in customer-facing templates and README content.

**Problems**

- Customer-facing terminology is mixed with internal operating terminology.
- The review record is conflated with the GitHub Issue transport mechanism.
- There is little conceptual space for switching to a file-based operating mode.

**Recommended adjustment**

- Standardize on `Gate Review` as the customer-facing umbrella term.
- Treat `Weekly Review` as a cadence label and `Issue` as an optional transport.
- Keep `Phase2.5` as internal-only naming.

### B. Relationship to `gate_history`

**Current state**

- `gate_history` artifacts are already generated, and the reporting bundle exists.
- `gate-history-summary.json` already structures comparison, coverage, stale-case review, and reliability.
- However, the review payload does not carry `gate_run_id`, `gate_history_ref`, or `source_report`.

**Missing metadata**

- `review_id`
- `gate_run_id`
- `gate_history_ref`
- `source_report`
- `pack_version`
- `gate_policy_version`
- review decision/status

**Recommended adjustment**

- The review layer should always carry metadata that points back to `gate_history`.
- `gate_history` and the review layer should reference each other.
- The review layer should be explicitly treated as decision notes, not as the source of truth.

### C. Customer decision burden

**Current state**

- The customer README points primarily to `gate-report.md` and `gate-report.json`.
- The distinction between weekly review issues, internal ops docs, and raw artifacts is not organized for customer readers.

**Where customers get confused**

- It is unclear which artifact is the primary decision document.
- The division of responsibility between `gate-report.md` and the review/ticket layer is unclear.
- It is hard to tell how deeply raw artifacts need to be inspected.

**Recommended adjustment**

- State clearly in the customer README: start with Gate Review, and only consult Gate Report or raw artifacts when needed.
- Fix the distinction between Gate Review, Gate Report, Investigation, Action Item, and raw artifacts in a comparison table.

### D. File-based `reviews/` operation

**Current state**

- `templates/customer-rqg-template/reviews/` does not exist.
- There are no templates for gate reviews, investigations, or action items.

**Files to add**

- `reviews/README.md`
- `reviews/gate_reviews/.gitkeep`
- `reviews/investigations/.gitkeep`
- `reviews/action_items/.gitkeep`
- `reviews/templates/gate_review.md`
- `reviews/templates/investigation.md`
- `reviews/templates/action_item.md`

**Recommended directory structure**

- Add the Section 6 structure to the customer template.

### E. Relationship to GitHub Issues automation

**Current state**

- Issue automation is optimized for `Phase2.5` internal ops.
- The title prefix and labels are fixed around internal naming.
- GitHub Projects and Slack are optional, but the customer workflow still assumes internal conventions.

**Why it is hard to reuse as-is for customers**

- It exposes `Phase2.5` in the customer repository.
- It makes the `Weekly Review issue` look like the only review record.
- It does not define customer-facing metadata.

**Generalization approach**

- Keep the internal workflow unchanged.
- Add a separate customer-facing workflow with a `[ProofGate][Gate Review]` prefix and generic labels.
- Keep GitHub Projects and Slack as optional examples.

### F. Readiness for LLM search and knowledge reuse

**Current state**

- The `gate_history` side is relatively well structured.
- The review / investigation / action item layer is still undefined.
- `docs/agents` already includes a policy not to mix customer-specific information into shared assets.

**Structure still needed for LLM search**

- Stable IDs for reviews, investigations, and action items
- link fields
- status / owner / due date
- risk area / severity
- client-scoped reference design

**Metadata to add**

- `client_id`
- `review_id`
- `investigation_id`
- `action_id`
- `gate_run_id`
- `gate_history_ref`
- `risk_area`
- `status`
- `owner`
- `due_date`

In addition, cross-customer search should generally be avoided. If failure-pattern knowledge is promoted into shared assets, it should be anonymized, abstracted, and documented explicitly.
