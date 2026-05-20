"""Review stage normalization and input resolution helpers."""

from __future__ import annotations

from typing import Any

VALID_REVIEW_STAGES = ("pre_delivery", "post_delivery_change", "monthly_review")


def normalize_review_stage(value: object, *, allow_unknown: bool = False) -> str:
    """Normalize a review_stage input value.

    Public CLI/config inputs are strict by default. Internal fallback callers may
    allow unknown so old reports without the field continue to load.
    """
    stage = str(value or "").strip().lower().replace("-", "_").replace(" ", "_")
    if stage == "" and allow_unknown:
        return "unknown"
    if stage in VALID_REVIEW_STAGES:
        return stage
    if stage in {"pre", "diagnostic", "poc", "poc_review"}:
        return "pre_delivery"
    if stage in {"post", "change_review", "release_review"}:
        return "post_delivery_change"
    if stage in {"monthly", "monitor"}:
        return "monthly_review"
    if allow_unknown:
        return "unknown"

    allowed = ", ".join(VALID_REVIEW_STAGES)
    raise ValueError(f"Invalid review_stage '{value}' (allowed: {allowed})")


def review_stage_from_mapping(payload: dict[str, Any] | None) -> str | None:
    """Return normalized review_stage from a config-like mapping, if present."""
    if not isinstance(payload, dict):
        return None

    candidates = [
        payload.get("review_stage"),
        payload.get("usage_stage"),
        payload.get("review_context"),
    ]
    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        candidates.extend(
            [
                metadata.get("review_stage"),
                metadata.get("usage_stage"),
                metadata.get("review_context"),
            ]
        )
    pack = payload.get("pack")
    if isinstance(pack, dict):
        candidates.extend(
            [
                pack.get("review_stage"),
                pack.get("usage_stage"),
                pack.get("review_context"),
            ]
        )

    for candidate in candidates:
        if str(candidate or "").strip():
            return normalize_review_stage(candidate)
    return None


def resolve_review_stage(
    *,
    cli_value: object = None,
    quality_pack_payload: dict[str, Any] | None = None,
    gate_payload: dict[str, Any] | None = None,
    change_event: dict[str, Any] | None = None,
) -> str | None:
    """Resolve explicit review_stage using the public input priority contract."""
    if str(cli_value or "").strip():
        return normalize_review_stage(cli_value)

    for source in (quality_pack_payload, gate_payload, change_event):
        stage = review_stage_from_mapping(source)
        if stage:
            return stage
    return None
