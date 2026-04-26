# External RAG Adapter Contract

Proof Gate keeps customer RAG schema differences inside the external adapter
boundary. `eval`, `check`, and `gate` consume normalized contexts and should not
need to know the upstream API response shape.

## CLI Usage

Use `--adapter-config` when a customer RAG API does not already return RQG's
default response shape:

```bash
rqg eval --pack . --adapter-config adapter/adapter_config.yml
rqg gate --pack . --adapter-config adapter/adapter_config.yml
```

The existing flags remain supported for APIs that already return
`results[].chunk_id`, `results[].source`, and `results[].text`:

```bash
rqg gate --pack . \
  --rag-endpoint https://rag.customer-example.com/search \
  --rag-api-key-env CUSTOMER_RAG_API_TOKEN
```

## Config Shape

```yaml
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
  answer_path: answer
  results_path: sources
  chunk_id_path: id
  source_path: url
  text_path: content
  score_path: score
```

Simple dot paths are supported:

- `answer`
- `data.answer`
- `sources`
- `results.items`
- `id`
- `content`

## Normalized Context Contract

The adapter maps each result item to RQG's internal context shape:

| Normalized field | Required | Source mapping | Notes |
|---|---:|---|---|
| `chunk_id` | No | `chunk_id_path` | Generated as `external-result-N` if missing. |
| `source` | No | `source_path` | Uses `external-rag` if missing. |
| `text` | Yes | `text_path` | Retrieved context text used by eval/check. |
| `score` | No | `score_path` | Parsed as float when present. |
| `metadata.mapping_warnings` | No | adapter diagnostics | Contains optional-field mapping warnings. |

`answer_path` is validated when configured so onboarding teams can catch empty
or mismapped answer fields early. Existing gate decision semantics do not change:
RQG still evaluates using its existing runner and report contracts.

## Diagnostics

The adapter raises schema diagnostics without logging raw secrets or full
customer payload values.

Common diagnostics include:

- Missing `answer_path`: the configured answer dot path was not found.
- Missing `results_path`: the configured results list dot path was not found.
- Empty results: the adapter returns zero contexts; connection validation reports
  `empty contexts/sources`.
- Missing `text_path` in a result item: the configured context text path was not
  found and the response cannot be normalized.
- Missing optional `chunk_id_path`, `source_path`, or `score_path`: the result is
  still normalized, and `metadata.mapping_warnings` records the fallback.

Schema mismatch messages include available field names and a response mapping
hint. They intentionally avoid printing bearer tokens, endpoint secrets, or raw
answer/context text.

## Template

Start from:

```text
templates/customer-rqg-template/adapter/adapter_config.example.yml
```

Copy it to `adapter/adapter_config.yml` in the customer project and keep live
credentials in environment variables or CI secrets.
