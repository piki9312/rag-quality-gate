# Repository Guidance

This repository is a quality-assurance layer for customer-facing RAG and FAQ agents. Treat it as a production gate foundation for teams moving from paid PoC to monthly quality operations, not as a general LLMOps platform or a full RAG engine.

## Product Direction

- Primary users: RAG delivery vendors, AI implementation consultancies, and small to mid-sized teams delivering internal-document search or FAQ agents for customers.
- First use cases: high-risk document FAQ, internal policy RAG, HR/labor/internal-rule FAQ agents, and domains where answer mistakes create accountability or trust risk.
- Near-term product shape: CLI, Quality Pack, external RAG adapter boundary, and machine-readable/human-readable reports.
- Operating model: semi-product and semi-service until roughly 10 customer deployments; postpone SaaS, tenant workspaces, authentication, billing, and heavy UI.

## Compatibility Boundaries

Do not break these without an explicit migration plan:

- CLI argument backward compatibility.
- Existing `gate-report.json` fields.
- `GateDecision` machine-readable JSON contract.
- `QARunRecord` JSONL persistence format.
- Formal 16-column `cases.csv` and legacy aliases.
- Meanings of `mock`/real, `eval_mode`, `failure_type`, and fallback behavior.
- `external_adapter.py` as the boundary that absorbs external RAG response differences.
- Windows PowerShell compatibility for local usage.

## Implementation Bias

- Strengthen `rqg gate`, Quality Pack validation, reports, and external RAG contract before adding platform features.
- Keep customer-specific learnings in `docs/strategy/` first; move only repeatable patterns back into shared code or templates.
- Prefer additive docs and tests before changing behavior.
- Avoid building SaaS, auth, billing, dashboard, or multi-tenant database features until the CLI/report workflow has repeated customer evidence.
