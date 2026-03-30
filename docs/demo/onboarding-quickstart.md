# Onboarding Quickstart Demo

This is the shortest first-time onboarding path for Phase 2.

## Goal

Run a single flow end-to-end:

1. ingest
2. gen-cases
3. eval
4. check
5. impact
6. review output

This flow is the baseline for internal-documents assistant AI where document updates can change answers silently.

## Command

Run from repository root.

Bash (macOS/Linux):

```bash
python -m rqg.demo.onboarding_quickstart
```

PowerShell (Windows):

```powershell
python -m rqg.demo.onboarding_quickstart
```

## Expected output

Artifacts are written under:

`demo_runs/onboarding_quickstart/<run-id>/`

Key files:

- `artifacts/old_snapshot.json`
- `artifacts/new_snapshot.json`
- `artifacts/eval_cases.json`
- `artifacts/eval_cases_review.md`
- `artifacts/impact_report.json`
- `artifacts/impact_review.md`
- `summary.json`

Expected summary values:

- `gate_status=pass`
- `changed_evidence_count >= 1`
- `impacted_case_count >= 1`

## Notes

- This demo is designed for first-time users and keeps commands minimal.
- It uses the `packs/demo_cycle` sample pack and writes all outputs to `demo_runs/`.
- In production, start from `templates/sample_pack` and tune cases for your internal policy/FAQ/procedure documents.
