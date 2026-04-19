"""Question candidate generation from document sections."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path

from openai import APIError

from rqg.casegen.sections import DocumentSection
from rqg.quality.case_schema import infer_question_types
from rqg.serving.llm_client import OPENAI_MODEL, call_openai_chat

logger = logging.getLogger(__name__)

_SPACE_RE = re.compile(r"\s+")
_SECTION_PREFIX_RE = re.compile(r"^(?:第[0-9０-９]+[条章]\s*|[0-9０-９]+[.)．]\s*)")
_TIME_RANGE_RE = re.compile(r"\d{1,2}:\d{2}\s*[〜~\-]\s*\d{1,2}:\d{2}")
_ASCII_LABEL_RE = re.compile(r"^[A-Za-z0-9_\- ]+$")
_COMPLIANCE_HINT_RE = re.compile(r"禁止|違反|漏洩|懲戒|機密情報|個人情報|施錠|暗号化")
_ASCII_ALPHA_RE = re.compile(r"[A-Za-z]")
_JAPANESE_TEXT_RE = re.compile(r"[ぁ-んァ-ヶ一-龠々]")


def normalize_question_text(question: str) -> str:
    """Normalize question text for dedupe and quality checks."""
    compact = _SPACE_RE.sub(" ", question.strip())
    return compact.rstrip("?？ ")


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
    for suffix in ("ガイドライン", "制度", "規定", "規程", "runbook", "faq", "policy"):
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
    if "list" in question_types or "policy" in question_types or "amount" in question_types:
        return "policy"
    if "目的" in normalized or _TIME_RANGE_RE.search(section.content):
        return "policy"
    return "general"


def _is_generic_question(question: str) -> bool:
    normalized = normalize_question_text(question)
    if not normalized:
        return True
    generic_tokens = ["この内容", "このセクション", "本文", "本セクション"]
    return any(token in normalized for token in generic_tokens)


def filter_reviewable_questions(questions: list[str]) -> list[str]:
    """Filter and dedupe questions for reviewer-friendly output."""
    cleaned: list[str] = []
    seen_keys: set[str] = set()

    for question in questions:
        normalized = normalize_question_text(question)
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

    if any(keyword in subject + content for keyword in ["期限", "いつまで", "日まで", "期日"]):
        templates.append(f"{subject}はいつまでに対応する必要がありますか？")
    if any(keyword in subject + content for keyword in ["申請", "手続", "届け出", "提出"]):
        templates.append(f"{subject}の申請方法は何ですか？")
    if any(keyword in subject + content for keyword in ["条件", "対象", "要件"]):
        templates.append(f"{subject}の条件は何ですか？")
    if any(keyword in subject + content for keyword in ["禁止", "不可", "してはいけない"]):
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
