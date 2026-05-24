# Pattern-Based gen_cases Implementation Plan

## Purpose

This document defines the developer-facing implementation plan for pattern-based `gen_cases` and the Case Draft Engine.

Pattern-based `gen_cases` should:

- apply the Case Intent Library to customer documents
- use Failure Patterns and Question Variations to create customer-specific draft cases
- output generated cases as `needs_review`
- require vendor approval before generated cases become `active`
- preserve the rule that only `active` cases are Gate execution targets
- support coverage while leaving customer-specific correctness approval to the vendor

Proof Gate supports coverage: which risks, Failure Patterns, Case Intents, and Coverage Rules should be considered.

The vendor approves correctness: whether the `expected_answer` / `expected_behavior` is correct for the customer business.

## Non-Goals

This plan does not include:

- making generated cases `active`
- Proof Gate guaranteeing customer-specific `expected_answer`
- storing customer raw data on the Proof Gate side
- automatic case selection for Gate execution
- full Document Impact Analysis implementation
- SaaS, database, authentication, or multi-tenant implementation
- building a large Case Intent Library up front

## Target Architecture

```text
assets/case_intents/
  -> CaseIntentRegistry
  -> CaseDraftEngine
  -> Generated Customer Draft Cases
  -> Vendor Review
  -> Active Cases
  -> Gate Execution
```

Future module shape:

```text
src/rqg/case_assets/
  intent_schema.py
  registry.py
  loader.py
  validator.py

src/rqg/case_draft/
  engine.py
  retrieval.py
  prompt_builder.py
  output_parser.py
  validators.py

src/rqg/cli/casegen.py
```

The first implementation should keep existing CLI behavior stable unless an explicit follow-up changes it.

## Case Intent Library Management

Start with YAML as the source of truth.

Initial approach:

- YAML as source of truth
- Git review
- schema validation
- small library only

Mid-term approach:

- YAML source
- generated registry JSON for faster loading or packaging

Future approach:

- Private Asset Registry
- database-backed registry
- remote asset service

Do not start with a database because:

- the schema will likely change
- Git review is valuable for early asset governance
- humans need to read and review the assets
- the first implementation should stay small

Conditions that may justify DB or registry extraction:

- thousands to tens of thousands of intents
- UI-based management
- usage analytics
- vendor-specific pack distribution
- remote protected asset loading

## Case Draft Engine Responsibilities

The Case Draft Engine should:

- select relevant Case Intents
- reference customer document sections
- concretize Question Variations
- create `expected_answer_draft`
- connect Evidence Requirements to `source_section_ref`
- add notes markers
- output `status=needs_review`
- validate draft rows
- avoid raw secret leakage

It should not approve cases, select cases for Gate execution, or make release decisions.

The first skeleton should produce an internal `DraftCaseCandidate`, not a new public `cases.csv` schema.

## Generation Modes

### Document-Based Generation

Creates basic review cases from document sections.

This is closest to existing `gen_cases` behavior.

Typical severity direction: S2 / S3.

### Pattern-Based Generation

Creates risk-oriented cases from Failure Patterns and Case Intents.

This is the core new implementation direction.

Typical severity direction: S1 / S2.

### Change-Aware Generation

Uses `change-event.yml` `affected_business_categories` to select candidate Case Intents and propose draft cases.

It must not automatically activate generated cases.

It must not filter which active cases are executed.

## LLM Usage Policy

LLM is a draft assistant, not the authority.

LLM may help with:

- draft question generation
- `expected_answer_draft` generation
- source section summarization
- Question Variation concretization

LLM must not:

- make cases `active`
- make the final customer-specific correctness decision
- make Go / No-Go decisions by itself
- automatically promote assets into the Case Intent Library

Human review and vendor approval remain mandatory before generated cases become approved-for-run.

## Output Contract

Generated case output should use the existing case schema first.

Initial output contract:

