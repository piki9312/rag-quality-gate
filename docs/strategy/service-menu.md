# Service Menu

## Purpose

This service menu translates RAG Quality Gate into sellable delivery packages for RAG vendors and AI implementation consultancies. It is intentionally service-friendly: before 10 customer deployments, the product should support hands-on implementation and learning rather than force premature SaaS structure.

## Package 1: PoC Quality Gate Setup

Goal: add a repeatable quality gate to an existing RAG or FAQ PoC.

Typical scope:

- Review customer documents and risk areas.
- Create an initial `cases.csv` with S1/S2 split.
- Configure `gate.yml` thresholds.
- Run `rqg gate` in mock or real mode.
- Deliver `gate-report.md`, `gate-decision.json`, and `gate-report.json`.
- Prepare a customer-facing Gate Review that summarizes production readiness,
  major risks, and required actions.
- Use `ci` or `redacted` report mode for shared summaries; keep full evidence
  only in local, private runner, or customer-controlled environments.

Best fit:

- Paid PoC nearing customer demo or production decision.
- Teams currently validating answers manually in spreadsheets.

Success signal:

- The customer can see which cases block rollout and why.
- The customer understands what remains in CI artifacts and what stays outside
  GitHub-hosted Actions.

## Package 2: External RAG Contract Integration

Goal: connect RQG to the customer's existing RAG endpoint without replacing their system.

Typical scope:

- Confirm the HTTP retrieval contract with `rqg validate-connection`.
- Normalize retrieved chunks through the external adapter boundary.
- Run `rqg gate --rag-endpoint`.
- Document endpoint, auth, timeout, and schema assumptions.
- Prefer staging, test, or read-only endpoints for PoC validation.
- Keep API keys in environment variables or GitHub Secrets, never in the repo.

Best fit:

- Vendors with their own RAG stack.
- Customers that do not want to move documents into the local demo RAG path.

Success signal:

- RQG can evaluate the delivered RAG system through a stable retrieval boundary.
- HTTP error bodies, raw endpoints, and secrets do not appear in validation
  stdout, reports, or CI artifacts.

## Package 3: Monthly Quality Operation

Goal: turn one-time validation into ongoing quality assurance.

Typical scope:

- Run scheduled gate checks after document, prompt, model, or retrieval changes.
- Review failures by category.
- Maintain S1/S2 case coverage.
- Export weekly or monthly review payloads from `gate-report.json`.
- Track stale cases and missing next actions.
- Maintain Gate Reviews, Investigations, and Action Items as the human-facing
  operating record.

Best fit:

- Production FAQ or internal-document agents.
- Customers that need ongoing vendor accountability.

Success signal:

- Quality review becomes a recurring operational artifact, not an ad hoc manual check.

## Customer-Facing PoC Deliverables

For a paid PoC, keep the deliverables simple and decision-oriented:

| Deliverable | What it tells the customer | Normal audience |
|---|---|---|
| Gate Review | Whether the change can proceed, must be blocked, or needs human review. | Customer owner and manager |
| Gate Report or redacted report | The detailed basis for the Gate Review. | Technical reviewer |
| Safe CI summary | Automated run status, pass rate, S1 failures, and safe artifact references. | Delivery and CI owner |
| Risk / failure pattern summary | The recurring failure categories and business risk areas. | PM, vendor lead |
| Action Items | Fixes or confirmations needed before release. | Assigned delivery owner |
| Final PoC Report | Continue, productionize, improve existing RAG, or start Monitor. | Decision makers |

Raw artifacts are not the normal customer decision material. Treat them as
machine-readable logs for audit or automation, and share them only when the
environment and customer agreement allow it.

## Package 4: Quality Pack Expansion

Goal: grow a customer's case portfolio safely after the first gate is working.

Typical scope:

- Use `gen-cases` to draft candidates from snapshots.
- Review generated candidates in CSV or Markdown.
- Merge curated rows with `merge-cases`.
- Validate the pack with `validate-cases` and `validate-pack`.

Best fit:

- Customers expanding from one document group to another.
- Vendors standardizing delivery across similar customer domains.

Success signal:

- Case coverage grows without breaking the formal 16-column CSV contract.

## Not Included Yet

- Hosted dashboard.
- Customer login and user management.
- Billing integration.
- Multi-tenant workspace model.
- Generic observability platform features.
