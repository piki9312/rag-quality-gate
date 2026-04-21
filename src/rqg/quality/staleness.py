"""Case staleness helpers for gate-time freshness checks."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from .models import QATestCase


@dataclass(frozen=True, slots=True)
class CaseStalenessItem:
    case_id: str
    name: str
    severity: str
    owner: str
    reference_field: str
    reference_value: str
    age_days: int | None
    issue: str


@dataclass(frozen=True, slots=True)
class CaseStalenessSummary:
    stale_after_days: int
    total_cases: int
    fresh_cases: int
    stale_cases: list[CaseStalenessItem]

    @property
    def fresh_rate(self) -> float:
        if self.total_cases <= 0:
            return 100.0
        return self.fresh_cases / self.total_cases * 100.0


def summarize_case_staleness(
    cases: list[QATestCase],
    *,
    stale_after_days: int,
    now: datetime | None = None,
) -> CaseStalenessSummary:
    """Summarize which active cases are stale for operational review."""
    current_time = _coerce_utc_datetime(now or datetime.now(timezone.utc))
    stale_cases: list[CaseStalenessItem] = []

    for case in cases:
        reference_field, reference_value, reference_dt, issue = _resolve_reference_datetime(case)
        if reference_dt is None:
            stale_cases.append(
                CaseStalenessItem(
                    case_id=case.case_id,
                    name=case.name,
                    severity=case.severity,
                    owner=case.owner,
                    reference_field=reference_field,
                    reference_value=reference_value,
                    age_days=None,
                    issue=issue,
                )
            )
            continue

        age_days = max(0, int((current_time - reference_dt).total_seconds() // 86400))
        if age_days <= stale_after_days:
            continue

        stale_cases.append(
            CaseStalenessItem(
                case_id=case.case_id,
                name=case.name,
                severity=case.severity,
                owner=case.owner,
                reference_field=reference_field,
                reference_value=reference_value,
                age_days=age_days,
                issue=f"older than {stale_after_days} days",
            )
        )

    stale_cases = sorted(
        stale_cases,
        key=lambda item: (
            0 if item.severity == "S1" else 1,
            -(item.age_days or -1),
            item.case_id,
        ),
    )
    total_cases = len(cases)
    fresh_cases = max(0, total_cases - len(stale_cases))
    return CaseStalenessSummary(
        stale_after_days=stale_after_days,
        total_cases=total_cases,
        fresh_cases=fresh_cases,
        stale_cases=stale_cases,
    )


def _resolve_reference_datetime(
    case: QATestCase,
) -> tuple[str, str, datetime | None, str]:
    invalid_fields: list[tuple[str, str]] = []
    for field_name in ("last_reviewed_at", "updated_at"):
        raw_value = getattr(case, field_name, "").strip()
        if not raw_value:
            continue
        parsed = _parse_case_datetime(raw_value)
        if parsed is not None:
            return field_name, raw_value, parsed, ""
        invalid_fields.append((field_name, raw_value))

    if invalid_fields:
        field_name, raw_value = invalid_fields[0]
        return field_name, raw_value, None, f"invalid {field_name}"

    return "-", "", None, "missing last_reviewed_at / updated_at"


def _parse_case_datetime(raw_value: str) -> datetime | None:
    normalized = raw_value.strip()
    if not normalized:
        return None

    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"

    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return _coerce_utc_datetime(parsed)


def _coerce_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
