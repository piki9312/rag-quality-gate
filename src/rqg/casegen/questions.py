"""Question candidate generation from document sections."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from openai import APIError

from rqg.casegen.sections import DocumentSection
from rqg.locales import detect_locale
from rqg.locales import is_english_text as is_english_text  # re-export
from rqg.locales import ja as ja_locale
from rqg.quality.case_schema import infer_question_types, strip_ordinal_prefix
from rqg.serving.llm_client import OPENAI_MODEL, call_openai_chat

logger = logging.getLogger(__name__)

_SPACE_RE = re.compile(r"\s+")
_SECTION_PREFIX_RE = ja_locale.SECTION_PREFIX_RE
_TIME_RANGE_RE = ja_locale.TIME_RANGE_RE
_ASCII_LABEL_RE = re.compile(r"^[A-Za-z0-9_\- ]+$")
_COMPLIANCE_HINT_RE = re.compile(r"禁止|違反|漏洩|懲戒|機密情報|個人情報|施錠|暗号化")
_ASCII_ALPHA_RE = re.compile(r"[A-Za-z]")
_JAPANESE_TEXT_RE = re.compile(r"[ぁ-んァ-ヶ一-龠々]")
_SENTENCE_RE = re.compile(r"[^。！？.!?]+(?:[。！？.!?]|$)")
_ANSWER_FACT_RE = re.compile(
    r"毎月\s*\d{1,2}\s*日"
    r"|\d{1,3}(?:,\d{3})*\s*円"
    r"|\d+\s*営業日前"
    r"|\d+\s*営業日以内"
    r"|\d+\s*日以内"
    r"|\d+\s*日まで"
    r"|翌営業日"
    r"|前営業日"
    r"|\d+\s*business days?"
    r"|\d+\s*days?",
    re.IGNORECASE,
)
_ANSWER_TOKEN_RE = re.compile(r"[A-Za-z]{2,}|\d[\d,]*|[ぁ-んァ-ヶー一-龠々]{2,}")
_JAPANESE_AMOUNT_RE = re.compile(r"(?:月額\s*)?\d{1,3}(?:,\d{3})*円")
_DAY_LIMIT_RE = re.compile(r"通算\s*\d+\s*日まで|最大\s*\d+\s*日|最長\s*\d+\s*日")
_DEADLINE_SENTENCE_RE = re.compile(
    r"毎月\s*\d{1,2}\s*日"
    r"|\d+\s*営業日前"
    r"|\d+\s*営業日以内"
    r"|\d+\s*日以内"
    r"|翌営業日"
    r"|前営業日"
    r"|\d+\s*business days?"
    r"|in advance"
    r"|within\s+\d+\s+days",
    re.IGNORECASE,
)
_DEADLINE_HINTS = ("期限", "いつまで", "日まで", "期日")
_PROCEDURE_HINTS = ("申請", "手続", "届け出", "提出")
_POLICY_HINTS = ("条件", "対象", "要件")
_COMPLIANCE_RULE_HINTS = ("禁止", "不可", "してはいけない")
_ANSWER_STOPWORDS = {
    "the",
    "and",
    "for",
    "with",
    "from",
    "that",
    "this",
    "must",
    "should",
    "within",
    "before",
    "after",
    "です",
    "ます",
    "こと",
    "場合",
    "必要",
    "まで",
    "ため",
}


def normalize_question_text(question: str) -> str:
    """Normalize question text for dedupe and quality checks."""
    compact = _SPACE_RE.sub(" ", question.strip())
    return compact.rstrip("?？ ")


def _contains_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(pattern in text for pattern in patterns)


def _infer_rule_hint_category(subject: str, content: str, question: str = "") -> str:
    combined = f"{subject}\n{content}\n{question}"
    if _contains_any(combined, ja_locale.DEADLINE_KEYWORDS):
        return "deadline"
    if _contains_any(combined, ja_locale.APPLICATION_KEYWORDS):
        return "procedure"
    if _contains_any(combined, ja_locale.CONDITION_KEYWORDS):
        return "policy"
    if _contains_any(combined, ja_locale.PROHIBITION_KEYWORDS):
        return "compliance"
    return "general"


def is_english_text(text: str) -> bool:
    normalized = _SPACE_RE.sub(" ", (text or "").strip())
    return bool(_ASCII_ALPHA_RE.search(normalized)) and not bool(
        _JAPANESE_TEXT_RE.search(normalized)
    )


def _append_question_mark(question: str) -> str:
    normalized = normalize_question_text(question)
    if not normalized:
        return ""
    return normalized + ("?" if is_english_text(normalized) else "？")


def _ensure_question_mark(question: str) -> str:
    return _append_question_mark(question)


def _strip_section_prefix(text: str) -> str:
    return _SECTION_PREFIX_RE.sub("", normalize_question_text(text)).strip()


def _document_label(section: DocumentSection) -> str:
    document_key = section.section_id.split("#", 1)[0].replace("\\", "/")
    return Path(document_key).stem or document_key.rsplit("/", 1)[-1]


def _document_topic(section: DocumentSection) -> str:
    label = _strip_section_prefix(_document_label(section)).replace("_", " ").strip()
    for suffix in ja_locale.DOCUMENT_TOPIC_SUFFIXES:
        if label.lower().endswith(suffix.lower()) and len(label) > len(suffix):
            return label[: -len(suffix)].strip()
    return label


def _usable_topic_for_question(topic: str, question: str) -> str:
    if not topic:
        return ""
    if _ASCII_LABEL_RE.fullmatch(topic) and re.search(r"[ぁ-んァ-ヶ一-龠々]", question):
        return ""
    return topic


def _lowercase_initial(text: str) -> str:
    if not text:
        return ""
    if len(text) == 1:
        return text.lower()
    return text[:1].lower() + text[1:]


def _english_subject_from_action_sentence(content: str) -> tuple[str, str]:
    match = re.search(r"([A-Z][A-Za-z0-9 /-]+?)\s+must be\s+(requested|submitted)", content)
    if match:
        return _lowercase_initial(match.group(1).strip()), match.group(2).lower()
    return "", ""


def _english_request_subject(subject: str) -> str:
    if not subject:
        return "request"
    if subject.endswith(" access"):
        return subject[: -len(" access")] + " request"
    if subject.endswith(" requests") or subject.endswith(" request"):
        return subject
    return subject + " request"


def _english_incident_subject(content: str) -> str:
    match = re.search(r"(P\d+ security incidents?)", content, re.IGNORECASE)
    if not match:
        return "a P1 security incident"
    subject = match.group(1)
    if subject.lower().endswith("incidents"):
        subject = subject[:-1]
    return f"a {subject}"


def _generate_english_rule_questions(section: DocumentSection) -> list[str]:
    content = section.content
    content_lower = content.lower()
    subject, action = _english_subject_from_action_sentence(content)
    templates: list[str] = []

    if (
        subject
        and action
        and (
            "business days" in content_lower
            or "in advance" in content_lower
            or "within" in content_lower
        )
    ):
        templates.append(f"When should {subject} be {action}")

    if "request method" in content_lower or "submit through" in content_lower:
        request_subject = _english_request_subject(subject)
        templates.append(f"How should employees submit a {request_subject}")

    if "primary contact order" in content_lower:
        templates.append(f"Who must be contacted first for {_english_incident_subject(content)}")

    if "runbooks review is required" in content_lower or "weekly review cycle" in content_lower:
        templates.append("How often must internal wiki runbooks be reviewed")

    if not templates:
        heading = section.heading.strip() or "this section"
        templates.append(f"What are the key points of {heading}")

    return templates


def naturalize_question(question: str, section: DocumentSection) -> str:
    normalized = _strip_section_prefix(question)
    if not normalized:
        return ""

    if is_english_text(f"{section.heading}\n{section.content}\n{normalized}"):
        return _ensure_question_mark(normalized)

    heading_subject = _strip_section_prefix(section.heading)
    topic = _usable_topic_for_question(_document_topic(section), normalized)
    content = section.content

    if normalized.endswith("の申請方法は何ですか"):
        subject = (
            _strip_section_prefix(normalized[: -len("の申請方法は何ですか")]) or heading_subject
        )
        if subject == "注意事項":
            if topic:
                return _ensure_question_mark(f"{topic}で注意すべき点は何ですか")
            return _ensure_question_mark("注意事項は何ですか")
        if subject in {"提出方法", "申請方法"}:
            if topic:
                return _ensure_question_mark(f"{topic}の提出方法は何ですか")
            return _ensure_question_mark(subject)
        if subject == "残業" and "事前" in content:
            return _ensure_question_mark("残業はどのように事前申請しますか")
        return _ensure_question_mark(f"{subject}はどのように申請しますか")

    if normalized.endswith("はいつまでに対応する必要がありますか"):
        subject = (
            _strip_section_prefix(normalized[: -len("はいつまでに対応する必要がありますか")])
            or heading_subject
        )
        if subject == "締め日":
            return _ensure_question_mark("締め日はいつですか")
        if subject == "打刻" and "打刻漏れ" in content:
            return _ensure_question_mark("打刻漏れはいつまでに修正申請しますか")
        if subject == "介護休業" and "通算" in content and "日" in content:
            return _ensure_question_mark("介護休業は通算何日まで取得できますか")
        return _ensure_question_mark(f"{subject}はいつまでに対応する必要がありますか")

    if normalized.endswith("の要点は何ですか"):
        subject = _strip_section_prefix(normalized[: -len("の要点は何ですか")]) or heading_subject
        if subject == "総則" and "本規則" in content:
            title = topic or _document_label(section)
            return _ensure_question_mark(f"{title}の目的は何ですか")
        if subject == "勤務時間" and _TIME_RANGE_RE.search(content):
            return _ensure_question_mark("所定の勤務時間は何時から何時までですか")
        if subject == "在宅勤務" and "打刻" in content:
            return _ensure_question_mark("在宅勤務日はどのように打刻しますか")
        if subject == "育児休業" and "延長" in content:
            return _ensure_question_mark("育児休業の延長条件は何ですか")
        if subject == "慶弔見舞金" and ("祝金" in content or "弔慰金" in content):
            return _ensure_question_mark("慶弔見舞金の支給内容は何ですか")
        if subject == "出張経費" and ("実費精算" in content or "宿泊費" in content):
            return _ensure_question_mark("出張経費の精算ルールは何ですか")
        if subject == "接待費" and "承認" in content:
            return _ensure_question_mark("接待費の承認条件は何ですか")
        if subject == "服装規定" and "オフィス勤務日" in content:
            return _ensure_question_mark("オフィス勤務日の服装ルールは何ですか")
        if subject == "懲戒" and ("懲戒解雇" in content or "背信行為" in content):
            return _ensure_question_mark("懲戒解雇の主な事由は何ですか")
        if subject == "注意事項":
            if topic:
                return _ensure_question_mark(f"{topic}で注意すべき点は何ですか")
            return _ensure_question_mark("注意事項は何ですか")
        return _ensure_question_mark(f"{subject}の要点は何ですか")

    if normalized == "提出方法は何ですか":
        if topic:
            return _ensure_question_mark(f"{topic}の提出方法は何ですか")
        return _ensure_question_mark(normalized)

    if normalized == "注意事項は何ですか":
        if topic:
            return _ensure_question_mark(f"{topic}で注意すべき点は何ですか")
        return _ensure_question_mark(normalized)

    return _ensure_question_mark(normalized)


def infer_case_category(question: str, section: DocumentSection) -> str:
    normalized = normalize_question_text(question)
    question_types = set(infer_question_types(normalized))
    text = f"{section.heading}\n{section.content}\n{normalized}"

    if len(question_types) >= 2:
        return "general"
    if "how often" in normalized.lower() and (
        "review" in normalized.lower() or "review cycle" in text.lower()
    ):
        return "policy"
    if "延長条件" in normalized or ("延長" in normalized and "最長" in section.content):
        return "exception"
    if "通算" in normalized and "取得" in normalized:
        return "policy"
    if "支給内容" in normalized:
        return "policy"
    if "contact" in question_types:
        return "escalation"
    if "exception" in question_types:
        return "exception"
    if "procedure" in question_types:
        return "procedure"
    if "deadline" in question_types:
        return "deadline"
    if _COMPLIANCE_HINT_RE.search(text):
        return "compliance"
    rule_hint_category = _infer_rule_hint_category(section.heading, section.content, normalized)
    if rule_hint_category != "general":
        return rule_hint_category
    if "policy" in question_types or "amount" in question_types:
        return "policy"
    if "目的" in normalized or _TIME_RANGE_RE.search(section.content):
        return "policy"
    return "general"


def _is_generic_question(question: str) -> bool:
    normalized = normalize_question_text(question)
    if not normalized:
        return True
    return any(token in normalized for token in ja_locale.GENERIC_QUESTION_TOKENS)


def filter_reviewable_questions(questions: list[str]) -> list[str]:
    """Filter and dedupe questions for reviewer-friendly output."""
    cleaned: list[str] = []
    seen_keys: set[str] = set()

    for question in questions:
        normalized = normalize_question_text(question)
        normalized = strip_ordinal_prefix(normalized)
        if not normalized:
            continue
        if len(normalized) < 8 or len(normalized) > 120:
            continue
        key = normalized.lower()
        if key in seen_keys:
            continue
        seen_keys.add(key)
        cleaned.append(_append_question_mark(normalized))

    if len(cleaned) <= 1:
        return cleaned

    non_generic = [question for question in cleaned if not _is_generic_question(question)]
    return non_generic or cleaned


def _extract_keywords(text: str, limit: int = 3) -> list[str]:
    normalized = re.sub(r"[^\w\u3040-\u30ff\u3400-\u9fff]+", " ", text)
    seen: list[str] = []
    for token in normalized.split():
        if len(token) < 2:
            continue
        if token not in seen:
            seen.append(token)
        if len(seen) >= limit:
            break
    return seen


def suggest_keywords(section: DocumentSection) -> list[str]:
    heading_keywords = _extract_keywords(section.heading, limit=2)
    content_keywords = _extract_keywords(section.content, limit=5)
    merged: list[str] = []
    for token in heading_keywords + content_keywords:
        if token not in merged:
            merged.append(token)
        if len(merged) >= 3:
            break
    return merged


def _content_units(content: str) -> list[str]:
    units: list[str] = []
    for raw_line in content.splitlines():
        line = _SPACE_RE.sub(" ", raw_line).strip(" -*\t")
        if not line:
            continue
        parts = [part.strip() for part in _SENTENCE_RE.findall(line) if part.strip()]
        units.extend(parts or [line])
    return units


def _compact_fact_key(text: str) -> str:
    return re.sub(r"\s+", "", text).lower()


def _answer_tokens(text: str) -> list[str]:
    tokens: list[str] = []
    for match in _ANSWER_TOKEN_RE.finditer(_SPACE_RE.sub(" ", text).strip()):
        token = match.group(0).lower()
        if token in _ANSWER_STOPWORDS:
            continue
        if token not in tokens:
            tokens.append(token)
    return tokens


def _looks_like_amount_question(question: str) -> bool:
    lowered = question.lower()
    return any(token in lowered for token in ("いくら", "何円", "月額", "amount", "cost")) or (
        "上限" in question
    )


def _looks_like_day_limit_question(question: str) -> bool:
    lowered = question.lower()
    if "通算" in question and "日" in question:
        return True
    if "何日まで" in question and any(
        token in question for token in ("取得", "休業", "休暇", "利用")
    ):
        return True
    return "up to" in lowered and "day" in lowered


def _extract_deadline_answer(_question: str, section: DocumentSection) -> str:
    units = _content_units(section.content)
    matches: list[tuple[int, str]] = []
    for index, unit in enumerate(units):
        if _DEADLINE_SENTENCE_RE.search(unit):
            matches.append((index, unit))

    if not matches:
        return ""

    first_index, first_unit = matches[0]
    answer_parts = [first_unit]
    if (
        re.search(r"毎月\s*\d{1,2}\s*日", first_unit)
        and first_index + 1 < len(units)
        and ("前営業日" in units[first_index + 1] or "休日" in units[first_index + 1])
    ):
        answer_parts.append(units[first_index + 1])

    return " ".join(answer_parts).strip()


def _extract_amount_answer(question: str, section: DocumentSection) -> str:
    units = _content_units(section.content)
    amounts = []
    for unit in units:
        amounts.extend(_JAPANESE_AMOUNT_RE.findall(unit))

    unique_amounts: list[str] = []
    for amount in amounts:
        normalized = _SPACE_RE.sub(" ", amount).strip()
        if normalized not in unique_amounts:
            unique_amounts.append(normalized)

    if len(unique_amounts) != 1:
        return ""

    for unit in units:
        if unique_amounts[0] in unit and (
            "上限" in unit or "月額" in unit or _looks_like_amount_question(question)
        ):
            return unit
    return ""


def _extract_day_limit_answer(section: DocumentSection) -> str:
    for unit in _content_units(section.content):
        if _DAY_LIMIT_RE.search(unit):
            return unit
    return ""


def _validate_answer_draft(answer: str, section: DocumentSection) -> str | None:
    normalized_answer = _SPACE_RE.sub(" ", answer).strip()
    if len(normalized_answer) < 4:
        return "too_short"
    if len(normalized_answer) > 160:
        return "too_long"

    answer_sentences = [
        part for part in re.split(r"(?<=[。！？])|(?<=[.!?])\s+", normalized_answer) if part.strip()
    ]
    if len(answer_sentences) > 2:
        return "too_long"

    normalized_content = _SPACE_RE.sub(" ", section.content).strip()
    if normalized_answer in normalized_content:
        return None

    content_fact_keys = {
        _compact_fact_key(match.group(0)) for match in _ANSWER_FACT_RE.finditer(normalized_content)
    }
    for match in _ANSWER_FACT_RE.finditer(normalized_answer):
        if _compact_fact_key(match.group(0)) not in content_fact_keys:
            return "numeric_mismatch"

    content_tokens = set(_answer_tokens(normalized_content))
    answer_tokens = _answer_tokens(normalized_answer)
    if answer_tokens and not any(token in content_tokens for token in answer_tokens):
        return "low_overlap"

    return None


def generate_llm_answer_draft(question: str, section: DocumentSection) -> str:
    """Generate a review-only answer draft from a single section. Returns empty on SKIP/failure."""
    system = (
        "You draft short review-only expected answers from a single policy document section. "
        "Use only facts explicitly stated in the section. Return at most two short sentences in the "
        "same language as the question. If the section does not clearly answer the question, return "
        "exactly SKIP."
    )
    user = f"QUESTION:\n{question}\n\nSECTION:\n{section.content}"
    try:
        response = call_openai_chat(
            OPENAI_MODEL,
            system,
            user,
            max_tokens=120,
            temperature=0.0,
        )
    except (APIError, RuntimeError, OSError, TypeError, ValueError) as exc:
        logger.warning("llm answer draft failed for %s: %s", section.section_id, exc)
        return ""

    answer = _SPACE_RE.sub(" ", response.get("text", "").strip()).strip('"')
    if not answer or answer.upper() == "SKIP":
        return ""
    return answer


def generate_expected_answer_draft(
    question: str,
    section: DocumentSection,
    *,
    category: str = "",
    use_llm: bool = False,
) -> tuple[str, list[str]]:
    """Return a safe expected_answer draft plus note markers for reviewer workflows."""
    candidate = ""

    if _looks_like_amount_question(question):
        candidate = _extract_amount_answer(question, section)
    elif _looks_like_day_limit_question(question):
        candidate = _extract_day_limit_answer(section)
    elif category == "deadline" or "deadline" in infer_question_types(question):
        candidate = _extract_deadline_answer(question, section)

    if candidate:
        invalid_reason = _validate_answer_draft(candidate, section)
        if invalid_reason:
            return "", [
                "auto_expected_answer:extract",
                f"auto_expected_answer_invalid:{invalid_reason}",
            ]
        return candidate, ["auto_expected_answer:extract", "auto_expected_answer_status:draft"]

    if not use_llm:
        return "", []

    candidate = generate_llm_answer_draft(question, section)
    if not candidate:
        return "", []

    invalid_reason = _validate_answer_draft(candidate, section)
    if invalid_reason:
        return "", ["auto_expected_answer:llm", f"auto_expected_answer_invalid:{invalid_reason}"]
    return candidate, ["auto_expected_answer:llm", "auto_expected_answer_status:draft"]


def generate_rule_questions(section: DocumentSection, max_questions: int = 1) -> list[str]:
    """Generate stable rule-based questions from a section."""
    heading = section.heading.strip()
    subject = heading or "このセクション"
    content = section.content
    templates: list[str] = []

    if is_english_text(f"{heading}\n{content}"):
        filtered = filter_reviewable_questions(_generate_english_rule_questions(section))
        if filtered:
            return filtered[:max_questions]
        return ["What are the key points of this section?"]

    if any(keyword in subject + content for keyword in ja_locale.DEADLINE_KEYWORDS):
        templates.append(f"{subject}はいつまでに対応する必要がありますか？")
    if any(keyword in subject + content for keyword in ja_locale.APPLICATION_KEYWORDS):
        templates.append(f"{subject}の申請方法は何ですか？")
    if any(keyword in subject + content for keyword in ja_locale.CONDITION_KEYWORDS):
        templates.append(f"{subject}の条件は何ですか？")
    if any(keyword in subject + content for keyword in ja_locale.PROHIBITION_KEYWORDS):
        templates.append(f"{subject}で禁止されていることは何ですか？")

    templates.append(f"{subject}の要点は何ですか？")

    filtered = filter_reviewable_questions(templates)
    if filtered:
        return filtered[:max_questions]
    return ["このセクションの要点は何ですか？"]


def generate_llm_questions(section: DocumentSection, max_questions: int = 2) -> list[str]:
    """Generate natural questions via LLM. Returns [] on failure."""
    system = (
        "You create concise Japanese evaluation questions from policy document sections. "
        "Return strict JSON with a top-level key 'questions' containing 1 to 2 strings."
    )
    user = (
        f"section_id: {section.section_id}\n"
        f"heading: {section.heading or '(none)'}\n"
        f"content:\n{section.content}\n\n"
        f"Create up to {max_questions} reviewable questions."
    )
    try:
        response = call_openai_chat(OPENAI_MODEL, system, user, max_tokens=200)
        payload = json.loads(response["text"])
        questions = payload.get("questions", [])
        if not isinstance(questions, list):
            return []
        cleaned = [str(question) for question in questions]
        filtered = filter_reviewable_questions(cleaned)
        return filtered[:max_questions]
    except (json.JSONDecodeError, KeyError, TypeError, APIError, RuntimeError, OSError) as exc:
        logger.warning("llm question generation failed for %s: %s", section.section_id, exc)
        return []
