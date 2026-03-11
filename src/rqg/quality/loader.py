"""CSV ケースローダー — Quality Pack のテストケースを読み込む。"""

from __future__ import annotations

import csv
from pathlib import Path

from .models import QATestCase


def load_cases(file_path: str) -> list[QATestCase]:
    """CSV ファイルから QATestCase のリストを読み込む。

    CSV カラム（必須: case_id, name, question。他はオプション）:
        case_id, name, severity, question, expected_chunks,
        expected_keywords, golden_answer, category, owner, min_pass_rate
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Test case file not found: {file_path}")

    cases: list[QATestCase] = []
    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # セミコロン区切りのリスト
            expected_kw = [
                k.strip()
                for k in row.get("expected_keywords", "").split(";")
                if k.strip()
            ]
            expected_ch = [
                c.strip()
                for c in row.get("expected_chunks", "").split(";")
                if c.strip()
            ]
            min_pr = 0.0
            if row.get("min_pass_rate"):
                try:
                    min_pr = float(row["min_pass_rate"])
                except ValueError:
                    pass

            case = QATestCase(
                case_id=row.get("case_id", ""),
                name=row.get("name", ""),
                question=row.get("question", ""),
                severity=row.get("severity", "S2").strip().upper(),
                expected_keywords=expected_kw,
                expected_chunks=expected_ch,
                golden_answer=row.get("golden_answer", ""),
                category=row.get("category", "general"),
                owner=row.get("owner", ""),
                min_pass_rate=min_pr,
            )
            cases.append(case)
    return cases
