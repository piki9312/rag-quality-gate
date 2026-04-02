# Phase2.5 Weekly Metrics Register

This file is the weekly transfer format for Phase2.5 hardening operation.
Update one row per week (or per workflow_dispatch run for ad-hoc checks).

## Metrics definition

- onboarding_time_minutes: WS1 baseline sheet の初回導入時間
- weekly_ops_time_minutes: WS1 baseline sheet の週次運用時間
- failure_action_coverage_rate: WS2 で action_owner と due_date が設定された fail 件数 / fail 総件数
- gate_exception_count: WS3 で status=active の例外件数
- overdue_exceptions_count: WS3 で期限超過かつ status=active の例外件数

## Weekly Evidence Minimum Set (fixed)

week_start ごとに「証跡あり」と判定する最小条件:

- E1 row existence:
	- 当該 week_start の行が Current records に 1 行以上ある
- E2 traceability:
	- run_id と run_url が空でない
- E3 metric completeness:
	- M1, M2, M3, M4, M5 がすべて記録されている
- E4 weekly threshold:
	- decision = keep-going
	- failure_action_coverage_rate >= 1.00
	- overdue_exceptions_count = 0

補足:

- 同じ week_start に複数行ある場合は、E4 を満たす行が 1 行以上あれば pass とする
- provisional exit decision 判定では、4 週連続で E1-E4 を満たすことを必須とする

## Weekly log template

| week_start | run_id | run_url | onboarding_time_minutes | weekly_ops_time_minutes | failure_action_coverage_rate | gate_exception_count | overdue_exceptions_count | decision | reviewer | notes |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| YYYY-MM-DD | 00000000000 | https://github.com/<owner>/<repo>/actions/runs/<id> | 0.00 | 0.00 | 1.00 | 0 | 0 | keep-going / investigate | owner-name | summary |

## Current records

| week_start | run_id | run_url | onboarding_time_minutes | weekly_ops_time_minutes | failure_action_coverage_rate | gate_exception_count | overdue_exceptions_count | decision | reviewer | notes |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- | --- | --- |
| 2026-03-28 | 23675763638 | https://github.com/piki9312/rag-quality-gate/actions/runs/23675763638 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going | piki9312 | initial Phase2.5 baseline from WS1 measurement, WS2 template kickoff, WS3 exception template kickoff |
| 2026-03-23 | 23676386099 | https://github.com/piki9312/rag-quality-gate/actions/runs/23676386099 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going | piki9312 | workflow_dispatch run; notes: WS1 baseline measured_date=2026-03-28, WS2 no failure rows this week, WS3 active=0 overdue=0 |
| 2026-03-23 | 23679795825 | https://github.com/piki9312/rag-quality-gate/actions/runs/23679795825 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going | piki9312 | WS1 baseline measured_date=2026-03-28, WS2 no failure rows this week, WS3 active=0, overdue=0 |
| 2026-03-23 | 23698940469 | https://github.com/piki9312/rag-quality-gate/actions/runs/23698940469 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going | piki9312 | WS1 baseline measured_date=2026-03-28, WS2 no failure rows this week, WS3 active=0, overdue=0 |
| 2026-03-16 | 23699562524 | https://github.com/piki9312/rag-quality-gate/actions/runs/23699562524 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going | piki9312 | WS1 baseline measured_date=2026-03-28, WS2 covered=1/1, WS3 active=0, overdue=0, week_start_override=2026-03-16 |
| 2026-03-09 | 23699721101 | https://github.com/piki9312/rag-quality-gate/actions/runs/23699721101 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going | piki9312 | WS1 baseline measured_date=2026-03-28, WS2 covered=1/1, WS3 active=0, overdue=0, week_start_override=2026-03-09 |
| 2026-03-23 | 23701914227 | https://github.com/piki9312/rag-quality-gate/actions/runs/23701914227 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going | piki9312 | WS1 baseline measured_date=2026-03-28, WS2 covered=1/1, WS3 active=0, overdue=0 |
| 2026-03-30 | 23731344346 | https://github.com/piki9312/rag-quality-gate/actions/runs/23731344346 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going | piki9312 | WS1 baseline measured_date=2026-03-28, WS2 covered=1/1, WS3 active=0, overdue=0 |
| 2026-03-30 | 23890613934 | https://github.com/piki9312/rag-quality-gate/actions/runs/23890613934 | 0.25 | 1.57 | 1.00 | 0 | 0 | keep-going | piki9312 | WS1 baseline measured_date=2026-03-28, WS2 no failure rows for week_start=2026-03-30, WS2 next_actions for week_start=2026-03-30: none, WS3 active=0, overdue=0, week_start_override=2026-03-30 |

## Update procedure

1. Collect WS1 time values from docs/ops/phase2-5-ws1-baseline-sheet.md.
2. Collect WS2 failure_action_coverage_rate from docs/ops/phase2-5-ws2-failure-review-template.md records.
3. Collect WS3 exception counts from docs/ops/phase2-5-ws3-gate-exception-approval-template.md records.
4. Run workflow Phase2.5 Weekly Hardening Metrics for run URL traceability.
5. Workflow automatically appends one row and creates a PR if register changed.
6. For local/manual fallback, run `python -m rqg.demo.phase2_5_weekly_metrics --append-register --reviewer <name>`.
7. If any metric violates expected range, set decision=investigate and open a follow-up issue.
8. For provisional exit decision, evaluate E1-E4 per week and confirm 4-week consecutive pass.

## CI artifact

- Workflow: .github/workflows/phase2-5-weekly-metrics.yml
- Artifact name: phase2-5-weekly-metrics
- Summary file: runs/phase2-5-weekly/summary.json
- Auto PR branch: automation/phase2-5-weekly-metrics-<run_id>

## Near-term Standard Operation

- failure action quality:
	- docs/ops/phase2-5-ws2-failure-review-template.md の Recommended Actions に従う
- investigate response:
	- docs/ops/phase2-5-investigate-response-flow.md のタイムラインで対応する
- exception strictness:
	- docs/ops/phase2-5-ws3-gate-exception-approval-template.md の Strict Controls を適用する
- case quality regular review:
	- .github/workflows/phase2-5-weekly-review-issue.yml で週次 issue を生成し
		docs/ops/phase2-5-case-quality-weekly-review.md を用いてレビューする
- onboarding / weekly ops accumulation:
	- weekly metrics workflow で summary を継続生成し、register の Current records へ蓄積する