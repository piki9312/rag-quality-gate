from __future__ import annotations

import json
from unittest.mock import patch

from rqg.casegen.questions import (
    filter_reviewable_questions,
    generate_llm_questions,
    generate_rule_questions,
    infer_case_category,
    is_english_text,
    naturalize_question,
)
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


def test_filter_reviewable_questions_removes_generic_when_specific_exists():
    questions = [
        "このセクションの要点は何ですか？",
        "申請期限はいつまでですか？",
        "申請期限はいつまでですか？",
    ]

    filtered = filter_reviewable_questions(questions)

    assert filtered == ["申請期限はいつまでですか？"]


def test_generate_llm_questions_filters_short_and_duplicate_questions():
    section = DocumentSection(
        section_id="docs/hr.md#sec-1",
        heading="申請期限",
        content="年次有給休暇は5営業日前までに申請します。",
        level=2,
    )
    payload = {
        "questions": [
            "申請期限はいつまでですか？",
            "申請期限はいつまでですか？",
            "短い",
        ]
    }

    with patch(
        "rqg.casegen.questions.call_openai_chat",
        return_value={"text": json.dumps(payload, ensure_ascii=False)},
    ):
        questions = generate_llm_questions(section, max_questions=2)

    assert questions == ["申請期限はいつまでですか？"]


def test_filter_reviewable_questions_strips_leading_ordinal_prefix_only():
    questions = [
        "1. 申請期限はいつまでですか？",
        "2) 申請期限はいつまでですか？",
        "3、禁止事項は何ですか？",
        "対象は3、4月入社者ですか？",
    ]

    filtered = filter_reviewable_questions(questions)

    assert filtered == [
        "申請期限はいつまでですか？",
        "禁止事項は何ですか？",
        "対象は3、4月入社者ですか？",
    ]


def test_generate_rule_questions_for_access_faq_in_english():
    section = DocumentSection(
        section_id="packs/wiki/documents/access_faq.md#sec-1",
        heading="Access FAQ",
        content=(
            "Temporary VPN exception access must be requested at least 2 business days before access is needed.\n\n"
            "Request method:\n- Submit through the IT service portal\n- Include business reason, requested dates, and manager approval"
        ),
        level=1,
    )

    questions = generate_rule_questions(section, max_questions=3)

    assert is_english_text(section.content) is True
    assert questions == [
        "When should temporary VPN exception access be requested?",
        "How should employees submit a temporary VPN exception request?",
    ]


def test_infer_case_category_uses_rule_hint_fallbacks_for_initial_review_labels():
    deadline_section = DocumentSection(
        section_id="docs/hr.md#sec-1",
        heading="申請期限",
        content="有給休暇は5営業日前までに申請します。",
        level=2,
    )
    procedure_section = DocumentSection(
        section_id="docs/hr.md#sec-2",
        heading="申請手続",
        content="申請は勤怠管理システムから行います。",
        level=2,
    )
    policy_section = DocumentSection(
        section_id="docs/hr.md#sec-3",
        heading="利用要件",
        content="利用対象と承認要件を定めます。",
        level=2,
    )
    compliance_section = DocumentSection(
        section_id="docs/hr.md#sec-4",
        heading="禁止事項",
        content="個人情報の持ち出しは禁止です。",
        level=2,
    )
    general_section = DocumentSection(
        section_id="docs/hr.md#sec-5",
        heading="概要",
        content="この制度の背景を説明します。",
        level=2,
    )

    assert (
        infer_case_category(generate_rule_questions(deadline_section)[0], deadline_section)
        == "deadline"
    )
    assert (
        infer_case_category(generate_rule_questions(procedure_section)[0], procedure_section)
        == "procedure"
    )
    assert (
        infer_case_category(generate_rule_questions(policy_section)[0], policy_section) == "policy"
    )
    assert (
        infer_case_category(generate_rule_questions(compliance_section)[0], compliance_section)
        == "compliance"
    )
    assert (
        infer_case_category(generate_rule_questions(general_section)[0], general_section)
        == "general"
    )


