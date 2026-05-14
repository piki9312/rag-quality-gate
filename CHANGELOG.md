# Changelog

## Unreleased

- Hardened CI-safe reporting for customer PoC use.
- Limited `rqg gate --report-mode ci` stdout to aggregate summaries.
- Split CI report artifacts into `gate-report-ci.md` and `gate-report-ci.json`.
- Restricted CI `gate-report-ci.json` case rows to safe metadata and hashed case IDs.
- Restricted CI `gate-decision.json` reasons to a fixed safe taxonomy, with free-form values rounded to `unknown_failure`.
- Updated customer template workflow artifact uploads to an allowlist with short retention.
- Renamed customer-facing retrieval metrics to expected evidence recall/hit-rate wording while keeping the old `retrieval_precision` key as a read-only compatibility alias.
- Clarified S1/S2/judge fallback policy mapping for customer-facing reports.
