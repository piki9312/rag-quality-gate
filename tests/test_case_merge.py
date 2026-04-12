from __future__ import annotations

from rqg.quality.case_merge import merge_cases_rows


def test_merge_updates_core_content_but_preserves_curated_fields():
    base_rows = [
        {
            "case_id": "C001",
            "name": "leave policy",
            "severity": "S1",
            "question": "old question",
            "expected_evidence": "docs/old#sec-1",
            "expected_keywords": "old",
            "expected_answer": "base answer",
            "category": "policy",
            "owner": "hr-team",
            "min_case_score": "100",
            "last_reviewed_at": "2026-04-01",
        }
    ]

    review_rows = [
        {
            "case_id": "C001",
            "name": "generated name",
            "severity": "S2",
            "question": "new question",
            "expected_evidence": "docs/new#sec-2",
            "expected_keywords": "new;keyword",
            "expected_answer": "generated answer",
            "category": "generated",
            "owner": "qa-team",
            "min_case_score": "85",
            "last_reviewed_at": "2026-04-02",
        }
    ]

    merged_rows, summary = merge_cases_rows(base_rows, review_rows)

    assert len(merged_rows) == 1
    row = merged_rows[0]
    assert row["case_id"] == "C001"
    assert row["question"] == "new question"
    assert row["expected_evidence"] == "docs/new#sec-2"
    assert row["expected_keywords"] == "new;keyword"

    # Existing curated fields are preserved unless base value is empty.
    assert row["name"] == "leave policy"
    assert row["severity"] == "S1"
    assert row["expected_answer"] == "base answer"
    assert row["category"] == "policy"
    assert row["owner"] == "hr-team"
    assert row["min_case_score"] == "100"
    assert row["last_reviewed_at"] == "2026-04-01"

    assert summary.updated_case_ids == ["C001"]
    assert summary.added_case_ids == []


def test_merge_adds_new_case_from_review_rows():
    merged_rows, summary = merge_cases_rows(
        base_rows=[],
        review_rows=[
            {
                "case_id": "C002",
                "question": "When should leave be requested?",
                "expected_evidence": "docs/hr.md#sec-1",
                "risk_level": "S1",
            }
        ],
    )

    assert len(merged_rows) == 1
    row = merged_rows[0]
    assert row["case_id"] == "C002"
    assert row["severity"] == "S1"
    assert row["expected_evidence"] == "docs/hr.md#sec-1"
    assert row["category"] == "general"
    assert row["name"] == "C002"
    assert row["min_case_score"] == "100"
    assert row["status"] == "draft"
    assert summary.added_case_ids == ["C002"]
    assert summary.updated_case_ids == []


def test_merge_records_duplicate_review_case_ids_and_last_row_wins():
    merged_rows, summary = merge_cases_rows(
        base_rows=[],
        review_rows=[
            {
                "case_id": "C003",
                "question": "old",
                "expected_evidence": "docs/a#1",
            },
            {
                "case_id": "C003",
                "question": "new",
                "expected_evidence": "docs/a#2",
            },
        ],
    )

    assert len(merged_rows) == 1
    row = merged_rows[0]
    assert row["case_id"] == "C003"
    assert row["question"] == "new"
    assert row["expected_evidence"] == "docs/a#2"
    assert summary.duplicate_review_case_ids == ["C003"]


def test_merge_matches_by_content_signature_when_case_id_differs():
    base_rows = [
        {
            "case_id": "HR013",
            "name": "expense draft",
            "severity": "S2",
            "question": "1. 通勤交通費の申請方法は何ですか？",
            "expected_evidence": "packs/hr/documents/expense.md#sec-1-2",
            "expected_keywords": "old",
            "expected_answer": "",
            "category": "general",
            "owner": "",
            "min_case_score": "85",
            "last_reviewed_at": "",
        }
    ]
    review_rows = [
        {
            "case_id": "経費精算ガイドライン_002",
            "question": "2. 通勤交通費の申請方法は何ですか？",
            "expected_evidence": "packs/hr/documents/expense.md#sec-1-2",
            "expected_keywords": "new;keyword",
        }
    ]

    merged_rows, summary = merge_cases_rows(base_rows, review_rows)

    assert len(merged_rows) == 1
    assert merged_rows[0]["case_id"] == "HR013"
    assert merged_rows[0]["expected_keywords"] == "new;keyword"
    assert summary.added_case_ids == []
    assert summary.updated_case_ids == ["HR013"]
    assert summary.matched_by_content_review_case_ids == ["経費精算ガイドライン_002"]


def test_merge_does_not_over_dedupe_partial_overlap():
    base_rows = [
        {
            "case_id": "HR004",
            "name": "経費証憑要件",
            "severity": "S2",
            "question": "経費精算に必要な証憑は何ですか？",
            "expected_evidence": "",
            "expected_keywords": "経費;証憑;レシート",
            "expected_answer": "",
            "category": "procedure",
            "owner": "finance-team",
            "min_case_score": "85",
            "last_reviewed_at": "2026-03-30",
        }
    ]
    review_rows = [
        {
            "case_id": "経費精算ガイドライン_001",
            "question": "1. 締め日と提出方法はいつまでに対応する必要がありますか？",
            "expected_evidence": "packs/hr/documents/経費精算ガイドライン.md#sec-1-1",
            "expected_keywords": "締め日;提出方法",
        }
    ]

    merged_rows, summary = merge_cases_rows(base_rows, review_rows)

    assert len(merged_rows) == 2
    assert summary.added_case_ids == ["経費精算ガイドライン_001"]
    assert summary.matched_by_content_review_case_ids == []


def test_merge_handles_legacy_field_names_in_base():
    """Base CSV with old field names (expected_chunks, golden_answer, min_pass_rate)
    should be normalized to the formal schema."""
    base_rows = [
        {
            "case_id": "LEGACY001",
            "name": "legacy case",
            "severity": "S1",
            "question": "What is the old format?",
            "expected_chunks": "docs/old#sec-1",
            "expected_keywords": "old",
            "golden_answer": "legacy answer",
            "category": "policy",
            "owner": "hr-team",
            "min_pass_rate": "100",
            "last_reviewed_at": "2026-04-01",
        }
    ]

    merged_rows, summary = merge_cases_rows(base_rows, review_rows=[])

    assert len(merged_rows) == 1
    row = merged_rows[0]
    assert row["case_id"] == "LEGACY001"
    assert row["expected_evidence"] == "docs/old#sec-1"
    assert row["expected_answer"] == "legacy answer"
    assert row["min_case_score"] == "100"
    assert row["status"] == "active"
    assert "expected_chunks" not in row or row.get("expected_chunks") is None