```text
status = needs_review
severity = severity_hint or generated severity candidate
category = risk_category
question = generated draft question
expected_answer = expected_answer_draft
expected_evidence / source_doc = source section refs if available
```

`notes` should include markers:

```text
generated_by:gen_cases
case_type:generated-draft
intent:<intent_id>
pattern:<failure_pattern>
```

Use notes markers first to avoid breaking the formal `cases.csv` schema.

## Validation

Minimum validation:

- `status` is not `active`
- `intent_id` is present
- `generated_by` marker is present
- `category` is present
- `severity` is an allowed value
- `question` is not empty
- `expected_answer_draft` is not empty
- `source_section_ref` exists if referenced
- raw secrets or API keys are not present
- safe/full boundary is not violated

Validation should fail closed for activation-related mistakes. A generated row that cannot be validated should stay out of formal Gate execution.

## Implementation Phases

### Phase 0: Docs And Consistency Review

- design consistency review
- implementation plan
- no code changes

### Phase 1: gen_cases Safety

- generated cases default to `needs_review`
- add `generated_by` marker
- do not change active execution behavior

### Phase 2: Case Intent Schema And Loader

- YAML schema
- small sample intents
- validation tests
- optional generated registry JSON

Phase 2 should start with a minimal Case Intent Library foundation:

- planned source location: `src/rqg/case_assets/`
- planned sample location: `assets/case_intents/`
- sample intents are not customer-approved `cases.csv`
- customer-specific `expected_answer` is rejected from Case Intent YAML

Before the Case Draft Engine generates anything, relevant Case Intents must be selected in a deterministic way. `CaseIntentRegistry` is the planned selection layer:

- look up intents by id, risk category, Failure Pattern, severity hint, or affected business category
- select candidates from `coverage_rule.required_when.affected_business_categories`
- keep selection deterministic by returning `intent_id` sorted results
- avoid delegating intent selection to an LLM

### Phase 3: Case Draft Engine Skeleton

- internal module
- no full LLM dependency required
- template/mock-based draft generation is acceptable

Phase 3 planned implementation note:

- planned source location: `src/rqg/case_draft/`
- the engine should create `DraftCaseCandidate` from a `CaseIntent`
- output status should be `needs_review`, never `active`
- initial generation should be template-based and should not call an LLM
- existing `gen_cases` should not be connected yet

Planner planned implementation note:

- `CaseDraftPlanner` should connect `CaseIntentRegistry` candidate selection to `CaseDraftEngine`
- affected business categories should be mapped to candidate Case Intents through `coverage_rule.required_when.affected_business_categories`
- candidate intents should be converted to `needs_review` `DraftCaseCandidate` objects
- duplicate intent hits should not create duplicate drafts
- this planner should remain internal and should not be connected to the existing `gen_cases` CLI at first
- it should not use LLMs, retrieval, or automatic activation

Source matching planned implementation note:

- `SourceSectionMatcher` should deterministically select a candidate `SourceSection` for a `CaseIntent`
- matching should use `evidence_requirement` against section id, source ref, and text
- this is not full retrieval and does not use LLMs, embeddings, BM25, vector DB, or RAG endpoints
- the matcher can be replaced by a future retrieval layer
- drafts remain `needs_review` even when a source section is matched

Row adapter planned implementation note:

- `DraftCaseCandidate` should be convertible to a formal `cases.csv` compatible draft row
- this adapter is the boundary before future `gen_cases` CLI integration
- adapter output status should remain `needs_review`
- adapter output should add `answer_status:unapproved-draft`
- generated `expected_answer` remains an unapproved draft until vendor approval
- active promotion remains a separate vendor approval step

Internal pipeline planned implementation note:

- `PatternDraftPipeline` should combine registry selection, source matching, draft generation, and row adaptation
- input should be affected categories, a `CaseIntentRegistry`, and optional `SourceSection` candidates
- output should be `cases.csv` compatible `needs_review` draft rows
- the pipeline should remain internal and should not be connected to the existing `gen_cases` CLI at first
- it should not use LLMs, embeddings, BM25, vector DB, RAG endpoints, or automatic activation

