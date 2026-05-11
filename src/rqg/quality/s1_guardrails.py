"""High-risk S1 answer guardrails beyond keyword matching.

This module currently focuses on Japanese-heavy customer support wording with a
small bilingual fallback set for common English policy terms.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# Numeric units recognized by the guardrail:
# - percentage/currency: %, ％, 円
# - deadline/period: 日, 営業日, 日前, か月, ヶ月, 月, 年
# - time: 時間, h
# The `|` characters below are regex alternation operators, not literal unit text.
_NUMBER_TOKEN_UNIT_PATTERN = r"%|％|円|日|営業日|日前|か月|ヶ月|月|年|時間|h"
_NUMBER_TOKEN_RE = re.compile(
    rf"(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>{_NUMBER_TOKEN_UNIT_PATTERN})?"
)
_DEADLINE_OR_PERIOD_UNIT_RE = re.compile(r"(?:日|営業日|日前|か月|ヶ月|月|年)")
_NEGATION_TERMS = ("できない", "不可", "対象外", "ありません", "しない", "禁止", "not", "cannot")
_AFFIRMATIVE_TERMS = ("できます", "可能", "対象です", "あります", "ok", "allowed")
_EXCEPTION_TERMS = ("ただし", "例外", "除く", "except", "unless", "個別審査")
_CONDITION_TERMS = ("場合", "限り", "のみ", "after", "本人確認", "if", "when", "かつ", "または")
_OVER_ASSERTIVE_TERMS = ("必ず", "確実", "無条件", "always", "definitely")
_INSUFFICIENT_TERMS = ("根拠が見つかりません", "わかりません", "不明", "cannot determine")


@dataclass(frozen=True, slots=True)
class S1GuardrailFailure:
    failure_type: str
    failure_reason: str


def _normalized_numbers(text: str) -> set[str]:
    found: set[str] = set()
    for match in _NUMBER_TOKEN_RE.finditer(text):
        value = match.group("value")
        unit = (match.group("unit") or "").strip()
        if not value:
            continue
        found.add(f"{value}{unit}")
    return found


def _contains_any(text: str, needles: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


def evaluate_s1_guardrails(expected_answer: str, answer: str) -> S1GuardrailFailure | None:
    expected = (expected_answer or "").strip()
    actual = (answer or "").strip()
    if not expected or not actual:
        return None

    if _contains_any(actual, _INSUFFICIENT_TERMS):
        return S1GuardrailFailure(
            "insufficient_context",
            "Answer indicates insufficient context for an S1 case",
        )

    expected_numbers = _normalized_numbers(expected)
    if expected_numbers:
        actual_numbers = _normalized_numbers(actual)
        if expected_numbers != actual_numbers:
            failure_type = (
                "deadline_or_period_mismatch"
                if any(_DEADLINE_OR_PERIOD_UNIT_RE.search(token) for token in expected_numbers)
                else "numeric_mismatch"
            )
            return S1GuardrailFailure(
                failure_type,
                f"Expected numeric terms {sorted(expected_numbers)} but answer used {sorted(actual_numbers)}",
            )

    expected_has_negation = _contains_any(expected, _NEGATION_TERMS)
    actual_has_negation = _contains_any(actual, _NEGATION_TERMS)
    actual_has_affirmative = _contains_any(actual, _AFFIRMATIVE_TERMS)
    if expected_has_negation and actual_has_affirmative and not actual_has_negation:
        return S1GuardrailFailure(
            "negation_error",
            "Expected answer contains a denial/restriction but the answer sounds affirmative",
        )

    expected_has_exception = _contains_any(expected, _EXCEPTION_TERMS)
    if expected_has_exception and not _contains_any(actual, _EXCEPTION_TERMS):
        return S1GuardrailFailure(
            "exception_omission",
            "Expected answer contains exception handling that the answer omitted",
        )

    expected_has_condition = _contains_any(expected, _CONDITION_TERMS)
    if expected_has_condition and not _contains_any(actual, _CONDITION_TERMS):
        return S1GuardrailFailure(
            "condition_mismatch",
            "Expected answer contains conditions that the answer omitted",
        )

    if _contains_any(actual, _OVER_ASSERTIVE_TERMS) and (
        expected_has_exception
        or expected_has_condition
        or _contains_any(expected, ("個別審査", "要確認"))
    ):
        return S1GuardrailFailure(
            "over_assertive_answer",
            "Answer was more definitive than the expected conditional/reviewed behavior",
        )

    return None
