# Proof Gate Product Map

## 1. 事業定義

Proof Gate は、RAG / AIチャットボットの導入・納品・変更運用に対して、重大誤回答の有無を検査し、顧客提出用レポートまで揃えて本番判断を支援する Release Gate です。

価値は「AIを作ること」ではなく、AIを安全に変更・納品・運用できる状態にすることです。

## 2. 売るもの

- 顧客対応AI / 社内RAG / FAQ AI の高リスク回答チェック。
- S1重大事故を本番前に止めるRelease Gate。
- 納品、PoCレビュー、変更承認に使える顧客提出用レポート。
- PoC後の Build / Improve / Monitor への導線。

## 3. 今は売らないもの

- 汎用RAGフレームワーク。
- フル機能のLLMOps基盤。
- SaaS tenant workspace、認証、課金、アクセス制御。
- AIの完全な安全保証。
- S1ケースの完全自動生成・自動active化。

## 4. 主な利用者

- RAG納品ベンダー。
- AI導入支援会社。
- FAQ、規約、料金、HR、労務、社内規程、顧客サポートAIを扱う中小チーム。
- 文書、プロンプト、モデル、検索設定の変更前後で証跡が必要なチーム。

## 5. 提供メニュー

| メニュー | 目的 | 成果 |
|---|---|---|
| Build | Proof Gate付きで小さくRAG PoCを作る | 導入判断証跡と本格RAGの次スコープ |
| Improve | 既存RAG / chatbotを診断・改善する | リスク検出、修正、before/after証跡 |
| Monitor | 変更後に高リスクケースを再実行する | 継続的なRelease Gateと月次品質証跡 |

## 6. 製品面

現在の実装はこの面を中心にする:

- CLI。
- Quality Pack。
- `cases.csv`。
- 外部RAG adapter境界。
- `GateDecision`。
- Markdown / JSON report。
- customer-safe report mode / artifact。
- 調査用の最小read-only dashboard。

## 7. Customer Decision Package

近い将来の顧客提出パッケージは以下を標準にする:

- 顧客提出版gate report。
- Before / after one-pager。
- 顧客データ取扱い説明1枚。
- PoC後の選択肢。
- machine-readableな `gate-decision.json`。
- 運用詳細は別紙。最初に見せるものではない。

## 8. S1 / S2 の役割

| 種別 | 役割 | 作り方 | リリース判断での意味 |
|---|---|---|---|
| S1 | 重大事故を止めるSafety Gate | 業務リスク、文書根拠、expected answer、block reason、人間承認 | 1件失敗でBLOCKになり得る |
| S2 | 網羅・検索・説明品質を見るQuality Gate | 文書セクション、生成候補、軽いレビュー | REVIEW / 改善対象になりやすい |

S1は生成候補から直接active化しない。S2は `gen-cases` を候補生成として使ってよい。

## 9. Source Of Truth

- 最終テストケース: `cases.csv`。
- 最終機械判定: `gate-decision.json`。
- full report bundle: `gate-report.json`。
- 顧客向け説明: customer summary / customer gate report。
- failure pattern: ケース作成の補助。runtime正本ではない。
- generated review file: 一時レビューartifact。正本ではない。

## 10. 現在の実装との対応

repoにはすでに以下の基盤がある:

- CLIとQuality Pack flow。
- S1/S2 severityとgate decision。
- 外部RAG adapter境界。
- case validation / merge helper。
- CI-safe report / artifact hardening。
- 顧客向けsales / report template。
- 内部S1 case authoring demo。

大きな差分は、部品は揃い始めているが、`gateを実行する` から `顧客に本番判断パッケージを提出する` までの導線がまだ分散していることです。

## 11. 次の優先度

P0はruntime拡張ではなく、情報設計と成果物整理です。

1. Product Mapを製品正本にする。
2. Current Working Setで今見る資料を絞る。
3. Customer Decision Packageを標準化する。
4. `cases.csv` を壊さずにS1 case authoringを標準化する。
5. 古いPhase資料はarchiveまたはhistorical扱いにする。

## 12. 後回し

- asset registry。
- usage log / `seen_count`。
- common/customer/demo pack registry。
- tenant DB。
- SaaS dashboard。
- S1自動active化。
- CLI、`GateDecision`、`gate-report.json`、`cases.csv` の破壊的変更。
