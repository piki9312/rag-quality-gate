from rqg.quality.s1_guardrails import evaluate_s1_guardrails


def test_guardrails_ignore_chunk_id_citation_numbers() -> None:
    expected = "経費精算の締め日は毎月25日で25日が休日の場合は前営業日です"
    actual = (
        "経費精算の締め日は毎月25日で25日が休日の場合は前営業日です "
        "[経費精算ガイドライン.md@bdd0e3fbc459b02d#chunk0]"
    )

    assert evaluate_s1_guardrails(expected, actual) is None


def test_guardrails_normalize_comma_formatted_currency() -> None:
    expected = "通勤交通費の月額上限は50000円です"
    actual = (
        "通勤交通費の月額上限は月額50,000円です "
        "[経費精算ガイドライン.md@bdd0e3fbc459b02d#chunk0]"
    )

    assert evaluate_s1_guardrails(expected, actual) is None


def test_guardrails_ignore_extra_unrelated_numeric_terms() -> None:
    expected = "通勤交通費の月額上限は50000円です"
    actual = (
        "通勤交通費の上限は月額50,000円です。"
        "定期券の場合は6ヶ月分をまとめて申請いただけます。 "
        "[経費精算ガイドライン.md@bdd0e3fbc459b02d#chunk0]"
    )

    assert evaluate_s1_guardrails(expected, actual) is None


def test_guardrails_ignore_numbered_list_ordinals_when_expected_has_units() -> None:
    expected = "懲戒解雇の主な事由には無断欠勤14日以上が含まれます"
    actual = (
        "1. 業務上の重大な背信行為 2. 正当な理由のない無断欠勤が14日以上に及んだ場合 "
        "3. 刑事事件で有罪判決を受けた場合 4. 会社の機密情報を故意に漏洩した場合 "
        "5. 就業規則に著しく違反した場合"
    )

    assert evaluate_s1_guardrails(expected, actual) is None


def test_guardrails_still_flag_real_numeric_mismatches() -> None:
    expected = "通勤交通費の月額上限は50000円です"
    actual = (
        "通勤交通費の月額上限は月額60,000円です "
        "[経費精算ガイドライン.md@bdd0e3fbc459b02d#chunk0]"
    )

    failure = evaluate_s1_guardrails(expected, actual)

    assert failure is not None
    assert failure.failure_type == "numeric_mismatch"