def test_generate_rule_questions_for_security_runbook_in_english():
    section = DocumentSection(
        section_id="packs/wiki/documents/security_runbook.md#sec-1",
        heading="Security Runbook",
        content=(
            "P1 security incidents escalate to security on-call within 15 minutes. Weekly runbooks review is required.\n\n"
            "Assigned knowledge owners refresh internal wiki runbooks during the weekly review cycle.\n\n"
            "Primary contact order:\n1. Security on-call\n2. Incident commander\n3. CISO delegate"
        ),
        level=1,
    )

    questions = generate_rule_questions(section, max_questions=3)

    assert questions == [
        "Who must be contacted first for a P1 security incident?",
        "How often must internal wiki runbooks be reviewed?",
    ]

    assert infer_case_category(questions[0], section) == "escalation"
    assert infer_case_category(questions[1], section) == "policy"


def test_naturalize_question_rewrites_legal_procedure_prompt():
    section = DocumentSection(
        section_id="packs/hr/documents/就業規則.md#sec-1-4",
        heading="第15条 有給休暇",
        content="有給休暇は5営業日前までに申請しなければならない。\n申請は勤怠管理システムから行い、上長の承認を得ること。",
        level=2,
    )

    question = naturalize_question("第15条 有給休暇の申請方法は何ですか？", section)

    assert question == "有給休暇はどのように申請しますか？"
    assert infer_case_category(question, section) == "procedure"


def test_naturalize_question_contextualizes_generic_notice_question():
    section = DocumentSection(
        section_id="packs/hr/documents/経費精算ガイドライン.md#sec-1-5",
        heading="5. 注意事項",
        content="レシートのない経費は原則として精算できません。\n不正な経費申請は懲戒の対象となります。",
        level=2,
    )

    question = naturalize_question("注意事項は何ですか？", section)

    assert question == "経費精算で注意すべき点は何ですか？"
    assert infer_case_category(question, section) == "compliance"


def test_naturalize_question_rewrites_notice_procedure_prompt_to_compliance_question():
    section = DocumentSection(
        section_id="packs/hr/documents/経費精算ガイドライン.md#sec-1-5",
        heading="5. 注意事項",
        content="レシートのない経費は原則として精算できません。\n不正な経費申請は懲戒の対象となります。",
        level=2,
    )

    question = naturalize_question("5. 注意事項の申請方法は何ですか？", section)

    assert question == "経費精算で注意すべき点は何ですか？"
    assert infer_case_category(question, section) == "compliance"


def test_naturalize_question_rewrites_time_range_section():
    section = DocumentSection(
        section_id="packs/hr/documents/就業規則.md#sec-1-2",
        heading="第10条 勤務時間",
        content="勤務時間は 9:00〜18:00（休憩 12:00〜13:00）とする。",
        level=2,
    )

    question = naturalize_question("第10条 勤務時間の要点は何ですか？", section)

    assert question == "所定の勤務時間は何時から何時までですか？"
    assert infer_case_category(question, section) == "policy"


def test_naturalize_question_preserves_rule_document_title_for_purpose_question():
    section = DocumentSection(
        section_id="packs/hr/documents/就業規則.md#sec-1-1",
        heading="第1章 総則",
        content="本規則は、株式会社サンプルの従業員の就業に関する事項を定めるものです。",
        level=1,
    )

    question = naturalize_question("第1章 総則の要点は何ですか？", section)

    assert question == "就業規則の目的は何ですか？"
    assert infer_case_category(question, section) == "policy"


def test_infer_case_category_handles_exception_and_benefit_policy_questions():
    extension_section = DocumentSection(
        section_id="packs/hr/documents/福利厚生制度.md#sec-1-1",
        heading="育児休業",
        content="保育所に入所できない場合等は、最長2歳まで延長が可能です。",
        level=2,
    )
    care_section = DocumentSection(
        section_id="packs/hr/documents/福利厚生制度.md#sec-1-2",
        heading="介護休業",
        content="対象家族1人につき通算93日まで介護休業を取得できます。",
        level=2,
    )
    benefit_section = DocumentSection(
        section_id="packs/hr/documents/福利厚生制度.md#sec-1-3",
        heading="慶弔見舞金",
        content="結婚祝金: 30,000円\n弔慰金: 50,000円（本人の配偶者・1親等）",
        level=2,
    )

    assert infer_case_category("育児休業の延長条件は何ですか？", extension_section) == "exception"
    assert infer_case_category("介護休業は通算何日まで取得できますか？", care_section) == "policy"
    assert infer_case_category("慶弔見舞金の支給内容は何ですか？", benefit_section) == "policy"
