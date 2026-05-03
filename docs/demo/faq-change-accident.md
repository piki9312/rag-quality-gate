# FAQ Change Accident Demo

This page is kept as a short pointer after the PoC demo assets were reorganized.

Use these locations instead:

- PoC runbook: [../user-guide/proof-gate-poc.md](../user-guide/proof-gate-poc.md)
- Demo assets: [../../demos/customer_support_faq_change/README.md](../../demos/customer_support_faq_change/README.md)
- Sales draft: [../sales/customer-support-faq-change-demo.md](../sales/customer-support-faq-change-demo.md)

The FAQ source files, generated demo cases, runnable demo cases, case summary, and before / after reports now live under `demos/customer_support_faq_change/`.

## Runtime Severity Note

`case_set_summary.json` separates PoC selection bands from runtime severities. `S3` is a selection/classification band for the PoC case set, not a new runtime severity. The formal `cases.csv` schema continues to emit only the existing runtime severities; S3-selected cases are written as `severity=S2` and keep `poc_band:S3` in `notes` so the selection rationale remains auditable.
