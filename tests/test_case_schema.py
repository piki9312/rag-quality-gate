"""Tests for case_schema: ReviewCase, mapper, normalizer, and validation."""

from __future__ import annotations

import pytest

from rqg.quality.case_schema import (
    FORMAL_CASE_FIELDS,
    REVIEW_OUTPUT_FIELDS,
    PromotionResult,
    ReviewCase,
    ValidationError,
    classify_review_status,
    infer_question_types,
    is_mixed_question,
    normalize_legacy_row,
    promote_review_cases,
    review_case_to_formal_row,
    review_row_to_review_case,
    validate_case_row,
    validate_case_rows,
)


class TestReviewCaseToFormalRow:
    def test_basic_mapping(self):
        rc = ReviewCase(
            title="経費精算の締め日",
            question="経費精算の締め日はいつですか？",
            expected_answer="毎月25日です",
            expected_evidence="経費精算ガイドライン.md#sec-1",
            severity="S1",
            category="deadline",
        )
        row = review_case_to_formal_row(rc, case_id="NEW001", default_owner="hr-team")

        assert row["case_id"] == "NEW001"
        assert row["name"] == "経費精算の締め日"
        assert row["question"] == "経費精算の締め日はいつですか？"
        assert row["severity"] == "S1"
        assert row["eval_mode"] == "exact"
        assert row["status"] == "draft"  # complete case → draft
        assert row["owner"] == "hr-team"
        assert row["min_case_score"] == "100"  # S1 default
        assert row["source_doc"] == ""
        assert "source_doc未設定" in row["notes"]

    def test_infers_evidence_keyword_mode(self):
        rc = ReviewCase(
            title="有給申請の要件",
            question="有給休暇の申請要件は何ですか？",
            expected_evidence="就業規則.md#sec-1",
            expected_keywords="有給;申請",
            severity="S2",
        )
        row = review_case_to_formal_row(rc, case_id="NEW002")

        assert row["eval_mode"] == "evidence_keyword"
        assert row["status"] == "draft"

    def test_explicit_default_status_overrides_auto(self):
        rc = ReviewCase(title="test", question="q?")
        row = review_case_to_formal_row(rc, default_status="active")
        assert row["status"] == "active"

    def test_none_default_status_auto_classifies(self):
        rc = ReviewCase(title="test", question="q?")
        # no expected_answer, no expected_evidence → needs_review
        row = review_case_to_formal_row(rc)
        assert row["status"] == "needs_review"

    def test_empty_case_id_left_blank(self):
        rc = ReviewCase(title="test", question="q?")
        row = review_case_to_formal_row(rc)
        assert row["case_id"] == ""

    def test_invalid_severity_defaults_to_s2(self):
        rc = ReviewCase(title="test", question="q?", severity="bad")
        row = review_case_to_formal_row(rc)
        assert row["severity"] == "S2"
        assert row["min_case_score"] == "85"

    def test_notes_preserved(self):
        rc = ReviewCase(title="t", question="q?", notes="手動確認が必要")
        row = review_case_to_formal_row(rc)
        assert "手動確認が必要" in row["notes"]
        assert "source_doc未設定" in row["notes"]

    def test_mixed_question_note_added(self):
        rc = ReviewCase(title="t", question="締め日と提出方法はいつまでに対応する必要がありますか？")
        row = review_case_to_formal_row(rc)
        assert "mixed_question:deadline,procedure" in row["notes"]

    def test_all_formal_fields_present(self):
        rc = ReviewCase(title="t", question="q?")
        row = review_case_to_formal_row(rc)
        for field in FORMAL_CASE_FIELDS:
            assert field in row


