from __future__ import annotations

from unittest.mock import patch

from rqg.casegen.questions import generate_llm_questions, generate_rule_questions
from rqg.casegen.sections import DocumentSection


def test_generate_rule_questions_from_heading():
    section = DocumentSection(
        section_id="docs/hr.md#sec-1",
        heading="申請期限",
        content="年次有給休暇は5営業日前までに申請します。",
        level=2,
    )

    questions = generate_rule_questions(section)

    assert len(questions) >= 1
    assert "いつまで" in questions[0]


def test_generate_rule_questions_without_heading():
    section = DocumentSection(
        section_id="docs/hr.md#sec-1",
        heading="",
        content="年次有給休暇は5営業日前までに申請します。",
        level=1,
    )

    questions = generate_rule_questions(section)

    assert len(questions) >= 1


def test_generate_llm_questions_falls_back_to_empty_list_on_error():
    section = DocumentSection(
        section_id="docs/hr.md#sec-1",
        heading="申請期限",
        content="年次有給休暇は5営業日前までに申請します。",
        level=2,
    )

    with patch("rqg.casegen.questions.call_openai_chat", side_effect=RuntimeError("boom")):
        questions = generate_llm_questions(section)

    assert questions == []
