"""In-memory registry and candidate selection for Case Intents."""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

from rqg.case_assets.intent_schema import CaseIntent, CaseIntentLibraryError
from rqg.case_assets.loader import load_case_intents


class CaseIntentRegistry:
    """Stable lookup index for reusable Case Intent assets.

    Initial registry matching uses exact string matching. Normalization or alias
    mapping may be added later if partner runs prove it is needed.
    """

    def __init__(self, intents: Sequence[CaseIntent]) -> None:
        sorted_intents = sorted(intents, key=lambda intent: intent.intent_id)
        self._intents_by_id: dict[str, CaseIntent] = {}
        for intent in sorted_intents:
            if intent.intent_id in self._intents_by_id:
                raise CaseIntentLibraryError(f"Duplicate Case Intent id: {intent.intent_id}")
            self._intents_by_id[intent.intent_id] = intent
        self._intents = list(self._intents_by_id.values())

    def all(self) -> list[CaseIntent]:
        """Return all intents in stable intent_id order."""
        return list(self._intents)

    def get(self, intent_id: str) -> CaseIntent | None:
        """Return a Case Intent by id when present."""
        return self._intents_by_id.get(intent_id)

    def require(self, intent_id: str) -> CaseIntent:
        """Return a Case Intent by id or fail with a clear error."""
        intent = self.get(intent_id)
        if intent is None:
            raise CaseIntentLibraryError(f"Unknown case intent: {intent_id}")
        return intent

    def find_by_risk_category(self, risk_category: str) -> list[CaseIntent]:
        """Find intents whose risk category exactly matches."""
        return [intent for intent in self._intents if intent.risk_category == risk_category]

    def find_by_failure_pattern(self, failure_pattern: str) -> list[CaseIntent]:
        """Find intents that contain the given failure pattern."""
        return [intent for intent in self._intents if failure_pattern in intent.failure_patterns]

    def find_by_severity_hint(self, severity_hint: str) -> list[CaseIntent]:
        """Find intents whose severity hint exactly matches."""
        return [intent for intent in self._intents if intent.severity_hint == severity_hint]

    def find_by_affected_business_category(self, category: str) -> list[CaseIntent]:
        """Find intents whose coverage rule applies to an affected category."""
        return [
            intent
            for intent in self._intents
            if category in intent.coverage_rule.required_when.affected_business_categories
        ]

    def find_candidates_for_affected_categories(
        self,
        categories: Sequence[str],
    ) -> list[CaseIntent]:
        """Find unique candidate intents for multiple affected categories."""
        if not categories:
            return []
        candidates: dict[str, CaseIntent] = {}
        for category in categories:
            for intent in self.find_by_affected_business_category(category):
                candidates[intent.intent_id] = intent
        return [candidates[intent_id] for intent_id in sorted(candidates)]


def load_case_intent_registry(path: str | Path) -> CaseIntentRegistry:
    """Load Case Intent YAML assets and return a registry."""
    return CaseIntentRegistry(load_case_intents(path))