class TestReviewRowToReviewCase:
    def test_with_new_field_names(self):
        row = {
            "title": "test case",
            "question": "What?",
            "eval_mode": "evidence-keyword",
            "expected_answer": "Answer",
            "expected_evidence": "doc.md#sec-1",
            "expected_keywords": "policy;request",
            "severity": "S1",
            "category": "policy",
            "notes": "note",
        }
        rc = review_row_to_review_case(row)
        assert rc.title == "test case"
        assert rc.eval_mode == "evidence-keyword"
        assert rc.expected_answer == "Answer"
        assert rc.expected_keywords == "policy;request"

    def test_with_legacy_field_names(self):
        row = {
            "name": "legacy name",
            "question": "What?",
            "golden_answer": "Old answer",
            "expected_chunks": "chunk-1",
            "risk_level": "S1",
        }
        rc = review_row_to_review_case(row)
        assert rc.title == "legacy name"
        assert rc.expected_answer == "Old answer"
        assert rc.expected_evidence == "chunk-1"
        assert rc.severity == "S1"


class TestNormalizeLegacyRow:
    def test_renames_legacy_fields(self):
        row = {
            "case_id": "X001",
            "golden_answer": "old answer",
            "expected_chunks": "chunk-1",
            "min_pass_rate": "90",
            "name": "test",
            "question": "q?",
            "severity": "S1",
        }
        result = normalize_legacy_row(row)
        assert result["expected_answer"] == "old answer"
        assert result["expected_evidence"] == "chunk-1"
        assert result["min_case_score"] == "90"
        assert result["status"] == "active"

    def test_formal_fields_not_overwritten(self):
        row = {
            "case_id": "X002",
            "expected_answer": "formal answer",
            "golden_answer": "legacy answer",
            "question": "q?",
        }
        result = normalize_legacy_row(row)
        assert result["expected_answer"] == "formal answer"

    def test_source_doc_extracted_from_evidence(self):
        row = {
            "case_id": "X003",
            "expected_evidence": "packs/hr/docs/leave.md#sec-1",
            "question": "q?",
        }
        result = normalize_legacy_row(row)
        assert result["source_doc"] == "packs/hr/docs/leave.md"


class TestValidation:
    def test_valid_row_no_errors(self):
        row = {
            "case_id": "V001",
            "question": "What?",
            "expected_answer": "Answer",
            "status": "active",
            "severity": "S1",
            "min_case_score": "100",
            "updated_at": "2026-04-13",
        }
        errors = validate_case_row(row)
        assert [e for e in errors if e.level == "error"] == []

    def test_active_evidence_keyword_requires_keywords(self):
        row = {
            "case_id": "V001A",
            "question": "What?",
            "status": "active",
            "eval_mode": "evidence_keyword",
            "expected_evidence": "doc.md#sec-1",
            "expected_keywords": "",
        }
        errors = validate_case_row(row)
        keyword_errors = [e for e in errors if e.field == "expected_keywords"]
        assert len(keyword_errors) == 1
        assert keyword_errors[0].level == "error"

    def test_active_grounded_judge_requires_evidence(self):
        row = {
            "case_id": "V001B",
            "question": "What?",
            "status": "active",
            "eval_mode": "grounded_judge",
            "expected_evidence": "",
        }
        errors = validate_case_row(row)
        evidence_errors = [e for e in errors if e.field == "expected_evidence"]
        assert len(evidence_errors) == 1
        assert evidence_errors[0].level == "error"

    def test_invalid_eval_mode(self):
        row = {"case_id": "V001C", "question": "What?", "eval_mode": "bad-mode"}
        errors = validate_case_row(row)
        assert any(e.field == "eval_mode" for e in errors)

    def test_deprecated_skips_content_requirements(self):
        row = {
            "case_id": "V001D",
            "status": "deprecated",
            "question": "",
            "expected_answer": "",
            "expected_evidence": "",
            "expected_keywords": "",
        }
        errors = validate_case_row(row)
        assert errors == []

    def test_empty_case_id(self):
        row = {"case_id": "", "question": "What?"}
        errors = validate_case_row(row)
        assert any(e.field == "case_id" for e in errors)

    def test_empty_question(self):
        row = {"case_id": "V002", "question": ""}
        errors = validate_case_row(row)
        assert any(e.field == "question" for e in errors)

    def test_invalid_status(self):
        row = {"case_id": "V003", "question": "q?", "status": "invalid"}
        errors = validate_case_row(row)
        assert any(e.field == "status" for e in errors)

    def test_invalid_severity(self):
        row = {"case_id": "V004", "question": "q?", "severity": "S3"}
        errors = validate_case_row(row)
        assert any(e.field == "severity" for e in errors)

    def test_min_case_score_out_of_range(self):
        row = {"case_id": "V005", "question": "q?", "min_case_score": "150"}
        errors = validate_case_row(row)
        assert any(e.field == "min_case_score" for e in errors)

    def test_min_case_score_non_numeric(self):
        row = {"case_id": "V006", "question": "q?", "min_case_score": "abc"}
        errors = validate_case_row(row)
        assert any(e.field == "min_case_score" for e in errors)

    def test_invalid_date_format(self):
        row = {"case_id": "V007", "question": "q?", "updated_at": "not-a-date"}
        errors = validate_case_row(row)
        assert any(e.field == "updated_at" for e in errors)

    def test_valid_date_format(self):
        row = {"case_id": "V008", "question": "q?", "updated_at": "2026-04-13"}
        errors = validate_case_row(row)
        assert not any(e.field == "updated_at" for e in errors)

    def test_duplicate_case_ids(self):
        rows = [
            {"case_id": "DUP", "question": "q1?"},
            {"case_id": "DUP", "question": "q2?"},
        ]
        errors = validate_case_rows(rows)
        dup_errors = [e for e in errors if "重複" in e.message]
        assert len(dup_errors) == 1

    def test_expected_answer_empty_is_warning(self):
        row = {"case_id": "V009", "question": "q?", "expected_answer": ""}
        errors = validate_case_row(row)
        ea_errors = [e for e in errors if e.field == "expected_answer"]
        assert len(ea_errors) == 1
        assert ea_errors[0].level == "warn"

    def test_numeric_only_evidence_warns(self):
        row = {"case_id": "V010", "question": "q?", "expected_evidence": "123"}
        errors = validate_case_row(row)
        ev_errors = [e for e in errors if e.field == "expected_evidence"]
        assert len(ev_errors) == 1
        assert ev_errors[0].level == "warn"


