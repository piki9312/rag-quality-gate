## Summary
Post-expiry cleanup for Issue #4. This PR removes legacy source_path compatibility in impact analysis and finalizes strict doc_id matching behavior after 2026-06-30.

## Scope
- [ ] Remove legacy alias expansion in impact analysis runtime
- [ ] Remove date-window guard for legacy compatibility
- [ ] Re-evaluate legacy fields in ImpactReport and review markdown
- [ ] Update tests for strict-only behavior
- [ ] Update docs for post-expiry operation

## Preconditions
- [ ] Confirm legacy_match_count == 0 in recent CI runs
- [ ] Confirm legacy_match_count == 0 in production-like operation data
- [ ] Attach evidence links for both checks

## Changes
### Runtime
- [ ] src/rqg/quality/impact_analysis.py
- [ ] src/rqg/domain/impact_report.py (if changed)
- [ ] src/rqg/presentation/markdown/impact_report_review.py (if changed)

### Tests
- [ ] tests/test_impact_analysis.py
- [ ] Related test files updated as needed

### Docs
- [ ] README.md
- [ ] docs/ops/phase2-migration-playbook.md
- [ ] docs/ops/phase2-weekly-metrics-register.md

## Validation
- [ ] pytest -q
- [ ] CI is green on PR
- [ ] Strict-only impact output checked manually
- [ ] No runtime path-based compatibility branch remains

## Risk and rollback
- Risk:
  - Potential false negatives if some cases still rely on path-based expected_evidence
- Rollback:
  - Revert this PR and continue migration-only operation

## Evidence
- Issue: https://github.com/piki9312/rag-quality-gate/issues/4
- Baseline/weekly metrics record: docs/ops/phase2-weekly-metrics-register.md
- First affected run URL:
  - [ ] <paste run url>

## Reviewer checklist
- [ ] Strict-only behavior is consistent across runtime, report, and docs
- [ ] Legacy compatibility code path is fully removed
- [ ] Migration operation remains executable after this change
