## Monthly Quality Summary

- Month start: 2026-04-01
- Total runs: 3
- Blocked runs: 1
- S1 incidents detected: 2
- Fallback trend: judge_runs=1 judge_count=1 embedding_runs=0 embedding_count=0
- Trend summary: Overall pass rate 100.0% -> 100.0%; S1 pass rate 100.0% -> 100.0%; latest status=PASS

### Top Reasons

| Reason | Count |
|---|---|
| S1 pass rate: 66.7 < 100.0 (4/6) | 1 |
| Refund policy S1 case failed: digital product refund was incorrectly allowed | 1 |
| This block is caused by business-risk answer quality, not evaluator fallback | 1 |
| Judge fallback detected; re-run evaluation and verify judge/API connectivity before release | 1 |
| Human review required because run reliability signals were degraded | 1 |

### Unresolved Issues

- Human review required because run reliability signals were degraded
- Judge fallback detected; re-run evaluation and verify judge/API connectivity before release
- This review state is caused by evaluator reliability, not a confirmed business-rule violation

### Resolved Issues

- Refund policy S1 case failed: digital product refund was incorrectly allowed
- S1 pass rate: 66.7 < 100.0 (4/6)
- This block is caused by business-risk answer quality, not evaluator fallback

### Recommended Actions

| Failure Category | Count | Action |
|---|---|---|
| judge_fallback_used | 1 | Re-run judge-enabled evaluation and route this run to the quality owner if fallback repeats |
