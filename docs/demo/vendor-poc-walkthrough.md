# Vendor PoC Walkthrough

This walkthrough is for RAG vendors and AI implementation teams that need to prove a customer-facing RAG/FAQ agent can move from PoC to production-quality operation.

It connects the recent quality-layer improvements into one first-run path:

- `validate-pack` onboarding diagnostics
- `eval`, `check`, and `gate`
- `gate-report.json` and Markdown report review
- S1 failure interpretation
- external RAG schema mismatch diagnostics
- Windows PowerShell command examples

No customer data or secrets are required. The walkthrough uses `examples/vendor-poc-pack`, a small English pack with one intentional S1 failure.

## What You Will Prove

By the end, you should be able to show a customer:

1. The Quality Pack is structurally valid before the gate runs.
2. The gate can detect an S1 failure before production.
3. `gate-report.md` is readable by humans.
4. `gate-report.json` is stable enough for downstream consumers.
5. External RAG response schema issues produce actionable diagnostics.

## Prerequisites

Bash:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
pip install -e .
```

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -U pip
pip install -e .
```

If PowerShell blocks activation scripts:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

If console text looks garbled on Windows, set UTF-8 for the current session:

```powershell
chcp 65001
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
```

Use the base install for this client-facing walkthrough. It is enough for `validate-pack`, `check`, `gate`, and report viewing, and it avoids installing `sentence-transformers`.

Install extras only when needed:

```bash
# External RAG HTTP adapter and connection validation.
pip install -e ".[external]"

# Local embedding, FAISS index, and sentence-transformers features.
pip install -e ".[embedding]"

# Developer formatting/test tools only.
pip install -e ".[dev]"

# Full developer test setup, including external, serve, and embedding extras.
pip install -e ".[all]"
```

## Pack Layout

The sample pack lives at:

```text
examples/vendor-poc-pack/
  cases.csv
  gate.yml
  quality-pack.yml
  documents/support_policy.md
```

The S1 case `VPOC001` intentionally expects the keyword `security owner hotline`, which is not present in the source document. This makes the gate fail in a controlled way so you can demonstrate S1 blocking behavior.

## 1. Validate The Pack

Bash:

```bash
rqg validate-pack --pack examples/vendor-poc-pack --output runs/vendor-poc/pack-validation.json
```

PowerShell:

```powershell
rqg validate-pack --pack examples\vendor-poc-pack --output runs\vendor-poc\pack-validation.json
```

Expected result:

- `Pack onboarding validation: OK`
- `finding_counts.error` is `0` in `pack-validation.json`
- warnings may appear as onboarding guidance, but warnings alone do not fail the command

Review the JSON:

Bash:

```bash
python -m json.tool runs/vendor-poc/pack-validation.json
```

PowerShell:

```powershell
python -m json.tool runs\vendor-poc\pack-validation.json
```

## 2. Run eval

Use `--mock` for first-run PoCs so no LLM API key is needed.

Bash:

```bash
rqg eval --pack examples/vendor-poc-pack \
  --mock \
  --index-dir runs/vendor-poc/index \
  --log-dir runs/vendor-poc/eval
```

PowerShell:

```powershell
rqg eval --pack examples\vendor-poc-pack `
  --mock `
  --index-dir runs\vendor-poc\index `
  --log-dir runs\vendor-poc\eval
```

Expected result:

- evaluation records are written under `runs/vendor-poc/eval`
- at least one record should show the intentional S1 keyword miss

## 3. Run check

Bash:

```bash
rqg check --pack examples/vendor-poc-pack --log-dir runs/vendor-poc/eval
```

PowerShell:

```powershell
rqg check --pack examples\vendor-poc-pack --log-dir runs\vendor-poc\eval
```

Expected result:

- `gate-report.md`
- `gate-decision.json`
- `gate-report.json`

The status should be `fail` because the S1 case is intentionally broken.

## 4. Run gate In One Command

`gate` combines eval and check. This is the command most vendors put in CI once the pack is stable.

`--pack` fills `cases.csv`, `documents/`, `gate.yml`, and `quality-pack.yml` from the pack root. If you also pass a lower-level argument such as `--docs` or `--config`, the explicit value wins.

Bash:

```bash
rqg gate --pack examples/vendor-poc-pack \
  --mock \
  --index-dir runs/vendor-poc/gate-index \
  --log-dir runs/vendor-poc/gate \
  --reset-log-dir
```

PowerShell:

```powershell
rqg gate --pack examples\vendor-poc-pack `
  --mock `
  --index-dir runs\vendor-poc\gate-index `
  --log-dir runs\vendor-poc\gate `
  --reset-log-dir
