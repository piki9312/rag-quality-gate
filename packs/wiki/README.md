# Internal Documents Pack (Wiki/FAQ Profile)

This pack is a Phase3 extension profile for internal knowledge-base and FAQ style assistant AI.

Principles:

- Product core remains horizontal quality-gate foundation
- This pack is a vertical profile for internal wiki and FAQ operations

## Included Files

- documents/
- cases.csv
- gate.yml
- quality-pack.yml

## Quick Start

1. ingest
   - rqg ingest packs/wiki/documents --index-dir index/wiki/current
2. eval
   - rqg eval packs/wiki/cases.csv --docs packs/wiki/documents --mock --index-dir index/wiki/current --log-dir runs/quality
3. check
   - rqg check --log-dir runs/quality --config packs/wiki/gate.yml
   - rqg check --log-dir runs/quality --config packs/wiki/gate.yml --quality-pack packs/wiki/quality-pack.yml

## Index Policy

- Use one canonical wiki index path: index/wiki/current
- Do not place index artifacts under runs/
- Move old trial indexes to index/archive/ or delete them

## What This Pack Protects

- Wrong deadline guidance for access and request operations
- Missing escalation routes for security incidents
- Procedure drift between wiki updates and expected case definitions

## Severity Policy

- S1: compliance/security/deadline critical guidance risks
- S2: non-critical explanation gaps and procedure clarity issues

## Weekly Review Focus

- S1 failures and follow-up owner assignment
- impacted_case_count trend changes
- stale cases based on last_reviewed_at
- unresolved investigate items

## Common Failure Patterns

- retrieval_miss
- stale_case_definition
- procedure_drift
- escalation_gap
