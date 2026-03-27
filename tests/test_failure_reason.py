from __future__ import annotations

from rqg.quality.failure_reason import classify_failure_category


def test_error_is_tool_failure():
    category = classify_failure_category(
        failure_type="error",
        failure_reason="connection timeout",
        retrieval_hit=None,
        retrieved_ids=[],
    )
    assert category == "tool_failure"


def test_keyword_miss_with_no_retrieval_is_retrieval_miss():
    category = classify_failure_category(
        failure_type="keyword_miss",
        failure_reason="Keyword match 0% < 80%",
        retrieval_hit=False,
        retrieved_ids=[],
    )
    assert category == "retrieval_miss"


def test_keyword_miss_with_retrieval_hit_is_synthesis():
    category = classify_failure_category(
        failure_type="keyword_miss",
        failure_reason="Keyword match 0% < 80%",
        retrieval_hit=True,
        retrieved_ids=["chunk_A"],
    )
    assert category == "synthesis"


def test_unknown_fallback():
    category = classify_failure_category(
        failure_type="something_else",
        failure_reason="unexpected mismatch",
        retrieval_hit=None,
        retrieved_ids=["chunk_A"],
    )
    assert category == "unknown"
