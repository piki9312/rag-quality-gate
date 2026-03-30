# Fail Fix Pass Demo

This demo fixes one reproducible quality-gate cycle around a single document and a single case.

## Goal

Run the system in three phases:

1. pass with the expected document
2. fail after breaking the document content
3. pass again after restoring the document

This demonstrates the release-gate behavior for internal-document updates:

- fail blocks unsafe release
- fix evidence is required before unblocking

## Command

Run from the repository root:

```bash
python -m rqg.demo.fail_fix_cycle
```

## What it does

- uses `packs/demo_cycle/` as the source pack
- writes a working copy under `demo_runs/fail_fix_cycle/pack`
- runs `rqg eval ... --mock`
- runs `rqg check ... --decision-file ...`
- rewrites the document once to force a gate failure
- restores the document and verifies recovery

## Expected outcome

The summary file is written under a run-specific directory:

`demo_runs/fail_fix_cycle/<run-id>/summary.json`

Expected statuses:

- `01-pass`: `pass`
- `02-fail`: `fail`
- `03-pass`: `pass`

Operational meaning:

- `02-fail` should trigger review and action assignment
- `03-pass` provides evidence for release resume

Each phase also leaves:

- gate report markdown
- gate decision json
- run logs
- document snapshots
