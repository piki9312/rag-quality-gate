"""Case Intent Library schema models."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


IntentStatus = Literal["experimental", "validated", "deprecated"]
SeverityHint = Literal["S1", "S2", "S3", "S4"]


class CaseIntentLibraryError(ValueError):
    """Raised when Case Intent Library assets cannot be loaded or validated."""


class QuestionVariation(BaseModel):
    """Reusable question wording for a case intent."""

    variation_type: str = Field(..., min_length=1)
    template: str = Field(..., min_length=1)

    model_config = ConfigDict(extra="forbid")

    @field_validator("variation_type", "template")
    @classmethod
    def _strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("field must not be empty")
        return value


class RequiredWhen(BaseModel):
    """Conditions that make an intent relevant for coverage checks."""

    affected_business_categories: list[str] = Field(default_factory=list)
    change_types: list[str] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    @field_validator("affected_business_categories", "change_types")
    @classmethod
    def _strip_list_items(cls, values: list[str]) -> list[str]:
        return _normalize_non_empty_list(values)


class MinimumActiveCases(BaseModel):
    """Minimum active approved-for-run cases expected for coverage."""

    any: int = Field(..., ge=0)
    s1_or_s2: int = Field(..., ge=0)

    model_config = ConfigDict(extra="forbid")


class CoverageRule(BaseModel):
    """Coverage criteria attached to a Case Intent."""

    required_when: RequiredWhen
    minimum_active_cases: MinimumActiveCases

    model_config = ConfigDict(extra="forbid")


class SafeSummary(BaseModel):
    """Safe customer/PM-facing summary for a reusable Case Intent."""

    label_ja: str = Field(..., min_length=1)
    description_ja: str = Field(..., min_length=1)

    model_config = ConfigDict(extra="forbid")

    @field_validator("label_ja", "description_ja")
    @classmethod
    def _strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("field must not be empty")
        return value


class CaseIntent(BaseModel):
    """Reusable intent asset for generating vendor-reviewed draft cases."""

    intent_id: str = Field(..., min_length=1)
    version: str = Field(..., min_length=1)
    status: IntentStatus
    domain: str = Field(..., min_length=1)
    risk_category: str = Field(..., min_length=1)
    failure_patterns: list[str] = Field(..., min_length=1)
    case_intent: str = Field(..., min_length=1)
    severity_hint: SeverityHint
    question_variations: list[QuestionVariation] = Field(..., min_length=1)
    expected_behavior_template: str = Field(..., min_length=1)
    evidence_requirement: list[str] = Field(..., min_length=1)
    coverage_rule: CoverageRule
    safe_summary: SafeSummary

    model_config = ConfigDict(extra="forbid")

    @model_validator(mode="before")
    @classmethod
    def _reject_customer_answer_keys(cls, payload: Any) -> Any:
        if _contains_forbidden_key(payload, "expected_answer"):
            raise ValueError(
                "Case Intent assets must not include customer-specific expected_answer"
            )
        return payload

    @field_validator(
        "intent_id",
        "version",
        "domain",
        "risk_category",
        "case_intent",
        "expected_behavior_template",
    )
    @classmethod
    def _strip_required_text(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("field must not be empty")
        return value

    @field_validator("failure_patterns", "evidence_requirement")
    @classmethod
    def _strip_required_list(cls, values: list[str]) -> list[str]:
        normalized = _normalize_non_empty_list(values)
        if not normalized:
            raise ValueError("field must contain at least one non-empty item")
        return normalized


def _normalize_non_empty_list(values: list[str]) -> list[str]:
    normalized: list[str] = []
    for value in values:
        if not isinstance(value, str):
            raise ValueError("list items must be strings")
        stripped = value.strip()
        if stripped:
            normalized.append(stripped)
    return normalized


def _contains_forbidden_key(payload: Any, key: str) -> bool:
    if isinstance(payload, dict):
        return key in payload or any(
            _contains_forbidden_key(value, key) for value in payload.values()
        )
    if isinstance(payload, list):
        return any(_contains_forbidden_key(item, key) for item in payload)
    return False
