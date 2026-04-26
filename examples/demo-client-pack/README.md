# Demo Client Quality Pack

This pack is a client-facing demo for RAG Quality Gate.

It represents an internal support RAG system for a company and keeps the content small enough to explain in a walkthrough. The policy and cases cover HR, IT support, security escalation, remote work, and payroll guardrails.

## Files

- `documents/internal_support_policy.md`: source policy used by the local RAG demo
- `cases.csv`: five active cases in the formal 16-column schema
- `gate.yml`: lightweight gate thresholds for the walkthrough
- `quality-pack.yml`: pack metadata and next-action hints

## Run validate-pack

```bash
rqg validate-pack --pack examples/demo-client-pack
```

Expected result: 0 errors and 0 warnings.

## Run a reproducible demo gate

Use a dedicated index directory for this pack so retrieval only sees this pack's documents. Starting from a clean isolated index avoids false failures when a shared default index already points to another corpus.

Bash:

```bash
rm -rf indexes/demo-client-pack
rm -rf logs/demo-client-pack
rqg gate --pack examples/demo-client-pack \
	--mock \
	--index-dir indexes/demo-client-pack \
	--reset-log-dir \
	--log-dir logs/demo-client-pack
```

PowerShell:

```powershell
Remove-Item -Recurse -Force indexes\demo-client-pack -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force logs\demo-client-pack -ErrorAction SilentlyContinue
rqg gate --pack examples\demo-client-pack `
	--mock `
	--index-dir indexes\demo-client-pack `
	--reset-log-dir `
	--log-dir logs\demo-client-pack
```

Expected result: PASS.

If `indexes/demo-client-pack` does not exist yet, `rqg gate` will build the local index from `documents/` before running the checks.

## Inspect the report

```bash
cat logs/demo-client-pack/gate-report.md
python -m json.tool logs/demo-client-pack/gate-report.json
```

The Markdown report should include an Executive Summary with:

`Recommended. This pack meets the configured gate thresholds.`

## What PASS Means

PASS means the pack met the configured S1 and overall thresholds, the expected evidence was retrieved, and the mock evaluation produced answers that satisfied the case expectations.

## How This Maps To A Real Client PoC

For a real client PoC, replace the sample policy with the client's internal support documents, update the cases to match the client's escalation and compliance rules, and connect the same gate outputs to the client's review and reporting flow.