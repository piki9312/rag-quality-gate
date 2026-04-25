# Vendor PoC Quality Pack

This is a minimal English Quality Pack for the vendor-facing walkthrough:

- `documents/support_policy.md`: source document for the local RAG demo.
- `cases.csv`: two active cases, including one intentional S1 keyword mismatch.
- `gate.yml`: lightweight gate thresholds.
- `quality-pack.yml`: pack metadata and next-action hints.

The S1 case intentionally expects `security owner hotline`, which is not present in the policy. This makes the walkthrough demonstrate how to read an S1 failure without requiring a real customer endpoint or secrets.
