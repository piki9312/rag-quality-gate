# Phase2 Kickoff Board

Last updated: 2026-03-28

## 1. Migration scope (fixed)

| scope_id | case_source | format | owner | target_zero_date | status |
| --- | --- | --- | --- | --- | --- |
| HR-001 | packs/hr/cases.csv | csv | hr-team | 2026-06-15 | running |
| DEMO-001 | packs/demo_cycle/cases.csv | csv | demo-team | 2026-06-15 | running |

## 2. Baseline metrics

| metric | value | baseline_date | evidence |
| --- | ---: | --- | --- |
| impacted_case_count | 1 | 2026-03-28 | CI run quality-gate legacy migration check |
| unresolved_legacy_refs | 0 | 2026-03-28 | migrate-cases report in CI artifact |

## 3. Weekly cadence (started)

- Workflow: .github/workflows/phase2-weekly-metrics.yml
- Schedule: every Monday 00:00 UTC (Monday 09:00 JST)
- Output artifact: phase2-weekly-metrics
- Review owner: quality owner
- Transfer record: docs/ops/phase2-weekly-metrics-register.md

## 4. Runbook and rollback

Runbook and rollback criteria are fixed in:

- docs/ops/phase2-migration-playbook.md

## 5. Regular impact pre-check

Use this command at least once per week before release:

```bash
qgate impact \
  --old-snapshot artifacts/old_snapshot.json \
  --new-snapshot artifacts/new_snapshot.json \
  --cases artifacts/eval_cases_migrated.json \
  --output artifacts/impact_report.json
```

## 6. Post-expiry cleanup owner

- Related issue: https://github.com/piki9312/rag-quality-gate/issues/4
- Owner: @piki9312
- Planned start: 2026-07-01 or later (after unresolved_legacy_refs stays 0)
- PR template: .github/PULL_REQUEST_TEMPLATE/issue4-post-expiry-cleanup.md
