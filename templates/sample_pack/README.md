# Sample Pack Template

This template can be copied into your own repository to bootstrap RQG.

Included files:

- documents/leave_policy.md
- cases.csv
- gate.yml
- reports/example-impact-report.json

Quick usage:

1. Copy this folder into your workspace as `packs/my_pack/`.
2. Run:
   - `rqg ingest packs/my_pack/documents --index-dir index`
   - `rqg eval packs/my_pack/cases.csv --docs packs/my_pack/documents --mock --index-dir index --log-dir runs/quality`
   - `rqg check --log-dir runs/quality --config packs/my_pack/gate.yml`
3. For onboarding smoke, use `python -m rqg.demo.onboarding_quickstart`.
