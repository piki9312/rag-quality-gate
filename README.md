# RAG Quality Gate

RAG/Agent システム向けに、回帰検証とリリース判定を継続運用するための品質ゲート基盤です。

このリポジトリでは、以下をエンドツーエンドで実行できます。

- 文書を ingest して DocumentSnapshot を生成
- テストケースを EvalCase として管理
- eval 実行で回答品質を評価
- check 実行で GateDecision を生成
- gen-cases で初期ケースを自動生成
- impact で文書更新時の影響ケースを抽出
- CI で PR の pass/fail を自動判定

## このプロジェクトの目的

RAG は文書更新、検索条件変更、プロンプト調整で品質が変化しやすく、変更の影響が見えにくい課題があります。

本プロジェクトは次を実現します。

- 変更前後の品質を再現可能に比較する
- 重大ケースを優先して守る
- 問題発生時に、どのケースを見直すべきかを明確にする
- リリース判定を運用可能な形で自動化する

## 最小セットアップ

要件:

- Python 3.11+
- pip

インストール:

```bash
pip install -e ".[dev]"
```

CLI ヘルプ:

```bash
rqg --help
```

## 最小実行フロー

同梱の HR pack を使って最小構成を実行できます。

```bash
# 1) 文書を投入して snapshot を生成
rqg ingest packs/hr/documents/ --index-dir index

# 2) 評価を実行
rqg eval packs/hr/cases.csv --docs packs/hr/documents/ --mock --index-dir index --log-dir runs/quality

# 3) ゲート判定を実行して GateDecision を出力
rqg check --log-dir runs/quality --config .rqg.yml --output-file runs/quality/gate-report.md --decision-file runs/quality/gate-decision.json
```

主な成果物:

- index/snapshots/*.json: DocumentSnapshot
- runs/quality/*.jsonl: eval 実行ログ
- runs/quality/gate-report.md: ゲートレポート
- runs/quality/gate-decision.json: GateDecision

## 初期ケース自動生成

DocumentSnapshot からレビュー可能な EvalCase 候補を生成できます。

```bash
# 1) snapshot JSON を作成
rqg init-snapshot \
  --snapshot-id snapshot_001 \
  --doc-id hr_rules \
  --title "HR Rules" \
  --source-path packs/demo_cycle/documents/leave_policy.md \
  --content "Paid leave requests must be submitted 5 business days in advance." \
  --output artifacts/doc_snapshot.json

# 2) ケース候補を生成 (JSON + 任意でレビュー用 Markdown)
qgate gen-cases \
  --snapshot artifacts/doc_snapshot.json \
  --output artifacts/eval_cases.json \
  --review-output artifacts/eval_cases_review.md \
  --mode rule
```

- JSON 出力は常に生成されます
- review-output 指定時のみレビュー用 Markdown を生成します

## Impact Analysis (Phase 1.5)

文書更新時に、どのケースを優先見直しすべきかを抽出します。

目的:

- old/new snapshot を比較
- changed_evidence_ids を抽出
- expected_evidence を使って impacted_case_ids を特定

```bash
qgate impact \
  --old-snapshot artifacts/old_snapshot.json \
  --new-snapshot artifacts/new_snapshot.json \
  --cases artifacts/eval_cases.json \
  --output artifacts/impact_report.json \
  --review-output artifacts/impact_report_review.md
```

入力:

- --old-snapshot: 変更前 DocumentSnapshot JSON
- --new-snapshot: 変更後 DocumentSnapshot JSON
- --cases: EvalCase JSON または CSV

出力:

- impact_report.json (ImpactReport)
  - old_snapshot_id
  - new_snapshot_id
  - changed_evidence_ids
  - impacted_case_ids
  - details (case_id, matched_evidence_id, question)
  - created_at
- review-output 指定時のみレビュー用 Markdown

運用メモ (Phase 1.5 仕上げ):

- section_id は doc_id ベースで生成されます（パス変更に強くするため）
- 既存ケースに source_path ベース expected_evidence が残っていても、impact 判定では後方互換マッチを行います
- 後方互換マッチの有効期間は 2026-03-27 から 2026-06-30 までです
- 新規ケース作成時は doc_id を安定した論理IDとして運用してください

移行完了条件 (後方互換ロジック終了の目安):

- source_path ベース expected_evidence を doc_id ベースへ移行完了
- legacy 互換マッチ 0 件を継続確認

### 文書更新時の推奨運用フロー

1. 現行文書を ingest して snapshot を保存
2. ケースを生成または更新
3. 文書を更新
4. 更新後文書を ingest して snapshot を保存
5. qgate impact を実行
6. impacted cases を優先レビュー
7. rqg eval と rqg check を実行
8. 必要な修正後に pass を確認

## デモ

### fail -> fix -> pass デモ

```bash
python -m rqg.demo.fail_fix_cycle
```

### impact を含む通しデモ

```bash
python -m rqg.demo.impact_cycle
```

関連ドキュメント:

- docs/demo/fail-fix-cycle.md
- docs/demo/impact-cycle.md
- docs/adr/0001-model-boundaries.md

## Phase 1 / 1.5 実装状況

- [x] ingest 時に DocumentSnapshot を自動生成
- [x] CSV ケースを EvalCase に正規化
- [x] rqg eval 実行
- [x] rqg check で GateDecision 生成
- [x] gen-cases でケース自動生成
- [x] impact で影響ケース抽出
- [x] レビュー用 Markdown 出力
- [x] CI で PR pass/fail 判定

## プロジェクト構成

```text
src/rqg/
  serving/        # RAG パイプライン (FAISS + sentence-transformers + OpenAI)
  quality/        # 品質評価・集計・ゲート判定・impact 分析
  casegen/        # セクション抽出・質問生成・ケース生成
  domain/         # DocumentSnapshot / EvalCase / GateDecision / ImpactReport
  presentation/   # レビュー向け Markdown フォーマッタ
  demo/           # 再現可能なデモシナリオ
  cli.py          # CLI エントリポイント
packs/            # ドメイン別 Quality Pack
tests/            # pytest
```

## Quality Pack

ドメインごとに次のファイルを持ちます。

- cases.csv: テストケース
- quality-pack.yml: KPI/SLO 定義
- documents/: 対象文書

CSV 例:

```csv
case_id,name,severity,question,expected_chunks,expected_keywords,golden_answer,category,owner,min_pass_rate
QA001,有給申請期限,S1,"有給の申請期限は？","","5営業日前;申請","",就業規則,hr-team,100
```

## Gate Config (.rqg.yml)

```yaml
thresholds:
  s1_pass_rate: 100.0
  overall_pass_rate: 80.0
  retrieval_precision: 70.0
```

## 評価軸

- keyword_match: 回答に期待キーワードが含まれるか
- retrieval_hit: 正しいチャンクが検索に含まれるか
- reference_accuracy: 回答中の引用整合性

## CI 連携

```yaml
- name: RAG Quality Gate
  run: |
    rqg eval packs/hr/cases.csv --docs packs/hr/documents/ --mock
    rqg check --log-dir runs/quality --config .rqg.yml
```

## 開発コマンド

```bash
# テスト
pytest tests/ -v

# フォーマット
black src/ tests/
isort src/ tests/

# カバレッジ
pytest tests/ --cov=rqg --cov-report=term-missing
```

## ライセンス

MIT
