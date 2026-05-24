from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest

from rqg.case_assets import (
    CaseIntentLibraryError,
    CaseIntentRegistry,
    load_case_intent_registry,
    load_case_intents,
)

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
    root = Path("tests/.tmp") / f"case-intent-registry-{uuid.uuid4()}"
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


def _write_intent(root: Path, name: str, content: str) -> Path:
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_registry_loads_from_sample_path() -> None:
    registry = load_case_intent_registry(Path("assets/case_intents"))

    intent = registry.get("refund_mid_contract_cancellation")
    assert intent is not None
    assert intent.risk_category == "refund"
    assert registry.require("refund_mid_contract_cancellation") == intent


def test_all_returns_stable_intent_id_order() -> None:
    root = _workspace_tmp()
    try:
        _write_intent(root, "z.yml", _intent_yaml(intent_id="z_case"))
        _write_intent(root, "a.yml", _intent_yaml(intent_id="a_case"))

        registry = load_case_intent_registry(root)

        assert [intent.intent_id for intent in registry.all()] == ["a_case", "z_case"]
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_get_and_require() -> None:
    registry = load_case_intent_registry(Path("assets/case_intents"))

    assert registry.get("refund_mid_contract_cancellation") is not None
    assert registry.get("unknown_intent") is None
    with pytest.raises(CaseIntentLibraryError, match="Unknown case intent: unknown_intent"):
        registry.require("unknown_intent")


def test_registry_rejects_duplicate_intent_id_when_constructed_directly() -> None:
    intents = load_case_intents(Path("assets/case_intents/customer_support/refund.yml"))

    with pytest.raises(CaseIntentLibraryError, match="Duplicate Case Intent id"):
        CaseIntentRegistry([intents[0], intents[0]])


def test_find_by_risk_category() -> None:
    registry = load_case_intent_registry(Path("assets/case_intents"))

    assert [intent.intent_id for intent in registry.find_by_risk_category("refund")] == [
        "refund_mid_contract_cancellation"
    ]
    assert registry.find_by_risk_category("pricing") == []


def test_find_by_failure_pattern() -> None:
    registry = load_case_intent_registry(Path("assets/case_intents"))

    assert [
        intent.intent_id for intent in registry.find_by_failure_pattern("refund_rule_reversal")
    ] == ["refund_mid_contract_cancellation"]
    assert [intent.intent_id for intent in registry.find_by_failure_pattern("stale_reference")] == [
        "refund_mid_contract_cancellation"
    ]
    assert registry.find_by_failure_pattern("unknown_pattern") == []


def test_find_by_severity_hint() -> None:
    registry = load_case_intent_registry(Path("assets/case_intents"))

    assert [intent.intent_id for intent in registry.find_by_severity_hint("S1")] == [
        "refund_mid_contract_cancellation"
    ]
    assert registry.find_by_severity_hint("S4") == []
    assert registry.find_by_severity_hint("critical") == []


def test_find_by_affected_business_category() -> None:
    registry = load_case_intent_registry(Path("assets/case_intents"))

    assert [
        intent.intent_id for intent in registry.find_by_affected_business_category("refund")
    ] == ["refund_mid_contract_cancellation"]
    assert [
        intent.intent_id for intent in registry.find_by_affected_business_category("contract_terms")
    ] == ["refund_mid_contract_cancellation"]
    assert registry.find_by_affected_business_category("pricing") == []


def test_find_candidates_for_affected_categories_deduplicates_results() -> None:
    registry = load_case_intent_registry(Path("assets/case_intents"))

    candidates = registry.find_candidates_for_affected_categories(["refund", "contract_terms"])

    assert [intent.intent_id for intent in candidates] == ["refund_mid_contract_cancellation"]


def test_find_candidates_for_empty_categories_returns_empty_list() -> None:
    registry = load_case_intent_registry(Path("assets/case_intents"))

    assert registry.find_candidates_for_affected_categories([]) == []
