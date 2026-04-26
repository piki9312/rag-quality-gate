# External RAG Walkthrough

This walkthrough is for customer-owned or vendor-owned RAG APIs that already
exist. Use it when the retrieval and answer generation path lives outside RQG,
but you want Proof Gate to run repeatable Quality Pack checks, emit reports, and
block risky changes before production.

External RAG mode keeps customer API differences inside the adapter boundary.
`eval`, `check`, and `gate` receive normalized contexts and do not need to know
the upstream response schema.

## When To Use External RAG Mode

Use external RAG mode when:

- The customer already has a RAG or FAQ API.
- A RAG vendor owns the runtime API and RQG should only evaluate it.
- The customer wants PoC or pre-production gates against the real system path.
- The API returns a schema that differs from RQG's default
  `results[].chunk_id`, `results[].source`, and `results[].text` shape.

Do not use external RAG mode to store customer secrets in this repository. Keep
tokens in environment variables, local secret managers, or GitHub Actions
secrets.

## Install And Diagnose

Install the external extra:

```bash
pip install -e ".[external]"
rqg doctor
```

PowerShell:

```powershell
pip install -e ".[external]"
rqg doctor
```

`rqg doctor` confirms Python, platform, package version, `EMB_MODEL`, and
optional dependency availability before customer onboarding or CI setup.

## Adapter Config

Create `adapter/adapter_config.yml` in the customer project. Start from
[`templates/customer-rqg-template/adapter/adapter_config.example.yml`](../../templates/customer-rqg-template/adapter/adapter_config.example.yml).

Complete example:

```yaml
adapter:
  type: http
  endpoint: https://rag.customer-example.invalid/rag/ask
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

Field meanings:

| Field | Meaning |
|---|---|
| `adapter.type` | Adapter type. Use `http`. |
| `adapter.endpoint` | Customer or vendor RAG API endpoint. Use placeholders in docs and templates, not real private URLs. |
| `adapter.method` | HTTP method. `POST` is supported. |
| `adapter.timeout_seconds` | Request timeout for the external API call. |
| `adapter.auth.type` | Auth style. Use `bearer` for bearer-token APIs. |
| `adapter.auth.token_env` | Environment variable that contains the token. Do not commit the token value. |
| `request_mapping.question_field` | Field name sent to the upstream API for the question. |
| `response_mapping.answer_path` | Dot path to the upstream answer field. |
| `response_mapping.results_path` | Dot path to the upstream list of retrieved contexts. |
| `response_mapping.chunk_id_path` | Dot path inside each result item for the context ID. Optional at runtime. |
| `response_mapping.source_path` | Dot path inside each result item for a reviewable source URL or document name. Optional at runtime. |
| `response_mapping.text_path` | Dot path inside each result item for retrieved context text. Required. |
| `response_mapping.score_path` | Dot path inside each result item for retrieval score. Optional. |

## Dot Path Examples

Simple dot paths are supported:

- `answer`
- `data.answer`
- `sources`
- `results.items`
- `id`
- `content`

For this response:

```json
{
  "data": {
    "answer": "Use the HR portal."
  },
  "results": {
    "items": [
      {
        "id": "hr-1",
        "content": "Use the HR portal for HR policy questions.",
        "url": "https://docs.example.invalid/hr",
        "score": 0.91
      }
    ]
  }
}
```

Use:

```yaml
response_mapping:
  answer_path: data.answer
  results_path: results.items
  chunk_id_path: id
  source_path: url
  text_path: content
  score_path: score
```

See [`examples/external-rag-fixtures`](../../examples/external-rag-fixtures) for
success, empty-result, and schema-mismatch examples.

## Set Secrets Locally

Bash:

```bash
export CUSTOMER_RAG_API_TOKEN="replace-with-session-token"
```

PowerShell:

```powershell
$env:CUSTOMER_RAG_API_TOKEN="replace-with-session-token"
```

Use GitHub Actions secrets for CI. Do not commit `.env`, live bearer tokens,
copied private configs, or raw customer payload captures.

## Run The Gate

From a customer project based on
[`templates/customer-rqg-template`](../../templates/customer-rqg-template):

```bash
rqg gate --pack . --adapter-config adapter/adapter_config.yml --reset-log-dir --index-dir indexes/customer-poc --log-dir logs/customer-poc
```

PowerShell:

```powershell
rqg gate --pack . --adapter-config adapter/adapter_config.yml --reset-log-dir --index-dir indexes\customer-poc --log-dir logs\customer-poc
```

Use isolated `--index-dir` and `--log-dir` values for all demos, customer PoCs,
and CI runs. This avoids stale report files and prevents local demo indexes from
being confused with customer or CI artifacts. External RAG mode does not build a
local FAISS index, but keeping the directory explicit makes commands consistent
across local, external, and CI modes.

## Diagnostics

The adapter reports schema and mapping problems without logging raw secrets or
full raw payload values.

Common diagnostics:

- Missing `answer_path`: the configured answer path was not found.
- Empty answer: the configured answer path exists but is empty.
- Missing `results_path`: the configured results list path was not found.
- Empty results: the adapter normalized zero contexts; connection validation
  reports empty contexts/sources.
- Missing or empty `text_path`: the configured result text path is missing or
  empty. This is blocking because RQG needs context text for eval/check.
- Optional `chunk_id_path`, `source_path`, or `score_path` fallback: the adapter
  can still normalize the result and records `mapping_warnings` in metadata.
- `mapping_warnings`: non-blocking diagnostics attached to normalized contexts
  when optional fields are missing.

Schema mismatch messages include available field names and response-mapping
hints. They should not include bearer tokens, endpoint secrets, raw answers, or
raw retrieved context text.

## What To Review

After a run, inspect:

```bash
python -m json.tool logs/customer-poc/gate-report.json
```

PowerShell:

```powershell
python -m json.tool logs\customer-poc\gate-report.json
```

Use the Markdown report for human review, and use `gate-report.json` for CI
artifacts, future UI, weekly review automation, and customer evidence archives.

## Related References

- [External RAG Adapter Contract](../engineering/external-rag-adapter-contract.md)
- [Customer adapter config example](../../templates/customer-rqg-template/adapter/adapter_config.example.yml)
- [Customer RQG template](../../templates/customer-rqg-template)
- [External RAG fixtures](../../examples/external-rag-fixtures)
