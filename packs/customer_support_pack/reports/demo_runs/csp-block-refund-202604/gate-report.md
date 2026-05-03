## Proof Gate Demo Run: BLOCK

- Run ID: csp-block-refund-202604
- Pack: Customer Support AI Quality Pack
- Legacy status: FAIL
- Policy status: BLOCK
- S1 fail count: 2
- Judge reliability: HIGH
- Fallback used: NO

### Reasons

- S1 pass rate: 66.7 < 100.0 (4/6)
- Refund policy S1 case failed: digital product refund was incorrectly allowed
- This block is caused by business-risk answer quality, not evaluator fallback

### Next Actions

- answer_quality_fail: Fix refund and cancellation answers, then rerun the gate before customer release
