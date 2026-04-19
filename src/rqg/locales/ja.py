"""Japanese locale patterns for runner and casegen question generation."""

from __future__ import annotations

import re
from typing import Sequence

# ---------------------------------------------------------------------------
# Answer-type detection patterns (runner.py)
# ---------------------------------------------------------------------------

CONTACT_ANSWER_RE = re.compile(r"(人事部|情報セキュリティ担当|[\w一-龠ぁ-んァ-ヶー々]+担当)")
NUMERIC_ANSWER_RE = re.compile(r"\d|毎月|翌営業日|営業日|前営業日|週\s*\d+\s*回|最長\s*\d+\s*歳")
PROCEDURE_ANSWER_RE = re.compile(r"申請|承認|提出|添付|システム|打刻|報告")
POLICY_ANSWER_RE = re.compile(r"禁止|必要|可能|対象|条件|事由|違反|原則")

# ---------------------------------------------------------------------------
# Question analysis patterns (runner.py)
# ---------------------------------------------------------------------------

QUESTION_SPLIT_RE = re.compile(r"[はをにでがと、。？！?\s]+")

QUESTION_SUFFIXES: tuple[str, ...] = (
    "はどの手順で申請しますか",
    "はどの手順ですか",
    "はどうやって申請しますか",
    "はどうやって行いますか",
    "は何ですか",
    "はいつまでですか",
    "はいつですか",
    "はどこですか",
    "はいくらですか",
)

QUESTION_GENERIC_PHRASES: frozenset[str] = frozenset(
    {
        "何ですか",
        "何",
        "いつですか",
        "いつ",
        "どこですか",
        "どこ",
        "いくらですか",
        "いくら",
        "ですか",
        "ますか",
        "する場合",
        "場合",
        "主な",
        "必要",
    }
)

# Intent-boost keyword groups  (question term → answer pattern)
CONTACT_QUESTION_TERMS: tuple[str, ...] = (
    "問い合わせ先",
    "どこ",
    "窓口",
    "連絡先",
    "エスカレーション",
)
DEADLINE_QUESTION_TERMS: tuple[str, ...] = (
    "いつ",
    "期限",
    "締め日",
    "何日",
    "いつまで",
    "上限",
)
AMOUNT_QUESTION_TERMS: tuple[str, ...] = ("いくら", "金額", "何円", "月額")
PROCEDURE_QUESTION_TERMS: tuple[str, ...] = ("手順", "方法", "申請", "どうやって")
POLICY_QUESTION_TERMS: tuple[str, ...] = ("条件", "ルール", "事由", "主な", "何ですか")

# ---------------------------------------------------------------------------
# Phrase aliases (domain-specific synonyms for mock scoring)
# ---------------------------------------------------------------------------

PHRASE_ALIAS_MAP: dict[str, list[str]] = {
    "証憑": ["レシート", "領収書", "添付", "原本"],
    "問い合わせ": ["人事部", "担当", "窓口"],
    "窓口": ["人事部", "担当", "窓口"],
    "連絡先": ["人事部", "担当", "窓口"],
    "期限": ["営業日", "前営業日", "翌営業日", "毎月25日"],
    "締め日": ["営業日", "前営業日", "翌営業日", "毎月25日"],
    "残業": ["残業"],
    "持ち出し": ["社外への持ち出し", "社外持ち出し", "原則禁止"],
    "承認": ["承認", "申請", "上司", "上長"],
    "手順": ["承認", "申請", "上司", "上長"],
    "懲戒": ["背信行為", "無断欠勤", "有罪判決", "機密情報"],
    "事由": ["背信行為", "無断欠勤", "有罪判決", "機密情報"],
    "在宅勤務": ["在宅勤務", "週2回", "在宅"],
    "育児休業": ["育児休業", "最長2歳", "保育所"],
    "延長": ["育児休業", "最長2歳", "保育所"],
}

# ---------------------------------------------------------------------------
# Mock answer formatting
# ---------------------------------------------------------------------------

CONTACT_ANSWER_TEMPLATE = "問い合わせ先は{contact}です。"
FOCUS_LABEL_TEMPLATE = "{label}については、{line}"

# ---------------------------------------------------------------------------
# Casegen patterns (questions.py)
# ---------------------------------------------------------------------------

SECTION_PREFIX_RE = re.compile(r"^(?:第[0-9０-９]+[条章]\s*|[0-9０-９]+[.)．]\s*)")
TIME_RANGE_RE = re.compile(r"\d{1,2}:\d{2}\s*[〜~\-]\s*\d{1,2}:\d{2}")
COMPLIANCE_HINT_RE = re.compile(r"禁止|違反|漏洩|懲戒|機密情報|個人情報|施錠|暗号化")
JAPANESE_TEXT_RE = re.compile(r"[ぁ-んァ-ヶ一-龠々]")

# Document topic suffixes to strip
DOCUMENT_TOPIC_SUFFIXES: tuple[str, ...] = (
    "ガイドライン",
    "制度",
    "規定",
    "規程",
    "runbook",
    "faq",
    "policy",
)

# Generic question tokens to filter out
GENERIC_QUESTION_TOKENS: tuple[str, ...] = (
    "この内容",
    "このセクション",
    "本文",
    "本セクション",
)

# Rule-based question templates
DEADLINE_KEYWORDS: tuple[str, ...] = ("期限", "いつまで", "日まで", "期日")
APPLICATION_KEYWORDS: tuple[str, ...] = ("申請", "手続", "届け出", "提出")
CONDITION_KEYWORDS: tuple[str, ...] = ("条件", "対象", "要件")
PROHIBITION_KEYWORDS: tuple[str, ...] = ("禁止", "不可", "してはいけない")

QUESTION_MARK = "？"
