## Proof Gate Demo Run: NEEDS_HUMAN_REVIEW

- Run ID: csp-needs-review-fallback-202604
- Pack: Customer Support AI Quality Pack
- Legacy status: PASS
- Policy status: NEEDS_HUMAN_REVIEW
- S1 fail count: 0
- Judge reliability: LOW
- Fallback used: YES

### Reasons

- Judge fallback detected; re-run evaluation and verify judge/API connectivity before release
- Human review required because run reliability signals were degraded
- This review state is caused by evaluator reliability, not a confirmed business-rule violation

### Next Actions

- judge_fallback_used: Re-run judge-enabled evaluation and route this run to the quality owner if fallback repeats
