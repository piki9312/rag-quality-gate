from __future__ import annotations

from datetime import datetime, timezone

from rqg.domain import GateDecision
from rqg.quality.notifications import _build_payload
from rqg.security import (
    contains_token_like_string,
    redact_text,
    sanitize_mapping,
    sanitize_url,
)


def test_redact_text_redacts_token_like_strings() -> None:
    examples = [
        "Authorization: Bearer abcdefghijklmnopqrstuvwxyz1234567890",
        "sk-abcdefghijklmnopqrstuvwxyz1234567890",
        "api_key=abcdefghijklmnopqrstuvwxyz1234567890",
    ]

    for example in examples:
        sanitized = redact_text(example)
        assert "[REDACTED]" in sanitized
        assert "abcdefghijklmnopqrstuvwxyz1234567890" not in sanitized
        assert contains_token_like_string(example)


def test_sanitize_mapping_redacts_sensitive_keys() -> None:
    payload = {
        "question": "What is the private policy?",
        "expected_answer": "Expected private answer",
        "answer": "Raw generated answer",
        "retrieved_evidence": "Raw evidence body",
        "chunk_text": "Raw chunk body",
        "endpoint": "https://rag.example.test/search",
        "api_key": "sk-abcdefghijklmnopqrstuvwxyz1234567890",
    }

    sanitized = sanitize_mapping(payload)

    for key in payload:
        assert sanitized[key] == "[REDACTED]"


def test_sanitize_mapping_preserves_safe_summary_fields() -> None:
    payload = {
        "status": "fail",
        "policy_status": "block",
        "pass_rate": 92.5,
        "s1_failed_count": 1,
        "failure_category": "retrieval_miss",
        "run_id": "run-safe-001",
    }

    assert sanitize_mapping(payload) == payload


def test_sanitize_url_redacts_sensitive_url() -> None:
    raw_url = (
        "https://rag.example.test/search?"
        "api_key=abcdefghijklmnopqrstuvwxyz1234567890&query=sample"
    )

    sanitized = sanitize_url(raw_url)

    assert "[REDACTED]" in sanitized
    assert raw_url not in sanitized
    assert "abcdefghijklmnopqrstuvwxyz1234567890" not in sanitized
    assert "query=sample" in sanitized


def test_notification_payload_sanitizes_free_text_fields() -> None:
    decision = GateDecision(
        run_id="run-notify-safe",
        status="fail",
        reasons=[
            "external error token=abcdefghijklmnopqrstuvwxyz1234567890 "
            r"source=C:\Users\someone\workspace\case.md"
        ],
        metrics={"s1_fail_count": 1},
        next_actions=[
            {
                "failure_category": "retrieval_miss",
                "count": 1,
                "action": (
                    "Review failed response with Bearer " "abcdefghijklmnopqrstuvwxyz1234567890"
                ),
            }
        ],
        created_at=datetime.now(timezone.utc),
    )

    payload = _build_payload(
        kind="webhook",
        decision=decision,
        report_path=r"C:\Users\someone\workspace\gate-report.json",
        decision_path=None,
    )
    payload_text = str(payload)

    assert "abcdefghijklmnopqrstuvwxyz1234567890" not in payload_text
    assert r"C:\Users\someone\workspace" not in payload_text
    assert "retrieval_fail" in payload_text
    assert payload["report_path"] == "gate-report.json"