class TestExpectedAnswerValidationByStatus:
    """expected_answer 空のバリデーションは status 依存。"""

    def test_active_status_empty_answer_is_error(self):
        row = {"case_id": "VA01", "question": "q?", "status": "active", "expected_answer": ""}
        errors = validate_case_row(row)
        ea_errors = [e for e in errors if e.field == "expected_answer"]
        assert len(ea_errors) == 1
        assert ea_errors[0].level == "error"

    def test_draft_status_empty_answer_is_warn(self):
        row = {"case_id": "VA02", "question": "q?", "status": "draft", "expected_answer": ""}
        errors = validate_case_row(row)
        ea_errors = [e for e in errors if e.field == "expected_answer"]
        assert len(ea_errors) == 1
        assert ea_errors[0].level == "warn"

    def test_needs_review_status_empty_answer_is_warn(self):
        row = {
            "case_id": "VA03",
            "question": "q?",
            "status": "needs_review",
            "expected_answer": "",
        }
        errors = validate_case_row(row)
        ea_errors = [e for e in errors if e.field == "expected_answer"]
        assert len(ea_errors) == 1
        assert ea_errors[0].level == "warn"

    def test_deprecated_status_empty_answer_is_ignored(self):
        row = {"case_id": "VA03D", "question": "", "status": "deprecated", "expected_answer": ""}
        errors = validate_case_row(row)
        ea_errors = [e for e in errors if e.field == "expected_answer"]
        assert ea_errors == []

    def test_active_with_answer_no_error(self):
        row = {"case_id": "VA04", "question": "q?", "status": "active", "expected_answer": "ans"}
        errors = validate_case_row(row)
        ea_errors = [e for e in errors if e.field == "expected_answer"]
        assert ea_errors == []


