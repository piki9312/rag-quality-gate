# Customer RQG Project Template

This template is a starting point for a customer-specific PoC repository that uses `rag-quality-gate` as an installed package instead of copying runtime code into the customer repo.

Use it when you want a clean project skeleton for:

- customer-approved evaluation cases
- customer-approved source documents
- repeatable gate runs with isolated index and log directories
- optional external RAG adapter integration
- GitHub Actions automation for regular gate runs

## What This Template Contains

- `cases.csv`: customer evaluation cases in the formal 16-column schema
- `documents/`: source documents used for local mock or local FAISS runs
- `adapter/adapter_config.example.yml`: external RAG adapter placeholder
- `gate.yml`: minimal gate threshold configuration
- `quality-pack.yml`: pack metadata and failure next-action hints
- `.github/workflows/monthly-gate.yml`: scheduled and manual gate workflow
- `reports/`: a place for reviewed report exports that you want to keep

## How To Start A Customer PoC

1. Copy `templates/customer-rqg-template/` into a new customer-specific repository.
2. Update `requirements.txt` to point to your tagged `rag-quality-gate` package source.
3. Replace the placeholder cases in `cases.csv` with customer-approved cases.
4. Replace the placeholder files in `documents/` with sanitized or approved customer documents.
5. Update `gate.yml` thresholds and `quality-pack.yml` metadata for the customer engagement.
6. If the customer uses an external RAG endpoint, copy `adapter/adapter_config.example.yml` to `adapter/adapter_config.yml` and fill in the endpoint, request mapping, and response mapping.
7. Configure secrets with environment variables or GitHub Actions secrets instead of committing tokens.

## Required Pack Root Layout

To work with `rqg validate-pack --pack .` and `rqg gate --pack .`, keep these files at the repository root:

- `cases.csv`
- `quality-pack.yml`
- `gate.yml`
- `documents/`

This root layout matches the built-in `--pack` resolver.

## Install Dependencies

Bash:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## Where To Put Customer Cases

Put customer-approved cases in `cases.csv`.

Use the formal 16-column schema:

`case_id,name,status,severity,eval_mode,question,expected_answer,expected_evidence,expected_keywords,category,source_doc,owner,min_case_score,updated_at,last_reviewed_at,notes`

Keep the first version small. A practical starting point is 3-5 S1 cases and 10-30 S2 cases.

## Where To Put Customer Documents

Put customer-approved or sanitized source documents in `documents/`.

Use stable file names and keep `source_doc` plus `expected_evidence` aligned to those files. When possible, use evidence anchors such as `policy.md#sec-2` so retrieval expectations stay explicit.

## Configure The External RAG Adapter

This template keeps local document evaluation as the default path. If the customer uses an external RAG endpoint:

1. Copy `adapter/adapter_config.example.yml` to `adapter/adapter_config.yml`.
2. Replace the placeholder endpoint with the customer endpoint.
3. Keep the bearer token in an environment variable such as `CUSTOMER_RAG_API_TOKEN`.
4. Confirm that the upstream response can be mapped to RQG's normalized context fields.

The adapter config supports simple dot paths for common customer schemas:

```yaml
adapter:
  type: http
  endpoint: https://rag.customer-example.com/rag/ask
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

`text_path` is required because it becomes the retrieved context used by eval/check. `chunk_id_path`, `source_path`, and `score_path` are optional; missing chunk IDs or sources are replaced with diagnostic fallback values.

Example connection check:

```bash
export CUSTOMER_RAG_API_TOKEN="replace-with-session-token"
python -m rqg.cli validate-connection \
  --endpoint https://rag.customer-example.com/search \
  --query "password reset" \
  --top-k 3 \
  --api-key-env CUSTOMER_RAG_API_TOKEN \
  --output reports/tmp/connection-check.json
```

If you move to external retrieval, prefer `--adapter-config` for `rqg eval` or `rqg gate` when the customer API does not already return RQG's default `results[].chunk_id`, `results[].source`, and `results[].text` shape.

```bash
python -m rqg.cli gate --pack . \
  --adapter-config adapter/adapter_config.yml \
  --reset-log-dir \
  --index-dir indexes/external-gate \
  --log-dir logs/external-gate
```

The older `--rag-endpoint` and `--rag-api-key-env` flags still work for endpoints that already return the default RQG response shape.

## Run validate-pack

This template uses the standard root pack layout, so pack onboarding can run directly from the repository root.

```bash
python -m rqg.cli validate-pack --pack .
```

Expected result for the placeholder template: onboarding validation is OK.

## Run gate With Isolated Index And Log Directories

Use isolated directories for every local or CI run so retrieval never reuses a stale shared index.

Bash:

```bash
rm -rf indexes/customer-poc
rm -rf logs/customer-poc
python -m rqg.cli gate --pack . \
  --mock \
  --index-dir indexes/customer-poc \
  --reset-log-dir \
  --log-dir logs/customer-poc
```

PowerShell:

```powershell
Remove-Item -Recurse -Force indexes\customer-poc -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force logs\customer-poc -ErrorAction SilentlyContinue
python -m rqg.cli gate --pack . `
  --mock `
  --index-dir indexes\customer-poc `
  --reset-log-dir `
  --log-dir logs\customer-poc
```

For customer-specific external retrieval with a mapped customer response schema, use the adapter config:

```bash
python -m rqg.cli gate --pack . \
  --adapter-config adapter/adapter_config.yml \
  --reset-log-dir \
  --index-dir indexes/external-gate \
  --log-dir logs/external-gate
```

## Inspect gate-report.md

After a local run, inspect the Markdown report first:

```bash
cat logs/customer-poc/gate-report.md
python -m json.tool logs/customer-poc/gate-report.json
```

The Markdown report is for human review. The JSON bundle is for CI, automation, or downstream dashboards.

## Handle Secrets Safely

- Keep API keys and bearer tokens in environment variables during local work.
- Use GitHub Actions secrets such as `CUSTOMER_RAG_API_TOKEN` in CI.
- Do not commit `.env`, `adapter/secrets.yml`, or copied adapter configs that include live credentials.
- If you need customer-private endpoints, keep them in repo variables or environment-specific deployment config, not in tracked template files.

## How A Customer Repo Uses This Template

The customer repo installs `rag-quality-gate` as a package, stores customer-owned cases and documents in the standard pack root layout, and runs `rqg validate-pack`, `rqg gate`, and report review without modifying `rag-quality-gate` runtime code.
