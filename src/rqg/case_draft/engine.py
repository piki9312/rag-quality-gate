"""Template-based Case Draft Engine skeleton."""

from __future__ import annotations

from rqg.case_assets import CaseIntent
from rqg.case_draft.draft_case import DraftCaseCandidate, SourceSection
from rqg.case_draft.validators import validate_draft_case_candidate


class CaseDraftEngine:
    """Create vendor-reviewed draft case candidates from Case Intents.

    This skeleton intentionally uses deterministic templates only. It does not
    call an LLM, perform retrieval, activate cases, or connect to the existing
    gen_cases CLI.
    """

    def create_draft_from_intent(
        self,
        intent: CaseIntent,
        source_section: SourceSection | None = None,
    ) -> DraftCaseCandidate:
        """Create one needs_review draft candidate from one Case Intent."""
        question = intent.question_variations[0].template
        evidence_parts = list(intent.evidence_requirement)
        notes_parts = [
            "generated_by:case_draft_engine",
            "case_type:generated-draft",
            f"intent:{intent.intent_id}",
            f"pattern:{intent.failure_patterns[0]}",
        ]
        if source_section is not None:
            notes_parts.append(f"source:{source_section.section_id}")
            evidence_parts.append(source_section.source_ref or source_section.section_id)

        candidate = DraftCaseCandidate(
            case_id=f"DRAFT-{intent.intent_id}",
            status="needs_review",
            severity=intent.severity_hint,
            category=intent.risk_category,
            question=question,
            expected_answer=intent.expected_behavior_template,
            expected_evidence=", ".join(evidence_parts),
            notes="; ".join(notes_parts),
        )
        return validate_draft_case_candidate(candidate)
