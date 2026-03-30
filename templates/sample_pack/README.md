# Internal Documents Sample Pack Template

This template is the minimum starter pack for assistant AI that relies on internal documents.

Product principle:

- Core is horizontal quality-gate foundation
- Pack is vertical entry point for easier adoption and value communication

Included files:

- documents/leave_policy.md
- cases.csv
- gate.yml
- quality-pack.yml
- reports/example-impact-report.json

Quick usage:

1. Copy this folder into your workspace as packs/my_pack/.
2. Run:
   - rqg ingest packs/my_pack/documents --index-dir index
   - rqg eval packs/my_pack/cases.csv --docs packs/my_pack/documents --mock --index-dir index --log-dir runs/quality
   - rqg check --log-dir runs/quality --config packs/my_pack/gate.yml
   - rqg check --log-dir runs/quality --config packs/my_pack/gate.yml --quality-pack packs/my_pack/quality-pack.yml
3. For onboarding smoke, use python -m rqg.demo.onboarding_quickstart.

Minimum review checklist:

- Confirm impacted cases after document updates
- Confirm S1 cases are still protected
- Confirm failures have owner and due date
- Confirm stale cases (last_reviewed_at older than 30 days) are reviewed

Severity policy (recommended):

- S1: policy/compliance/rights/money/deadline critical risk
- S2: non-critical completeness or clarity risk

Common failure patterns:

- Retrieval miss: expected evidence not found in top-k
- Stale case: expected keywords/evidence not updated after doc change
- Procedure drift: steps changed in docs but case expectation unchanged
- Escalation gap: ownership/contact route missing in generated answer
