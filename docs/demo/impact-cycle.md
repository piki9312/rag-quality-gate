# Impact Analysis Demo

This demo shows one fixed scenario for Phase 1.5.

## Goal

Run one end-to-end sequence:

1. ingest document A
2. auto-generate eval cases from snapshot
3. evaluate and pass
4. update document A
5. run impact analysis to extract impacted cases
6. re-evaluate and observe fail
7. fix document and pass again

## Command

Run from repository root:

```bash
python -m rqg.demo.impact_cycle
```

## Expected Result

Artifacts are written to:

`demo_runs/impact_cycle/<run-id>/`

Key files:

- `01-pass/artifacts/eval_cases.json`
- `02-fail-and-impact/artifacts/impact_report.json`
- `02-fail-and-impact/artifacts/impact_review.md`
- `summary.json`

Expected status flow:

- `phase1_gate=pass`
- `phase2_gate=fail`
- `phase3_gate=pass`

`impact_report.json` contains:

- `old_snapshot_id`
- `new_snapshot_id`
- `changed_evidence_ids`
- `impacted_case_ids`
- `details` with `case_id`, `matched_evidence_id`, `question`