CSV preview/writer planned implementation note:

- internal draft rows should be renderable as review CSV artifact text
- the writer should use formal-schema fields because the existing `merge-cases` flow accepts those rows as review input
- this output is not the governed source-of-truth `cases.csv`
- field order follows `FORMAL_CASE_FIELDS` for merge compatibility
- writer output should be limited to `needs_review` candidate rows
- active rows should be rejected
- generated answers remain marked as `answer_status:unapproved-draft`
- this is still not connected to the existing `gen_cases` CLI

Preview artifact planned implementation note:

- pattern draft rows should be writable as a review CSV artifact for vendor review
- the artifact writer should combine `PatternDraftPipeline` and the draft CSV writer
- input should be affected categories, a `CaseIntentRegistry`, optional source sections, and an output path
- output should be a `needs_review` review artifact plus metadata such as row count
- zero-row output should write a header-only CSV so missing candidates can still be inspected
- this is still not connected to the existing `gen_cases` CLI

Existing review flow alignment:

- pattern-based draft generation must feed the existing `review.csv -> merge-cases -> cases.csv` flow
- it must not introduce a separate approval workflow
- generated rows are review candidates until a human reviews them and the existing merge/adoption flow brings them into `cases.csv`
- generated rows remain `needs_review`; activation is a later vendor approval step
- recommended future filename: `pattern-draft-review.csv` or an explicit non-overwriting `review.csv` path chosen by the operator

### Phase 4: Pattern-Based Generation Prototype

- select Case Intent
- retrieve related document section
- generate draft question / `expected_answer_draft`
- output `needs_review` cases

### Phase 5: Change-Aware Connection

- use `affected_business_categories` to select candidate intents
- do not filter executed cases
- do not auto-activate generated cases

### Phase 6: Coverage Warning Integration

- compare affected categories / intents with active cases
- advisory warning only
- do not automatically change GateDecision

## Migration From Existing gen_cases

Existing document-based generation should remain available.

Migration direction:

- current document-based generation remains
- default output status changes to `needs_review`
- `generated_by` marker is added
- pattern-based mode is added later
- existing active cases behavior remains unchanged
- future pattern-based output should pass through a row adapter before writing `cases.csv` compatible draft rows
- row adapter output must remain `needs_review` and mark draft answers as unapproved
- future CLI integration can use the internal CSV writer first as a review artifact boundary
- CSV writer output is for vendor review, not approved-for-run evidence
- future CLI integration can call the preview artifact writer to produce `pattern-draft-review.csv` before the existing `merge-cases` adoption flow
- review artifact rows remain `needs_review`; vendor approval is still required before `active`

The migration should avoid breaking current partner workflows. The first behavioral change should be safety-oriented: generated rows should not become approved-for-run without vendor approval.

## Risk And Mitigation

| Risk | Mitigation |
|---|---|
| LLM hallucination | Keep output as `needs_review`, validate drafts, require vendor approval. |
| Bad `expected_answer_draft` | Do not activate by default; require vendor correctness review. |
| Library quality drift | Add review process, versioning, and asset states such as experimental / validated / deprecated. |
| Asset leakage | Do not distribute the full library; keep customer raw data out of Proof Gate-owned storage. |
| Overfitting to RAG | Model assets as AI output review concepts where possible. |
| Implementation complexity | Split implementation into phases and keep initial library small. |

## Safe/Full Boundary

Pattern-based generation may touch customer document text locally in the vendor or customer environment.

Proof Gate-side shared assets should contain reusable intent, pattern, variation, behavior template, severity, evidence requirement, and coverage metadata. They should not contain customer-private raw questions, raw answers, raw evidence, customer document text, customer names, owners, or secrets.

Generated cases may contain customer-specific full/private information. They should remain in the vendor or customer-controlled environment unless an explicit agreement says otherwise.
