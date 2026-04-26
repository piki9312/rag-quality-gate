# External RAG Fixtures

These fixtures are small, fake external RAG API responses for adapter mapping
tests, walkthroughs, and customer onboarding conversations. They contain no real
customer data, no real endpoints, and no secrets.

## success_response.json

This response matches the example mapping used in the external RAG walkthrough:

```yaml
response_mapping:
  answer_path: answer
  results_path: sources
  chunk_id_path: id
  source_path: url
  text_path: content
  score_path: score
```

Expected behavior: the adapter normalizes each `sources[]` item into RQG
contexts with `chunk_id`, `source`, `text`, and `score`.

## empty_result_response.json

This response has an empty answer and no sources:

```json
{
  "answer": "",
  "sources": []
}
```

Expected diagnostic with the example mapping: `empty answer` at `answer_path`.
If the answer were non-empty but `sources` remained empty, connection validation
should report empty contexts/sources.

## schema_mismatch_response.json

This response intentionally uses different names:

- `response` instead of `answer`
- `citations` instead of `sources`
- `docId` instead of `id`
- `body` instead of `content`
- `link` instead of `url`
- `confidence` instead of `score`

The default walkthrough mapping will fail with missing `answer_path` or
`results_path` diagnostics and show available fields such as `citations` and
`response`.

This mapping would handle the fixture:

```yaml
response_mapping:
  answer_path: response
  results_path: citations
  chunk_id_path: docId
  source_path: link
  text_path: body
  score_path: confidence
```

If `chunk_id_path`, `source_path`, or `score_path` are wrong or missing, the
adapter can still normalize the response and will attach `mapping_warnings` to
the result metadata. If `text_path` is wrong or empty, normalization fails
because RQG needs retrieved context text for eval/check.
