# Phase2 Weekly Metrics Register

This file is the weekly transfer format for Phase2 migration operation.
Update one row per week (or per workflow_dispatch run for ad-hoc checks).

## Metrics definition

- legacy_match_count: value from impact compatibility report
- unresolved_legacy_refs: value from migrate-cases report
- strict_only_impacted_case_count: count of impacted_case_ids in strict-only report

## Weekly log template

| week_start | run_id | run_url | legacy_match_count | unresolved_legacy_refs | strict_only_impacted_case_count | decision | reviewer | notes |
| --- | --- | --- | ---: | ---: | ---: | --- | --- | --- |
| YYYY-MM-DD | 00000000000 | https://github.com/<owner>/<repo>/actions/runs/<id> | 0 | 0 | 1 | keep-going / investigate | owner-name | summary |

## Current records

| week_start | run_id | run_url | legacy_match_count | unresolved_legacy_refs | strict_only_impacted_case_count | decision | reviewer | notes |
| --- | --- | --- | ---: | ---: | ---: | --- | --- | --- |
| 2026-03-28 | 23674931038 | https://github.com/piki9312/rag-quality-gate/actions/runs/23674931038 | 0 | 0 | 1 | keep-going | piki9312 | initial workflow_dispatch baseline |

## Update procedure

1. Run workflow `Phase2 Weekly Migration Metrics` (schedule or workflow_dispatch).
2. Download artifact `phase2-weekly-metrics` and open `summary.json`.
3. Copy values into the table above.
4. If any metric violates expected range, add `decision=investigate` and open a follow-up issue.
