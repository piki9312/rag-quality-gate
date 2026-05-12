from __future__ import annotations

import logging

from rqg.quality.provenance import load_yaml_or_json


def test_load_yaml_or_json_logs_sanitized_parse_failure(tmp_path, caplog) -> None:
    config_path = tmp_path / "customer-config.yml"
    config_path.write_text("token: sk-secret\nbad: [\n", encoding="utf-8")

    with caplog.at_level(logging.WARNING, logger="rqg.quality.provenance"):
        payload = load_yaml_or_json(config_path)

    assert payload == {}
    assert len(caplog.records) == 1
    message = caplog.records[0].getMessage()
    assert "Failed to parse config file" in message
    assert "customer-config.yml" in message
    assert "ParserError" in message
    assert "sk-secret" not in message
