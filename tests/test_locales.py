"""Tests for the locales module — detection, selection, and pattern access."""

from __future__ import annotations

import pytest

from rqg.locales import detect_locale, get_locale, is_english_text


class TestDetectLocale:
    def test_japanese_text(self):
        assert detect_locale("有給休暇の申請方法は何ですか？") == "ja"

    def test_english_text(self):
        assert detect_locale("What is the leave policy?") == "en"

    def test_mixed_defaults_to_ja(self):
        assert detect_locale("Leave policy は何ですか") == "ja"

    def test_empty_text(self):
        assert detect_locale("") == "en"

    def test_none_text(self):
        assert detect_locale(None) == "en"

    def test_numbers_only(self):
        assert detect_locale("12345") == "en"


class TestIsEnglishText:
    def test_english(self):
        assert is_english_text("Hello world") is True

    def test_japanese(self):
        assert is_english_text("こんにちは") is False

    def test_mixed(self):
        assert is_english_text("Hello こんにちは") is False

    def test_empty(self):
        assert is_english_text("") is False


class TestGetLocale:
    def test_ja_locale(self):
        ja = get_locale("ja")
        assert hasattr(ja, "CONTACT_ANSWER_RE")
        assert hasattr(ja, "QUESTION_SUFFIXES")
        assert hasattr(ja, "PHRASE_ALIAS_MAP")

    def test_en_locale(self):
        en = get_locale("en")
        assert en.QUESTION_MARK == "?"

    def test_unsupported_locale(self):
        with pytest.raises(ValueError, match="Unsupported locale"):
            get_locale("zh")


class TestJaLocalePatterns:
    def test_contact_answer_re(self):
        ja = get_locale("ja")
        assert ja.CONTACT_ANSWER_RE.search("人事部に問い合わせてください")

    def test_numeric_answer_re(self):
        ja = get_locale("ja")
        assert ja.NUMERIC_ANSWER_RE.search("毎月25日が締め日です")

    def test_phrase_alias_map_keys(self):
        ja = get_locale("ja")
        assert "証憑" in ja.PHRASE_ALIAS_MAP
        assert "残業" in ja.PHRASE_ALIAS_MAP

    def test_section_prefix_re(self):
        ja = get_locale("ja")
        assert ja.SECTION_PREFIX_RE.match("第1条 目的")
        assert ja.SECTION_PREFIX_RE.match("1. はじめに")
