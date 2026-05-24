from __future__ import annotations

from pathlib import Path

from rqg.case_assets import load_case_intent_registry
from rqg.case_draft import CaseDraftPlanner, SourceSection, SourceSectionMatcher


def _sample_intent():
    registry = load_case_intent_registry(Path("assets/case_intents"))
    return registry.require("refund_mid_contract_cancellation")


def test_matches_by_section_id() -> None:
    section = SourceSection(
        section_id="refund_policy_v2",
        text="general content",
        source_ref=None,
    )

    selected = SourceSectionMatcher().select_for_intent(_sample_intent(), [section])

    assert selected == section


def test_matches_by_source_ref() -> None:
    section = SourceSection(
        section_id="policy_section",
        text="general content",
        source_ref="docs/contract_terms.md",
    )

    selected = SourceSectionMatcher().select_for_intent(_sample_intent(), [section])

    assert selected == section


def test_matches_by_text() -> None:
    section = SourceSection(
        section_id="section-1",
        text="This section describes refund_policy details.",
        source_ref=None,
    )

    selected = SourceSectionMatcher().select_for_intent(_sample_intent(), [section])

    assert selected == section


def test_chooses_highest_score() -> None:
    text_match = SourceSection(
        section_id="section-1",
        text="refund_policy appears in body only",
        source_ref=None,
    )
    section_id_match = SourceSection(
        section_id="refund_policy_v2",
        text="body",
        source_ref=None,
    )

    selected = SourceSectionMatcher().select_for_intent(
        _sample_intent(),
        [text_match, section_id_match],
    )

    assert selected == section_id_match


def test_returns_none_when_no_match() -> None:
    section = SourceSection(
        section_id="pricing",
        text="pricing content",
        source_ref="docs/pricing.md",
    )

    assert SourceSectionMatcher().select_for_intent(_sample_intent(), [section]) is None


def test_empty_sections_returns_none() -> None:
    assert SourceSectionMatcher().select_for_intent(_sample_intent(), []) is None


def test_planner_creates_drafts_with_matched_sections() -> None:
    registry = load_case_intent_registry(Path("assets/case_intents"))
    section = SourceSection(
        section_id="refund_policy_v2",
        text="refund_policy details",
        source_ref="docs/refund_policy.md",
    )

    drafts = CaseDraftPlanner(registry).create_drafts_for_affected_categories_with_sections(
        ["refund"],
        [section],
    )

    assert len(drafts) == 1
    assert "source:refund_policy_v2" in drafts[0].notes
    assert "docs/refund_policy.md" in drafts[0].expected_evidence


def test_planner_still_creates_draft_when_no_section_matches() -> None:
    registry = load_case_intent_registry(Path("assets/case_intents"))
    section = SourceSection(
        section_id="pricing",
        text="pricing content",
        source_ref="docs/pricing.md",
    )

    drafts = CaseDraftPlanner(registry).create_drafts_for_affected_categories_with_sections(
        ["refund"],
        [section],
    )

    assert len(drafts) == 1
    assert "source:" not in drafts[0].notes
    assert drafts[0].status == "needs_review"


def test_planner_does_not_output_active() -> None:
    registry = load_case_intent_registry(Path("assets/case_intents"))
    section = SourceSection(
        section_id="refund_policy_v2",
        text="refund_policy details",
        source_ref="docs/refund_policy.md",
    )

    drafts = CaseDraftPlanner(registry).create_drafts_for_affected_categories_with_sections(
        ["refund"],
        [section],
    )

    assert all(draft.status != "active" for draft in drafts)
