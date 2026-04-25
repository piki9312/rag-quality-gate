# Product Roadmap

## Roadmap Principle

RAG Quality Gate should become stronger as a CLI-first quality layer before it becomes a platform. The roadmap prioritizes compatibility, repeatable Quality Pack operations, external RAG integration, and explainable reports.

## Phase 1: Harden The Current Quality Gate

Focus:

- Preserve CLI argument compatibility.
- Preserve `GateDecision`, `QARunRecord`, `gate-report.json`, and formal CSV contracts.
- Improve test coverage around parser contracts and output schemas.
- Keep Windows PowerShell usage viable.

Expected outcomes:

- Existing users can upgrade without changing scripts.
- Reports remain machine-readable for downstream consumers.
- Failures are easier to diagnose without changing core semantics.

## Phase 2: Strengthen Quality Pack Operations

Focus:

- Make `validate-pack` more useful for first-time customer packs.
- Improve docs for S1/S2 case design and stale case review.
- Make `gen-cases`, review output, and `merge-cases` easier to operate safely.
- Keep customer-specific learnings in strategy docs until they repeat.

Expected outcomes:

- Delivery teams can create and maintain customer packs with less manual guidance.
- Pack growth does not break formal CSV compatibility.

## Phase 3: External RAG Adapter First

Focus:

- Treat local RAG as a demo and test harness.
- Grow the HTTP adapter boundary as the main customer integration point.
- Improve `validate-connection` diagnostics.
- Keep vendor-specific payload differences inside adapters.

Expected outcomes:

- RQG can evaluate customer systems without replacing their RAG implementation.
- External integration issues are separated from answer-quality failures.

## Phase 4: Report And Review Workflow

Focus:

- Strengthen `gate-report.json` as the downstream integration artifact.
- Keep Markdown report useful for human review.
- Improve weekly or monthly review payloads.
- Connect failure categories to owner-ready next actions.

Expected outcomes:

- Vendors can show customers what failed, why it matters, and what happens next.
- Monthly quality operation becomes a repeatable service motion.

## Phase 5: Consider Product Platform Features

Do not start this phase until the CLI and report workflow have repeated customer evidence.

Possible features:

- Lightweight UI for report browsing.
- Workspace concepts.
- Authentication.
- Hosted storage.
- Customer-facing dashboards.
- Billing.

Explicit constraint:

- These features should not be added merely because they are expected in SaaS. They should be added only when customer deployments show that CLI/report operation is the bottleneck.

## Always Protected

- CLI argument backward compatibility.
- Existing `gate-report.json` fields.
- `GateDecision` machine-readable contract.
- `QARunRecord` JSONL persistence format.
- Formal 16-column CSV and legacy aliases.
- `mock`/real, `eval_mode`, `failure_type`, and fallback meanings.
- External RAG adapter boundary.
- Windows PowerShell compatibility.
