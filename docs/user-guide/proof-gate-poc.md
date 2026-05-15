# Proof Gate PoCガイド

このガイドは、日本企業向けに Proof Gate の PoC を短時間で説明・再現するための入口です。

Proof Gate は、RAG AI を「作るだけ」で終わらせず、返金・解約・料金・契約条件などの高リスク回答をリリース前に確認し、重大誤回答リスクを可視化して、公開判断を支援する品質保証基盤です。

## PoCで見せる価値

- 自社FAQ・規約・料金表を使った RAG AI の体験
- 高リスク質問に対する回答品質の診断
- FAQ・規約変更後にAIが古い条件で誤回答する変更事故の検知
- S1重大失敗を `policy_status=block` として本番反映前に止めること
- 修正後に同じケースで再Gateし、改善を確認できること
- 月額Monitorで継続監視する合理性

## Build / Improve / Monitor

### Build: RAG未導入企業向け

顧客のFAQ・規約・料金表をもとに簡易RAGを構築し、高リスク質問ケースを作って回答品質を診断します。PoC後は、本格RAG構築と Proof Gate Monitor に進みます。

### Improve: 既存RAGあり企業向け

顧客またはベンダーが持つ既存RAG APIに Proof Gate を接続し、同じ高リスク質問セットで回答品質を診断します。PoC後は、改善支援と Proof Gate Monitor に進みます。

### Monitor: 継続品質監視

FAQ・規約・料金表・プロンプト・モデル変更後に高リスク質問を再実行し、重大誤回答リスクと品質劣化を継続確認します。
## 最短営業デモ: FAQ変更事故 before / after

```powershell
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python scripts\create_customer_support_faq_change_sales_demo.py
```

生成される主なファイル:

- `demos/customer_support_faq_change/reports/before_stale_v1/gate-report.md`
- `demos/customer_support_faq_change/reports/after_v2_reference/gate-report.md`
- `demos/customer_support_faq_change/before_after_onepager.md`
- `demos/customer_support_faq_change/demo_summary.json`

見る順番:

1. before report の `1. 本番反映判定` を見せ、`NG` / `BLOCK` を説明する。
2. before report の `5. S1重大失敗一覧` を見せ、古いFAQ条件で危険な回答が出ることを説明する。
3. after report の `1. 本番反映判定` を見せ、`OK` / `PASS` を説明する。
4. after report の `4. 実行結果サマリ` を見せ、S1 pass rate と overall pass rate の改善、S1重大失敗の解消を説明する。
5. `before_after_onepager.md` で、改善内容と次の推奨を共有する。
6. Monitor では、変更後も同じ高リスク質問セットを継続評価することを説明する。

> evaluator fallback を `NEEDS_HUMAN_REVIEW` として見せたい場合は、固定ダッシュボードデモの review シナリオを使います。FAQ変更事故デモのコミット済み after artifact は `PASS` です。

## ダッシュボードデモ

固定artifactを使う場合:

```powershell
.\.venv\Scripts\python scripts\create_customer_support_demo_artifacts.py
.\.venv\Scripts\python -m rqg.cli serve-dashboard --workspace-dir . --runs-dir packs\customer_support_pack\reports\demo_runs --port 8012
```

開く画面:

- `/packs`
- `/runs`
- `/runs/csp-pass-202604`
- `/runs/csp-block-refund-202604`
- `/runs/csp-needs-review-fallback-202604`
- `/cases/failures`
- `/reports/monthly`

## 通常CLIで実行する場合

```powershell
.\.venv\Scripts\python -m rqg.cli gate --pack packs\customer_support_pack --mock --log-dir runs\customer_support_pack --reset-log-dir
.\.venv\Scripts\python -m rqg.cli report-monthly --log-dir runs\customer_support_pack --month 2026-04
```

## 顧客に準備してもらうもの

- FAQ、規約、料金表、サポート手順などの対象文書
- 誤回答時に顧客影響が大きい質問領域
- 既存RAGがある場合は検索APIの接続情報とレスポンス例
- PoCで判定したい変更イベント
- 成果物の提出先とレビュー担当者

## PoC成果物

- Quality Pack
- 高リスク質問ケース `cases.csv`
- `gate-report.md`
- `gate-decision.json`
- `gate-report.json`
- before / after 比較メモ
- 月額Monitorに引き継ぐ確認項目

## 簡易RAG構築と本格RAG構築の違い

- 簡易RAG構築: PoC検証用。対象文書を限定し、重大誤回答リスクの検査と Gate 判定を重視する。
- 本格RAG構築: 実運用用。認証、権限、UI、ログ、監視、SLA、運用フロー、継続評価まで含める。
- PoCの簡易RAGは本番RAGの完成版ではありません。導入判断と改善優先度を明らかにするための検証用スコープです。

## Runtime severity note

PoC case selection may use `S3` as a classification band in `case_set_summary.json`, but `S3` is not a new runtime severity. The runtime CSV contract remains compatible with the existing formal schema: S3-selected rows are emitted in `cases.csv` as `severity=S2`, while the original selection band is preserved in `notes` as `poc_band:S3`. This is why `case_set_summary.json` includes both `severity_mix` and `runtime_severity_mix`.

## 顧客データの扱い

ローカルPoCでは、文書・ケース・評価ログは指定した作業ディレクトリに保存されます。外部RAG診断では、Proof Gate は外部RAG APIの検索結果と回答を評価し、顧客RAG本体を置き換えません。

実案件では、保存場所、外部送信有無、APIキー管理、ログ保持期間をPoC開始前に合意してください。詳細は [顧客データ取扱い説明](../sales/customer_data_handling_onepager.md) を参照してください。
