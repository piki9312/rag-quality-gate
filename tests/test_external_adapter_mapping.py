from __future__ import annotations

import uuid
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from rqg.serving.external_adapter import (
    ExternalRAGResponseMapping,
    ExternalRAGSchemaError,
    HTTPRAGAdapter,
    load_http_rag_adapter_config,
)


def test_response_mapping_maps_answer_sources_id_content_url_score() -> None:
    adapter = HTTPRAGAdapter(
        endpoint="https://rag.example.com/ask",
        response_mapping=ExternalRAGResponseMapping(
            answer_path="answer",
            results_path="sources",
            chunk_id_path="id",
            source_path="url",
            text_path="content",
            score_path="score",
        ),
    )

    results = adapter._normalize(
        {
            "answer": "Use the HR portal.",
            "sources": [
                {
                    "id": "chunk-1",
                    "url": "https://docs.example.com/hr",
                    "content": "Use the HR portal for policy questions.",
                    "score": "0.91",
                }
            ],
        }
    )

    assert results == [
        {
            "chunk_id": "chunk-1",
            "source": "https://docs.example.com/hr",
            "text": "Use the HR portal for policy questions.",
            "score": 0.91,
        }
    ]


def test_response_mapping_supports_nested_dot_paths() -> None:
    adapter = HTTPRAGAdapter(
        endpoint="https://rag.example.com/ask",
        response_mapping=ExternalRAGResponseMapping(
            answer_path="data.answer",
            results_path="results.items",
            chunk_id_path="meta.id",
            source_path="meta.source",
            text_path="payload.content",
            score_path="rank.score",
        ),
    )

    results = adapter._normalize(
        {
            "data": {"answer": "Password resets go through IT."},
            "results": {
                "items": [
                    {
                        "meta": {"id": "it-1", "source": "it-policy.md"},
                        "payload": {"content": "Password resets go through IT."},
                        "rank": {"score": 0.8},
                    }
                ]
            },
        }
    )

    assert results[0]["chunk_id"] == "it-1"
    assert results[0]["source"] == "it-policy.md"
    assert results[0]["text"] == "Password resets go through IT."
    assert results[0]["score"] == 0.8


def test_response_mapping_schema_mismatch_reports_available_fields() -> None:
    adapter = HTTPRAGAdapter(
        endpoint="https://rag.example.com/ask",
        response_mapping=ExternalRAGResponseMapping(
            answer_path="data.answer",
            results_path="results.items",
            text_path="content",
        ),
    )

    with pytest.raises(ExternalRAGSchemaError) as excinfo:
        adapter._normalize({"answer": "Use HR.", "sources": []})

    message = str(excinfo.value)
    assert "missing answer_path 'data.answer'" in message
    assert "Available fields: answer, sources" in message
    assert "response_mapping" in message
    assert "Use HR." not in message


def test_response_mapping_empty_results_returns_empty_list() -> None:
    adapter = HTTPRAGAdapter(
        endpoint="https://rag.example.com/ask",
        response_mapping=ExternalRAGResponseMapping(
            answer_path="answer",
            results_path="sources",
            text_path="content",
        ),
    )

    assert adapter._normalize({"answer": "No result.", "sources": []}) == []


def test_response_mapping_missing_text_path_is_schema_error() -> None:
    adapter = HTTPRAGAdapter(
        endpoint="https://rag.example.com/ask",
        response_mapping=ExternalRAGResponseMapping(
            answer_path="answer",
            results_path="sources",
            chunk_id_path="id",
            source_path="url",
            text_path="content",
        ),
    )

    with pytest.raises(ExternalRAGSchemaError) as excinfo:
        adapter._normalize({"answer": "Use HR.", "sources": [{"id": "1", "url": "doc"}]})

    assert "missing text_path 'content'" in str(excinfo.value)
    assert "Available fields: id, url" in str(excinfo.value)


def test_response_mapping_optional_fields_emit_metadata_warnings() -> None:
    adapter = HTTPRAGAdapter(
        endpoint="https://rag.example.com/ask",
        response_mapping=ExternalRAGResponseMapping(
            answer_path="answer",
            results_path="sources",
            chunk_id_path="id",
            source_path="url",
            text_path="content",
            score_path="score",
        ),
    )

    results = adapter._normalize({"answer": "Use HR.", "sources": [{"content": "Use HR."}]})

    assert results[0]["chunk_id"] == "external-result-1"
    assert results[0]["source"] == "external-rag"
    warnings = results[0]["metadata"]["mapping_warnings"]
    assert "missing optional chunk_id_path 'id'; generated external-result-1" in warnings
    assert "missing optional source_path 'url'; using external-rag" in warnings
    assert "missing optional score_path 'score'" in warnings


def test_adapter_config_loads_new_mapping_shape() -> None:
    config_path = Path("tests/.tmp") / f"{uuid.uuid4()}-adapter-config.yml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        """
adapter:
  type: http
  endpoint: https://example.com/rag/ask
  method: POST
  timeout_seconds: 30
  auth:
    type: bearer
    token_env: CUSTOMER_RAG_API_TOKEN
request_mapping:
  question_field: question
response_mapping:
  answer_path: data.answer
  results_path: results.items
  chunk_id_path: id
  source_path: url
  text_path: content
  score_path: score
""".strip(),
        encoding="utf-8",
    )

    config = load_http_rag_adapter_config(config_path)

    assert config.endpoint == "https://example.com/rag/ask"
    assert config.timeout_sec == 30
    assert config.api_key_env == "CUSTOMER_RAG_API_TOKEN"
    assert config.request_mapping.question_field == "question"
    assert config.response_mapping.answer_path == "data.answer"
    assert config.response_mapping.results_path == "results.items"


def test_existing_rag_endpoint_behavior_still_maps_default_results() -> None:
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "results": [{"chunk_id": "c1", "source": "policy.md", "text": "hello"}]
    }

    with patch("rqg.serving.external_adapter.httpx.post", return_value=mock_resp) as post:
        adapter = HTTPRAGAdapter(endpoint="https://rag.example.com/search")
        results = adapter.search("paid leave", top_k=2)

    assert results[0]["chunk_id"] == "c1"
    assert results[0]["source"] == "policy.md"
    assert results[0]["text"] == "hello"
    assert post.call_args.kwargs["json"] == {"query": "paid leave", "top_k": 2}
