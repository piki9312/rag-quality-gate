# Vendor PoC Quality Pack

This is the passing scenario for the vendor-facing walkthrough:

- `documents/support_policy.md`: source document for the local RAG demo.
- `cases.csv`: two active cases aligned to the policy text so the pack can pass under `--mock`.
- `gate.yml`: lightweight gate thresholds.
- `quality-pack.yml`: pack metadata and next-action hints.

The S1 case is aligned to the documented password-reset procedure, so `rqg gate --pack examples/vendor-poc-pack-pass --mock` demonstrates a clean PASS report and Executive Summary.
