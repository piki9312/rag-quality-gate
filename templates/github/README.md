# GitHub Actions templates for RQG

Copy `templates/github/workflows/rqg-reusable-gate.yml` into `.github/workflows/rqg-reusable-gate.yml` first.
Then copy one caller workflow into `.github/workflows/` in the target repository.

- `rqg-gate-mock.yml`: local/mock smoke gate for first-day onboarding
- `rqg-gate-external.yml`: external HTTP RAG validation + gate run
- `rqg-gate-external-notify.yml`: external gate with Slack notification hook
- `rqg-gate-weekly-review.yml`: reusable gate + downstream weekly review issue/Slack follow-up example

The reusable workflow exposes these job outputs for downstream jobs and deploy gates:

- `gate_status`
- `gate_run_id`
- `gate_decision_path`
- `gate_report_path`
- `gate_report_json_path`
- `pack_validation_ok`
- `pack_validation_path`
- `connection_ok`
- `connection_validation_path`
- `gate_history_summary_path`

Minimal setup checklist:

1. Replace `rqg_install_command` with your package source.
2. Turn on `run_pack_validation: true` and set `pack_dir` so misconfigured packs fail before eval/check.
3. Prefer `pack_validation_preset` for common caller profiles: `local_docs`, `external`, or `external_notify`.
4. Add `pack_required_env` only when you need repo-specific env checks beyond the preset.
5. Set `RAG_API_ENDPOINT` and `RAG_API_KEY` secrets for external mode.
6. Set `RQG_SLACK_WEBHOOK_URL` or map `notification_webhook_url` for notify mode.
7. Gate follow-up jobs on `needs.<job-id>.outputs.gate_status == 'pass'`.

When `run_pack_validation` is enabled, the reusable workflow runs `rqg validate-pack` before connection validation or gate execution. `pack_validation_preset` expands the common env requirements for each caller profile, `pack_required_env` appends repo-specific env names, and the workflow writes `pack-validation.json` into `log_dir/`, surfaces `pack_validation_ok` / `pack_validation_path` as workflow outputs, and adds top findings to the GitHub job summary.

The reusable workflow uses GitHub-hosted runners for sample/mock/dummy data only. CI artifacts are allowlisted and safe-metadata-only: `gate-report-ci.md`, `gate-report-ci.json`, `gate-decision.json`, and `gate-history-summary.json`. Full `gate-report.md`, full `gate-report.json`, raw JSONL logs, vector index files, `index/meta.json`, `faiss.index`, raw questions, raw answers, evidence text, source paths, endpoints, and token-like strings are forbidden artifacts. Full evidence belongs only in local, private runner, or customer-controlled environments.

If you need change metadata for release review, copy `../change-event.example.yml` to `change-event.yml` in a local or customer-controlled workspace and pass `--change-event change-event.yml` to `rqg gate` or `rqg check`. Do not put raw customer names, raw document names, absolute paths, `target_release`, or customer-specific summaries into GitHub-hosted CI runs. CI-safe artifacts should expose only hashes, counts, and bounded metadata.

`gate-report-ci.json`, `gate-decision.json`, and `gate-history-summary.json` are CI-safe variants. They keep aggregate status, pass rates, S1 failure counts, reason codes, execution mode, run ID, and safe artifact references, while omitting customer/app/tenant names, raw case text, owner/steward names, source references, endpoints, and internal paths. Artifact retention is intentionally short (`7` days).

The weekly review example downloads the uploaded gate artifacts, prefers the CI-safe report bundle via `gate_report_json_path`, falls back to `gate-history-summary.json` when needed, and shows how to upsert a GitHub issue plus send an optional Slack Block Kit summary based on the exported payload.

For triage board linking, set these repository secrets when you use a GitHub Project v2 board:

1. `RQG_TRIAGE_PROJECT_ID`
2. `RQG_TRIAGE_STATUS_FIELD_ID` (optional)
3. `RQG_TRIAGE_STATUS_OPTION_ID` (optional)

The exporter and example workflow align weekly review issues to the repo convention title `[Phase2.5][Weekly Review] YYYY-MM-DD` and default labels `phase2-5`, `weekly-review`, `ops`.

These templates stay intentionally small. The reusable workflow centralizes the operational contract so callers do not drift on notification, connection validation, artifact upload, and gate output handling.