class TestClassifyReviewStatus:
    """classify_review_status の判定ロジック。"""

    def test_infer_question_types_detects_multiple_intents(self):
        assert infer_question_types("締め日と提出方法はいつまでに対応する必要がありますか？") == (
            "deadline",
            "procedure",
        )

    def test_is_mixed_question_true_for_combined_prompt(self):
        assert is_mixed_question("締め日と提出方法はいつまでに対応する必要がありますか？") is True

    def test_complete_case_returns_draft(self):
        rc = ReviewCase(
            title="t",
            question="有給の期限は？",
            expected_answer="5営業日前",
            expected_evidence="doc.md#sec-1",
            severity="S1",
        )
        assert classify_review_status(rc) == "draft"

    def test_empty_question_returns_needs_review(self):
        rc = ReviewCase(title="t", question="", expected_answer="a", expected_evidence="e")
        assert classify_review_status(rc) == "needs_review"

    def test_short_question_returns_needs_review(self):
        rc = ReviewCase(title="t", question="q?", expected_answer="a", expected_evidence="e")
        assert classify_review_status(rc) == "needs_review"

    def test_evidence_only_infers_grounded_judge(self):
        rc = ReviewCase(title="t", question="有給の期限は？", expected_evidence="e")
        assert classify_review_status(rc) == "draft"

    def test_answer_only_infers_exact(self):
        rc = ReviewCase(title="t", question="有給の期限は？", expected_answer="a")
        assert classify_review_status(rc) == "draft"

    def test_exact_mode_without_answer_returns_needs_review(self):
        rc = ReviewCase(title="t", question="有給の期限は？", eval_mode="exact", expected_evidence="e")
        assert classify_review_status(rc) == "needs_review"

    def test_evidence_keyword_without_keywords_returns_needs_review(self):
        rc = ReviewCase(
            title="t",
            question="有給の期限は？",
            eval_mode="evidence_keyword",
            expected_evidence="e",
        )
        assert classify_review_status(rc) == "needs_review"

    def test_invalid_severity_returns_needs_review(self):
        rc = ReviewCase(
            title="t",
            question="有給の期限は？",
            expected_answer="a",
            expected_evidence="e",
            severity="S3",
        )
        assert classify_review_status(rc) == "needs_review"

    def test_mixed_question_returns_needs_review(self):
        rc = ReviewCase(
            title="t",
            question="締め日と提出方法はいつまでに対応する必要がありますか？",
            expected_evidence="doc.md#sec-1",
            expected_keywords="締め日;提出方法",
        )
        assert classify_review_status(rc) == "needs_review"


class TestPromoteReviewCases:
    """パイプラインテスト: review → formal with validation。"""

    def test_complete_cases_all_draft(self):
        reviews = [
            ReviewCase(
                title=f"case{i}",
                question=f"質問{i}の内容は？",
                expected_answer=f"回答{i}",
                expected_evidence=f"doc.md#sec-{i}",
                severity="S1",
            )
            for i in range(3)
        ]
        result = promote_review_cases(reviews, id_prefix="P")
        assert len(result.rows) == 3
        assert result.rows[0]["case_id"] == "P001"
        assert result.rows[2]["case_id"] == "P003"
        assert result.draft_count == 3
        assert result.needs_review_count == 0
        assert not result.has_errors

    def test_incomplete_cases_marked_needs_review(self):
        reviews = [
            ReviewCase(title="incomplete", question="何？"),  # no answer/evidence
        ]
        result = promote_review_cases(reviews, id_prefix="X", id_start=10)
        assert result.rows[0]["case_id"] == "X010"
        assert result.rows[0]["status"] == "needs_review"
        assert result.needs_review_count == 1

    def test_mixed_complete_and_incomplete(self):
        reviews = [
            ReviewCase(
                title="complete",
                question="有給の期限は？",
                expected_answer="5営業日前",
                expected_evidence="doc#s1",
                severity="S2",
            ),
            ReviewCase(title="incomplete", question="何？"),
        ]
        result = promote_review_cases(reviews)
        assert result.draft_count == 1
        assert result.needs_review_count == 1
        # needs_review case: expected_answer empty → warn (not error)
        assert not result.has_errors

    def test_validation_errors_detected(self):
        reviews = [
            ReviewCase(title="", question=""),  # both empty → errors
        ]
        result = promote_review_cases(reviews)
        assert result.has_errors
        assert any(e.field == "question" for e in result.validation_errors)
