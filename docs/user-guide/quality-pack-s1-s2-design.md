# Quality Pack S1/S2 Design Guide

This guide explains how to assign `severity` in `cases.csv` when building a Quality Pack for customer-facing RAG/FAQ agents.

`validate-pack` reports these checks as warnings first. The goal is to catch design mistakes early without breaking existing packs.

## Severity Meaning

| Severity | Meaning | Typical use |
| --- | --- | --- |
| `S1` | Production-blocking case. A failure should stop release or require explicit approval. | High-risk answers where a wrong response can harm trust, compliance, HR/labor handling, escalation, or customer accountability. |
| `S2` | Standard regression case. A failure should be reviewed and fixed, but usually does not block every release by itself. | Normal FAQ wording, coverage checks, low-risk policy details, or secondary flows. |

Use `S1` sparingly but deliberately. A pack with no S1 cases has a weak blocking gate; a pack where every case is S1 can become too heavy to operate.

## Recommended S1 Shape

Each active `S1` case should usually include:

- `expected_answer`: the short customer-approved answer.
- `expected_evidence` or legacy `expected_chunks`: the document section or chunk that grounds the answer.
- `expected_keywords`: 2-5 business-critical terms that catch obvious answer drift.
- `category`: a useful risk category such as `deadline`, `eligibility`, `procedure`, `exception`, or `escalation`.

Example:

```csv
case_id,severity,eval_mode,question,expected_answer,expected_evidence,expected_keywords,category
HR001,S1,evidence_keyword,When must paid leave be requested?,Paid leave requests must be submitted 5 business days in advance.,leave_policy.md#sec-1,paid leave;5 business days;advance request,deadline
```

## validate-pack Warnings

`validate-pack` warns about these S1/S2 design risks:

- `Quality Pack has 0 active S1 cases.`
- `Quality Pack has only 1 S1 case across ... active cases.`
- `S1 case has no expected_answer.`
- `S1 case has no expected_evidence.`
- `S1 case has no expected_keywords.`
- `All active cases are S1.`
- `All active cases are S2.`
- `Category coverage is concentrated in ...`

Warnings do not change the exit code unless there are existing validation errors. Treat them as onboarding guidance for improving the Quality Pack before monthly operation.

## Practical Starting Point

For the first customer pack, start with:

- 3-5 `S1` cases covering the highest-risk customer promises.
- 10-30 `S2` cases covering broader regression behavior.
- At least 3 categories so the pack is not dominated by one workflow.
- One reviewer-owned S1 case for each major failure mode: retrieval miss, wrong deadline, unsupported answer, and escalation/contact mistake.
