# Case Notes Marker Spec

## Purpose

`notes` markers provide a compatibility layer for structured review metadata
without expanding the formal `cases.csv` schema too early.

Markers should describe abstract IDs, test design intent, source type, release
review hints, and review state. They must not contain customer raw data or
customer-specific policy text.

## Marker Format

Use semicolon-separated markers:

```text
pattern:FP-STALEREF-001; intent:refund_mid_contract_cancellation; answer_status:unapproved-draft
```

Recommended format:

```text
key:value
```

Avoid free-form paragraphs in markers. If notes contain human comments, keep
structured markers short and bounded.

## Existing Markers

| Marker | Meaning | Example |
| --- | --- | --- |
| `pattern:<id>` | Failure Pattern identifier | `pattern:FP-STALEREF-001` |
| `answer_status:unapproved-draft` | Generated expected answer is not vendor/customer approved | `answer_status:unapproved-draft` |
| `answer_status:vendor-approved` | Expected answer was vendor-approved during review | `answer_status:vendor-approved` |
| `source_type:template` | Case came from a template or sample design | `source_type:template` |
| `source_type:generated` | Case was generated or proposed | `source_type:generated` |
| `poc_band:<band>` | PoC selection band; not necessarily runtime severity | `poc_band:S3` |

## Additional Candidate Markers

| Marker | Meaning | Example |
| --- | --- | --- |
| `intent:<intent_id>` | Case Intent identifier | `intent:refund_mid_contract_cancellation` |
| `design:<test_design_type>` | Test design type | `design:decision_table` |
| `claim_template:<id>` | Abstract claim template id | `claim_template:refund_eligibility` |
| `release:<hint>` | Release review hint | `release:needs_human_review` |

These markers are candidates for wider use. They should remain backward
compatible and warning-based until field evidence justifies schema promotion.

## Recommended Values

### pattern

Recommended format:

```text
pattern:FP-[A-Z0-9-]+
```

Example:

```text
pattern:FP-STALEREF-001
```

Existing code may also read `pattern:<slug>` or `failure_pattern:<slug>` for
draft artifacts. Prefer the `FP-...` format for active S1/S2 governance cases
where possible.

### design

Recommended values:

- `boundary_value`
- `decision_table`
- `state_transition`
- `equivalence_class`
- `risk_based`
- `stale_reference`
- `adversarial_prompt`

### answer_status

Allowed review meanings:

- `answer_status:unapproved-draft`
- `answer_status:vendor-approved`

`active` rows should not keep `answer_status:unapproved-draft`.

### release

Recommended values:

- `release:block`
- `release:allow_with_warning`
- `release:needs_human_review`

## What May Go In notes

Allowed:

- abstract IDs
- failure pattern IDs
- intent IDs
- test design type
- source type
- review status
- PoC selection band
- release-rule hint

Not allowed:

- customer name
- raw customer FAQ or policy text
- inquiry log excerpts
- personal information
- concrete pricing amounts
- customer-specific contract wording
- full expected answer text
- raw evidence text
- customer-specific source document body

## Relationship To Formal Schema

Markers are not a replacement for formal fields.

Use formal fields for:

- `case_id`
- `status`
- `severity`
- `eval_mode`
- `question`
- `expected_answer`
- `expected_evidence`
- `expected_keywords`
- `category`
- `source_doc`

Use markers only for metadata that is not stable enough to become a formal
column yet.

## Validator Guidance

Initial validator behavior should be warning-based:

- unknown marker keys should not be errors
- malformed `pattern:` values may warn
- unsupported `design:` values may warn
- unsupported `release:` values may warn
- missing recommended markers may warn for high-risk active rows

Do not attempt heavy raw-data detection in `notes`. That should remain a human
review and data-boundary discipline, not a brittle scanner.

## S1 Active Case Guidance

For `status=active` and `severity=S1`, recommended markers are:

- `pattern:FP-...`
- `design:<test_design_type>`
- optional `intent:<intent_id>`
- optional `release:<hint>`

These markers improve auditability, but adding them should not break existing
cases without an explicit migration plan.
