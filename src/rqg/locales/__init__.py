"""Locale detection and selection for multilingual pattern application.

Usage:
    from rqg.locales import detect_locale, get_locale

    locale = detect_locale("有給休暇の申請方法は何ですか？")
    assert locale == "ja"

    patterns = get_locale("ja")
    # -> rqg.locales.ja module
"""

from __future__ import annotations

import re
from types import ModuleType

_JAPANESE_TEXT_RE = re.compile(r"[ぁ-んァ-ヶ一-龠々]")
_ASCII_ALPHA_RE = re.compile(r"[A-Za-z]")
_SPACE_RE = re.compile(r"\s+")


def detect_locale(text: str) -> str:
    """Detect locale from text content.

    Returns ``"ja"`` if the text contains Japanese characters,
    otherwise ``"en"`` (default fallback).
    """
    normalized = _SPACE_RE.sub(" ", (text or "").strip())
    if _JAPANESE_TEXT_RE.search(normalized):
        return "ja"
    return "en"


def is_english_text(text: str) -> bool:
    """Return True if text is English (has ASCII alpha, no Japanese characters)."""
    normalized = _SPACE_RE.sub(" ", (text or "").strip())
    return bool(_ASCII_ALPHA_RE.search(normalized)) and not bool(
        _JAPANESE_TEXT_RE.search(normalized)
    )


def get_locale(locale: str) -> ModuleType:
    """Return the locale module for the given locale code.

    Raises ``ValueError`` if the locale is not supported.
    """
    if locale == "ja":
        from . import ja

        return ja
    elif locale == "en":
        from . import en

        return en
    raise ValueError(f"Unsupported locale: {locale!r}. Supported: 'ja', 'en'")