```

Expected result:

- exit code `1`
- `runs/vendor-poc/gate/gate-report.md`
- `runs/vendor-poc/gate/gate-decision.json`
- `runs/vendor-poc/gate/gate-report.json`

The non-zero exit is expected for this demo. It proves an S1 production-blocking issue is detected.

## 5. Review The Reports

Bash:

```bash
cat runs/vendor-poc/gate/gate-report.md
cat runs/vendor-poc/gate/gate-decision.json
python -m json.tool runs/vendor-poc/gate/gate-report.json
```

PowerShell:

```powershell
Get-Content runs\vendor-poc\gate\gate-report.md -Encoding UTF8
python -m json.tool runs\vendor-poc\gate\gate-decision.json
python -m json.tool runs\vendor-poc\gate\gate-report.json
```

Use the Markdown report for a human review conversation. Use `gate-report.json` for downstream consumers such as CI annotations, weekly review automation, dashboards, or customer evidence archives.

Do not remove or rename existing `gate-report.json` fields in downstream integrations. Treat it as a machine-readable contract.

If Markdown output looks garbled on Windows PowerShell, run the UTF-8 setup commands in the prerequisites section or open the file in VS Code.

## 6. Read The S1 Failure

In this pack, `VPOC001` is S1 and intentionally fails.

Look for:

- `case_id`: `VPOC001`
- `severity`: `S1`
- `failure_type`: usually `keyword_miss`
- `failure_reason`: explains which threshold was not met
- `category`: `escalation`
- next-action hints from `quality-pack.yml`

How to explain this to a customer:

> The retrieval path found support-policy evidence, but the answer did not include all S1-required business terms. Because this is an S1 escalation case, the gate blocks release until the case definition, source document, prompt, or model response is corrected.

Typical fixes:

- If `security owner hotline` is a real customer requirement, add it to the source document or update the RAG content.
- If it is not a real requirement, remove it from `expected_keywords`.
- If the prompt should mention escalation ownership, update the prompt and re-run `rqg gate`.

## 7. External RAG Schema Mismatch Diagnostic Example

When replacing local documents with a real customer RAG endpoint, the endpoint must return the external RAG contract expected by the adapter:

```json
{
  "results": [
    {
      "chunk_id": "support_policy.md#sec-1",
      "source": "support_policy.md",
      "text": "Employees can reset their password from the self-service portal.",
      "score": 0.92
    }
  ]
}
```

A common schema mismatch looks like this:

```json
{
  "answer": "Employees should contact IT.",
  "data": [
    {
      "id": "support-1",
      "body": "Employees can reset their password from the self-service portal."
    }
  ]
}
```

Run connection validation against your endpoint:

Bash:

```bash
export RQG_API_KEY="replace-with-your-session-token"
rqg validate-connection \
  --endpoint https://rag.example.com/search \
  --query "password reset" \
  --top-k 3 \
  --api-key-env RQG_API_KEY \
  --output runs/vendor-poc/external-connection.json
```

PowerShell:

```powershell
$env:RQG_API_KEY = "replace-with-your-session-token"
rqg validate-connection `
  --endpoint https://rag.example.com/search `
  --query "password reset" `
  --top-k 3 `
  --api-key-env RQG_API_KEY `
  --output runs\vendor-poc\external-connection.json
```

If the response uses `answer` and `data` instead of `results[].chunk_id/source/text`, the diagnostic should distinguish `schema_error` from HTTP/auth/server errors and include:

- missing expected field
- available fields such as `answer, data`
- a `response_mapping` fix hint

Do not paste real API keys, bearer tokens, or customer endpoint secrets into reports.

## 8. Replace The Local Pack With A Customer PoC

For a real PoC, copy `examples/vendor-poc-pack` and change only these assets first:

1. `documents/`: customer-approved public or sanitized policy/FAQ excerpts.
2. `cases.csv`: 3-5 S1 cases and 10-30 S2 cases.
3. `quality-pack.yml`: review owner and common failure patterns.
4. `gate.yml`: thresholds agreed for PoC success.

Keep the first version small. The goal is not to build a full SaaS dashboard; it is to prove that document changes, prompt changes, and model changes can be checked before production.

## 9. Completion Checklist

You are ready to move from PoC walkthrough to customer-specific setup when:

- `validate-pack` has no errors.
- S1/S2 warning messages are reviewed and accepted.
- `rqg gate` produces `gate-report.md`, `gate-decision.json`, and `gate-report.json`.
- The team can explain at least one S1 failure and its corrective action.
- External RAG schema validation is either passing or has a clear mapping fix.
- No secrets or customer-private data are committed to the repository.
