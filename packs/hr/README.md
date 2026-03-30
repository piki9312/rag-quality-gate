# Internal Documents Pack (HR Profile)

この pack は、社内文書を知識源とする業務支援 AI 向け品質ゲートの見本です。

原則:

- 本体は水平な品質ゲート基盤
- この pack は導入と価値説明のための縦プロファイル

## Included Files

- documents/
- cases.csv
- gate.yml
- quality-pack.yml

## Quick Start

1. ingest
   - rqg ingest packs/hr/documents --index-dir index
2. eval
   - rqg eval packs/hr/cases.csv --docs packs/hr/documents --mock --index-dir index --log-dir runs/quality
3. check
   - rqg check --log-dir runs/quality --config packs/hr/gate.yml
   - rqg check --log-dir runs/quality --config packs/hr/gate.yml --quality-pack packs/hr/quality-pack.yml
4. impact (optional)
   - rqg impact --old-snapshot <old_snapshot.json> --new-snapshot <new_snapshot.json> --cases packs/hr/cases.csv --output runs/quality/impact-report.json

## What This Pack Protects

- 期限・金額・権利など重大誤案内の防止
- 手順変更時の impacted cases 特定
- fail を review と改善アクションへ接続

## Severity Policy

- S1: 規程違反や重大影響につながる誤案内
- S2: 非重大な説明不足や補足欠落

## Weekly Review Focus

- S1 fail の有無
- impacted_case_count の急増/急減
- last_reviewed_at 基準の stale case
- owner/due 未設定 fail の有無

## Common Failure Patterns

- retrieval_miss
- stale_case_definition
- procedure_drift
- escalation_gap

詳細は quality-pack.yml を参照してください。
