"""Tests for evaluators — keyword, retrieval, reference."""

from __future__ import annotations

import pytest

from rqg.quality.evaluators.keyword import keyword_match_rate
from rqg.quality.evaluators.reference import extract_references, reference_accuracy
from rqg.quality.evaluators.retrieval import retrieval_hit, retrieval_precision_at_k


# ==================================================================
# keyword_match_rate
# ==================================================================


class TestKeywordMatch:
    def test_all_keywords_present(self):
        answer = "有給休暇は5営業日前までに申請してください。"
        assert keyword_match_rate(answer, ["5営業日前", "申請"]) == 1.0

    def test_partial_match(self):
        answer = "5営業日前までに手続きしてください。"
        assert keyword_match_rate(answer, ["5営業日前", "申請"]) == 0.5

    def test_no_match(self):
        answer = "わかりません。"
        assert keyword_match_rate(answer, ["5営業日前", "申請"]) == 0.0

    def test_empty_keywords_returns_1(self):
        assert keyword_match_rate("何でも", []) == 1.0

    def test_case_insensitive(self):
        assert keyword_match_rate("Hello World", ["hello", "WORLD"]) == 1.0


# ==================================================================
# retrieval_hit
# ==================================================================


class TestRetrievalHit:
    def test_hit(self):
        assert retrieval_hit(["chunk_A", "chunk_B"], ["chunk_A"]) is True

    def test_miss(self):
        assert retrieval_hit(["chunk_A", "chunk_B"], ["chunk_X"]) is False

    def test_empty_expected(self):
        assert retrieval_hit(["chunk_A"], []) is True

    def test_one_of_many(self):
        assert retrieval_hit(["chunk_A", "chunk_B"], ["chunk_X", "chunk_A"]) is True


# ==================================================================
# retrieval_precision_at_k
# ==================================================================


class TestRetrievalPrecision:
    def test_all_found(self):
        assert retrieval_precision_at_k(["a", "b", "c"], ["a", "b"]) == 1.0

    def test_half_found(self):
        assert retrieval_precision_at_k(["a", "b"], ["a", "x"]) == 0.5

    def test_none_found(self):
        assert retrieval_precision_at_k(["a", "b"], ["x", "y"]) == 0.0

    def test_empty_expected(self):
        assert retrieval_precision_at_k(["a"], []) == 1.0


# ==================================================================
# extract_references / reference_accuracy
# ==================================================================


class TestReference:
    def test_extract(self):
        answer = "答えは[doc#chunk1]にあります。[doc#chunk2]も参照。"
        refs = extract_references(answer)
        assert refs == ["doc#chunk1", "doc#chunk2"]

    def test_extract_no_refs(self):
        assert extract_references("引用なしの回答です。") == []

    def test_accuracy_all_valid(self):
        answer = "[doc#chunk1]と[doc#chunk2]"
        assert reference_accuracy(answer, ["doc#chunk1", "doc#chunk2"]) == 1.0

    def test_accuracy_half_valid(self):
        answer = "[doc#chunk1]と[doc#chunk3]"
        assert reference_accuracy(answer, ["doc#chunk1", "doc#chunk2"]) == 0.5

    def test_accuracy_no_refs_returns_1(self):
        assert reference_accuracy("plain text", ["doc#chunk1"]) == 1.0
