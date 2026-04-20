from __future__ import annotations

import json

from rqg.cli.helpers import write_json_data_output, write_text_output


def test_write_text_output_creates_parent_dirs(tmp_path) -> None:
    output_path = tmp_path / "nested" / "report.md"

    saved_path = write_text_output(output_path, "# Report\n")

    assert saved_path == output_path
    assert output_path.read_text(encoding="utf-8") == "# Report\n"


def test_write_json_data_output_serializes_payload(tmp_path) -> None:
    output_path = tmp_path / "nested" / "report.json"

    saved_path = write_json_data_output(output_path, {"status": "ok", "count": 2})

    assert saved_path == output_path
    assert json.loads(output_path.read_text(encoding="utf-8")) == {"status": "ok", "count": 2}
