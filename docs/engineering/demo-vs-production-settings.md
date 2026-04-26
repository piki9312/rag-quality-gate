# Demo vs Production Settings

This guide defines which Proof Gate settings are appropriate for client demos,
customer PoCs, pre-production gates, and CI blocking. The goal is to keep demos
easy to run while avoiding production-quality claims from demo-only shortcuts.

## Policy Summary

| Mode | Purpose | Acceptable settings | Avoid | Recommended command |
|---|---|---|---|---|
| Client demo | Show the product flow quickly with no secrets or customer systems. | `--mock`, `EMB_MODEL=local-fallback-hash-embedding`, isolated `--index-dir` and `--log-dir`, sample packs such as `examples/demo-client-pack` or `examples/vendor-poc-pack`. | Claiming the result proves production answer quality, reusing a shared index, hiding that mock evaluation was used. | `rqg gate --pack examples/demo-client-pack --mock --reset-log-dir --index-dir indexes/demo-client-pack --log-dir logs/demo-client-pack` |
| Customer PoC | Validate the customer's actual RAG/FAQ behavior against a customer-specific Quality Pack. | External RAG adapter or a real embedding path, customer-specific cases copied from `templates/customer-rqg-template`, isolated run directories, `rqg doctor` before onboarding. | Using `--mock` for customer quality claims, relying on implicit local fallback, mixing demo and customer indexes. | `rqg validate-pack --pack path/to/customer-pack` then `rqg gate --pack path/to/customer-pack --rag-endpoint https://example.invalid/search --rag-api-key-env RAG_API_KEY --index-dir indexes/customer-poc --log-dir logs/customer-poc` |
| Pre-production gate | Decide whether a release can proceed before production traffic. | Real RAG path, explicit judge and embedding configuration, S1 pass rate at `100%`, strict review of `gate-report.json` and `gate-report.md`. | Silent judge fallback, silent embedding fallback, lower S1 thresholds for production-blocking cases, demo packs. | `rqg gate --pack path/to/production-pack --rag-endpoint https://example.invalid/search --rag-api-key-env RAG_API_KEY --s1-threshold 100 --index-dir indexes/preprod --log-dir logs/preprod` |
| CI blocking | Fail a PR or deployment when the quality gate blocks release. | Isolated CI `--index-dir` and `--log-dir`, `--warn-exit-code 1`, no real API keys unless the job is explicitly configured for secure customer or staging systems. | Shared indexes across packs, external calls without secret scoping, treating mock CI as production proof. | `rqg gate --pack path/to/pack --mock --warn-exit-code 1 --reset-log-dir --index-dir indexes/ci-pack --log-dir logs/ci-pack` |

## Recommended Commands

Run `rqg doctor` before customer onboarding or CI setup:

```bash
rqg doctor
```

Use the lightweight install for pack validation, existing report review, and
environment checks:

```bash
pip install -e .
rqg validate-pack --pack examples/demo-client-pack
```

Use the embedding extra for local document demos that build a FAISS index:

```bash
pip install -e ".[embedding]"
export EMB_MODEL=local-fallback-hash-embedding
rqg gate --pack examples/demo-client-pack --mock --reset-log-dir --index-dir indexes/demo-client-pack --log-dir logs/demo-client-pack
```

Use the external extra when testing an external RAG adapter:

```bash
pip install -e ".[external]"
rqg validate-connection --endpoint https://example.invalid/search --query "benefits policy" --api-key-env RAG_API_KEY
```

For CI blocking, keep the output directories isolated and make warning outcomes
fail the job when that is the desired release policy:

```bash
rqg gate --pack path/to/pack --mock --warn-exit-code 1 --reset-log-dir --index-dir indexes/ci-pack --log-dir logs/ci-pack
```

## What Not To Claim From Demo Results

Do not claim that a `--mock` result proves production answer quality. `--mock`
is for demos and local validation of the Proof Gate workflow.

Do not claim that `local-fallback-hash-embedding` represents the customer's real
retrieval quality. It is useful for reproducible demos and avoiding first-run
model downloads, but it should always be explicit.

Do not claim that a sample pack covers a customer's risk surface. Use
`templates/customer-rqg-template` to start a customer-specific pack, then replace
documents, cases, severity labels, expected answers, keywords, and evidence.

Do not claim a PASS result is production-ready if the run used silent judge or
embedding fallback. Pre-production gates should avoid silent fallback and review
the reliability fields in the reports.

## Interpreting PASS

A demo PASS means the sample workflow completed and the sample pack met its
configured thresholds under demo settings. It is suitable for showing the flow:
validate the pack, run the gate, read the Markdown report, and inspect
`gate-report.json`.

A production PASS means the customer's own Quality Pack passed against the real
RAG path, with production-blocking S1 cases meeting a `100%` pass rate. It also
means fallback, reliability, and report artifacts were reviewed under the
release policy for that customer.

## Related Entry Points

- `examples/demo-client-pack`: client-facing PASS demo.
- `examples/vendor-poc-pack`: intentional FAIL demo for production blocking and next actions.
- `examples/vendor-poc-pack-pass`: remediation scenario that turns the FAIL demo into PASS.
- `templates/customer-rqg-template`: starting point for a customer-specific PoC or production gate repository.
