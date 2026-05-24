from __future__ import annotations

from pathlib import Path

from rqg.case_assets import load_case_intent_registry
from rqg.case_draft import CaseDraftEngine, SourceSection


def _sample_intent():
    registry = load_case_intent_registry(Path("assets/case_intents"))
    return registry.require("refund_mid_contract_cancellation")


def test_creates_needs_review_draft() -> None:
    draft = CaseDraftEngine().create_draft_from_intent(_sample_intent())

    assert draft.status == "needs_review"


def test_uses_first_question_variation() -> None:
    intent = _sample_intent()

    draft = CaseDraftEngine().create_draft_from_intent(intent)

    assert draft.question == intent.question_variations[0].template


def test_uses_expected_behavior_template_as_draft_answer() -> None:
    intent = _sample_intent()

    draft = CaseDraftEngine().create_draft_from_intent(intent)

    assert draft.expected_answer == intent.expected_behavior_template


def test_includes_required_notes_markers() -> None:
    intent = _sample_intent()

    draft = CaseDraftEngine().create_draft_from_intent(intent)

    assert "generated_by:case_draft_engine" in draft.notes
    assert "case_type:generated-draft" in draft.notes
    assert f"intent:{intent.intent_id}" in draft.notes
    assert f"pattern:{intent.failure_patterns[0]}" in draft.notes


def test_does_not_output_active() -> None:
    draft = CaseDraftEngine().create_draft_from_intent(_sample_intent())

    assert draft.status != "active"


def test_includes_evidence_requirement() -> None:
    draft = CaseDraftEngine().create_draft_from_intent(_sample_intent())

    assert "refund_policy" in draft.expected_evidence
    assert "contract_terms" in draft.expected_evidence


def test_source_section_marker() -> None:
    source_section = SourceSection(
        section_id="refund-policy#sec-1",
        text="契約途中解約時の返金条件",
        source_ref="docs/refund_policy.md#sec-1",
    )

    draft = CaseDraftEngine().create_draft_from_intent(
        _sample_intent(),
        source_section=source_section,
    )

    assert "source:refund-policy#sec-1" in draft.notes
    assert "docs/refund_policy.md#sec-1" in draft.expected_evidence


def test_integration_with_sample_intent() -> None:
    registry = load_case_intent_registry(Path("assets/case_intents"))
    intent = registry.require("refund_mid_contract_cancellation")

    draft = CaseDraftEngine().create_draft_from_intent(intent)

    assert draft.case_id == "DRAFT-refund_mid_contract_cancellation"
    assert draft.category == "refund"
    assert draft.severity == "S1"
