"""Question candidate generation from document sections."""

from __future__ import annotations

import json
import logging
import re

from rqg.casegen.sections import DocumentSection
from rqg.serving.llm_client import OPENAI_MODEL, call_openai_chat

logger = logging.getLogger(__name__)


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
    subject = section.heading.strip() or "この内容"
    content = section.content
    templates: list[str] = []

    if any(keyword in subject + content for keyword in ["期限", "いつまで", "日まで", "期日"]):
        templates.append(f"{subject}はいつまでに対応する必要がありますか？")
    if any(keyword in subject + content for keyword in ["申請", "手続", "届け出", "提出"]):
        templates.append(f"{subject}の申請方法は何ですか？")
    if any(keyword in subject + content for keyword in ["条件", "対象", "要件"]):
        templates.append(f"{subject}の条件は何ですか？")
    if any(keyword in subject + content for keyword in ["禁止", "不可", "してはいけない"]):
        templates.append(f"{subject}で禁止されていることは何ですか？")

    templates.append(f"{subject}の内容は何ですか？")

    deduped: list[str] = []
    for question in templates:
        if question not in deduped:
            deduped.append(question)
        if len(deduped) >= max_questions:
            break
    return deduped or ["このセクションの要点は何ですか？"]


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
        cleaned = [str(question).strip() for question in questions if str(question).strip()]
        return cleaned[:max_questions]
    except Exception as exc:
        logger.warning("llm question generation failed for %s: %s", section.section_id, exc)
        return []
