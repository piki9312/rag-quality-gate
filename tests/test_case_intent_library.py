from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import pytest

from rqg.case_assets import CaseIntentLibraryError, load_case_intents


SAMPLE_INTENT = """\
intent_id: refund_mid_contract_cancellation
version: 0.1.0
status: experimental
domain: customer_support
risk_category: refund
failure_patterns:
  - refund_rule_reversal
  - stale_reference
case_intent: 契約途中解約時の返金可否を確認する
severity_hint: S1
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
      - refund
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
    root = Path("tests/.tmp") / f"case-intents-{uuid.uuid4()}"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _write_intent(path: Path, content: str = SAMPLE_INTENT) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_valid_sample_yaml_loads() -> None:
    intents = load_case_intents(Path("assets/case_intents/customer_support/refund.yml"))

    assert len(intents) == 1
    intent = intents[0]
    assert intent.intent_id == "refund_mid_contract_cancellation"
    assert intent.risk_category == "refund"
    assert intent.severity_hint == "S1"
    assert len(intent.question_variations) == 3
    assert intent.coverage_rule.minimum_active_cases.any == 1
    assert "refund" in intent.coverage_rule.required_when.affected_business_categories
    assert intent.safe_summary.label_ja == "途中解約時の返金可否"


def test_directory_loads_yaml_recursively_in_stable_order() -> None:
    root = _workspace_tmp()
    try:
        _write_intent(root / "z" / "second.yml", SAMPLE_INTENT.replace(
            "refund_mid_contract_cancellation", "z_refund_case"
        ))
        _write_intent(root / "a" / "first.yaml", SAMPLE_INTENT.replace(
            "refund_mid_contract_cancellation", "a_refund_case"
        ))

        first_load = [intent.intent_id for intent in load_case_intents(root)]
        second_load = [intent.intent_id for intent in load_case_intents(root)]

        assert first_load == ["a_refund_case", "z_refund_case"]
        assert second_load == first_load
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_duplicate_intent_id_rejected() -> None:
    root = _workspace_tmp()
    try:
        _write_intent(root / "one.yml")
        _write_intent(root / "two.yml")

        with pytest.raises(CaseIntentLibraryError, match="Duplicate Case Intent id"):
            load_case_intents(root)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_invalid_status_rejected() -> None:
    root = _workspace_tmp()
    try:
        path = _write_intent(root / "invalid.yml", SAMPLE_INTENT.replace(
            "status: experimental", "status: approved"
        ))

        with pytest.raises(CaseIntentLibraryError, match="status"):
            load_case_intents(path)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_invalid_severity_rejected() -> None:
    root = _workspace_tmp()
    try:
        path = _write_intent(root / "invalid.yml", SAMPLE_INTENT.replace(
            "severity_hint: S1", "severity_hint: critical"
        ))

        with pytest.raises(CaseIntentLibraryError, match="severity_hint"):
            load_case_intents(path)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_missing_question_variations_rejected() -> None:
    root = _workspace_tmp()
    try:
        path = _write_intent(root / "invalid.yml", SAMPLE_INTENT.replace(
            "question_variations:\n"
            "  - variation_type: direct\n"
            "    template: 契約途中で解約した場合、返金されますか？",
            "question_variations: []",
        ))

        with pytest.raises(CaseIntentLibraryError, match="question_variations"):
            load_case_intents(path)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def test_expected_answer_rejected() -> None:
    root = _workspace_tmp()
    try:
        content = SAMPLE_INTENT.replace(
            "expected_behavior_template: >",
            "expected_answer: 顧客固有の正解\nexpected_behavior_template: >",
        )
        path = _write_intent(root / "invalid.yml", content)

        with pytest.raises(CaseIntentLibraryError, match="expected_answer"):
            load_case_intents(path)
    finally:
        shutil.rmtree(root, ignore_errors=True)
