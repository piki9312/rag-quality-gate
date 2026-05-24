from __future__ import annotations

import shutil
import uuid
from pathlib import Path

from rqg.case_assets import load_case_intent_registry
from rqg.case_draft import (
    CaseDraftPlanner,
    SourceSection,
)
from rqg.case_draft.planner import create_drafts_for_affected_categories

SAMPLE_INTENT = """\
intent_id: {intent_id}
version: 0.1.0
status: experimental
domain: customer_support
risk_category: {risk_category}
failure_patterns:
  - {failure_pattern}
case_intent: 契約途中解約時の返金可否を確認する
severity_hint: {severity_hint}
question_variations:
  - variation_type: direct
    template: 契約途中で解約した場合、返金されますか？
expected_behavior_template: >
  最新の返金・契約条件に基づき、返金可否、例外条件、人間確認要否を案内する。
evidence_requirement:
  - refund_policy
coverage_rule:
  required_when:
    affected_business_categories:
{affected_categories}
    change_types:
      - document_update
  minimum_active_cases:
    any: 1
    s1_or_s2: 1
safe_summary:
  label_ja: 途中解約時の返金可否
  description_ja: 返金可否・例外条件・人間確認要否を確認する高リスクケース意図
"""


def _workspace_tmp() -> Path:
    root = Path("tests/.tmp") / f"case-draft-planner-{uuid.uuid4()}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _affected_categories_yaml(categories: list[str]) -> str:
    return "\n".join(f"      - {category}" for category in categories)


def _intent_yaml(
    *,
    intent_id: str,
    risk_category: str = "refund",
    failure_pattern: str = "refund_rule_reversal",
    severity_hint: str = "S1",
    affected_categories: list[str] | None = None,
) -> str:
    return SAMPLE_INTENT.format(
        intent_id=intent_id,
        risk_category=risk_category,
        failure_pattern=failure_pattern,
        severity_hint=severity_hint,
        affected_categories=_affected_categories_yaml(affected_categories or ["refund"]),
    )


def _write_intent(root: Path, name: str, content: str) -> None:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_creates_drafts_from_affected_categories() -> None:
    registry = load_case_intent_registry(Path("assets/case_intents"))
    planner = CaseDraftPlanner(registry)

    drafts = planner.create_drafts_for_affected_categories(["refund"])

    assert len(drafts) >= 1
    assert drafts[0].status == "needs_review"
    assert "intent:refund_mid_contract_cancellation" in drafts[0].notes
    assert "generated_by:case_draft_engine" in drafts[0].notes


def test_empty_categories_returns_empty_list() -> None:
    registry = load_case_intent_registry(Path("assets/case_intents"))

    assert CaseDraftPlanner(registry).create_drafts_for_affected_categories([]) == []


def test_unknown_category_returns_empty_list() -> None:
    registry = load_case_intent_registry(Path("assets/case_intents"))

    assert CaseDraftPlanner(registry).create_drafts_for_affected_categories(["pricing"]) == []


def test_duplicate_categories_do_not_duplicate_drafts() -> None:
    registry = load_case_intent_registry(Path("assets/case_intents"))

    drafts = CaseDraftPlanner(registry).create_drafts_for_affected_categories(
        ["refund", "contract_terms"]
    )

    assert [draft.case_id for draft in drafts] == ["DRAFT-refund_mid_contract_cancellation"]


def test_stable_order() -> None:
    root = _workspace_tmp()
    try:
        _write_intent(root, "z.yml", _intent_yaml(intent_id="z_case"))
        _write_intent(root, "a.yml", _intent_yaml(intent_id="a_case"))
        registry = load_case_intent_registry(root)

        drafts = CaseDraftPlanner(registry).create_drafts_for_affected_categories(["refund"])

        assert [draft.case_id for draft in drafts] == ["DRAFT-a_case", "DRAFT-z_case"]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_source_section_is_propagated() -> None:
    registry = load_case_intent_registry(Path("assets/case_intents"))
    source_section = SourceSection(
        section_id="refund-policy#sec-1",
        text="契約途中解約時の返金条件",
        source_ref="docs/refund_policy.md#sec-1",
    )

    drafts = create_drafts_for_affected_categories(
        registry,
        ["refund"],
        source_section=source_section,
    )

    assert "source:refund-policy#sec-1" in drafts[0].notes
    assert "docs/refund_policy.md#sec-1" in drafts[0].expected_evidence


def test_does_not_output_active() -> None:
    registry = load_case_intent_registry(Path("assets/case_intents"))

    drafts = CaseDraftPlanner(registry).create_drafts_for_affected_categories(["refund"])

    assert drafts
    assert all(draft.status != "active" for draft in drafts)
