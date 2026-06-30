# Diagnostic PoC Internal Checklist

## Purpose

This checklist is for the team running a `RAG/FAQ Bot Pre-Release Diagnostic
PoC`. Use it before, during, and after the PoC to keep scope, data boundaries,
and review responsibilities clear.

## Scope And Boundary

- [ ] Target bot, target release, and review stage are defined.
- [ ] The PoC is framed as review evidence, not quality warranty.
- [ ] Customer raw data storage location is agreed.
- [ ] Full/private artifacts are kept in local, private, or customer-controlled
      storage.
- [ ] Customer-facing output mode is safe or redacted unless explicitly agreed.
- [ ] Case Intent Library is treated as non-runtime design input.
- [ ] Active formal `cases.csv` is the only runtime source of truth.

## Case Design

- [ ] S1 domains are selected: refund, cancellation, pricing, contract terms,
      eligibility, deadline, procedure, or support policy.
- [ ] S1 Case Intent candidates are selected only as review perspectives.
- [ ] Generated or drafted cases remain `needs_review`.
- [ ] Human review confirms question, expected_answer, expected_evidence,
      severity, eval_mode, and block_reason.
- [ ] Only approved cases are added to active `cases.csv`.
- [ ] S1 active cases include owner, last_reviewed_at, min_case_score, evidence,
      and failure pattern notes.
- [ ] `answer_status:vendor-approved` is used only after review.

## Execution

- [ ] `rqg validate-pack` is run before evaluation.
- [ ] `rqg eval` is run with the agreed mock/local/external RAG mode.
- [ ] `rqg gate` is run with gate config and change-event where applicable.
- [ ] Gate output is reviewed for S1 failures, overall pass rate, evidence
      recall, and human-review status.
- [ ] Review Packet and customer summary are generated in the correct mode.

## Customer Communication

Avoid these phrases:

- "Quality is guaranteed."
- "This is safe."
- "Production release is automatically approved."
- "There is no legal or compliance risk."
- "AI makes the final decision."

Recommended phrases:

- "Within this review scope..."
- "As a high-risk review candidate..."
- "As evidence for human review..."
- "Before production release, confirm..."
- "This is equivalent to BLOCK in the Release Gate."

譌･譛ｬ隱槭〒縺ｮ謗ｨ螂ｨ陦ｨ迴ｾ:

- 縲御ｻ雁屓縺ｮ遽・峇縺ｧ縺ｯ縲・- 縲碁㍾螟ｧ繝ｪ繧ｹ繧ｯ蛟呵｣懊→縺励※縲・- 縲御ｺｺ髢薙Ξ繝薙Η繝ｼ縺ｮ蛻､譁ｭ譚先侭縺ｨ縺励※縲・- 縲梧悽逡ｪ蜿肴丐蜑阪↓遒ｺ隱阪☆縺ｹ縺崎ｨｼ霍｡縺ｨ縺励※縲・- 縲軍elease Gate荳翫・BLOCK逶ｸ蠖薙〒縺吶・
## Deliverables

- [ ] Review Packet.
- [ ] `gate-report.md`.
- [ ] `gate-report.json`.
- [ ] `customer-summary.md`.
- [ ] S1/S2 major risk list.
- [ ] Recommended remediation memo.
- [ ] Follow-up proposal for change review or monthly monitor.

## Post-PoC

- [ ] Decide whether this becomes remediation support, change review, or monthly
      monitor.
- [ ] Do not move customer-specific expected answers into shared assets.
- [ ] Capture only reusable, abstract learnings into Case Intent / Failure
      Pattern docs.
- [ ] Confirm whether additional S1/S2 cases should be reviewed before the next
      release.
