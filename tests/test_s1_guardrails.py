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


def test_guardrails_still_flag_real_numeric_mismatches() -> None:
    expected = "通勤交通費の月額上限は50000円です"
    actual = (
        "通勤交通費の月額上限は月額60,000円です "
        "[経費精算ガイドライン.md@bdd0e3fbc459b02d#chunk0]"
    )

    failure = evaluate_s1_guardrails(expected, actual)

    assert failure is not None
    assert failure.failure_type == "numeric_mismatch"
