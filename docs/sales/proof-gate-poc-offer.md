# Proof Gate PoC提案1枚

## 提案名

Proof Gate付き RAG AI導入診断PoC / 既存RAG品質診断PoC

## 対象

- FAQ、規約、料金表、社内ルールを使った業務AIを検討している企業
- すでにRAG AIを持っているが、回答品質や変更後の劣化に不安がある企業
- 返金、解約、料金、契約条件、期限、資格条件などの誤回答を避けたい企業

## A軸: RAG未導入企業向け

Proof Gate付き RAG AI導入診断PoC

実施内容:

- 対象文書をもとに簡易RAGを構築
- 高リスク質問ケースを10〜30件作成
- 返金・解約・料金・契約条件などのS1/S2を分類
- Proof Gateで回答品質を診断
- gate report と改善ポイントを提出

PoC後の導線:

- 安全化した本格RAG構築
- Proof Gate Monitor

## B軸: 既存RAGあり企業向け

既存RAG品質診断PoC

実施内容:

- 既存RAG APIへの接続確認
- 外部RAG adapterで検索結果を正規化
- 高リスク質問ケースを10〜30件作成
- Proof Gateで現行RAGの品質を診断
- 改善ポイントと月次監視項目を提出

PoC後の導線:

- 改善支援
- Proof Gate Monitor

## 4週間の進め方

1. Week 1: 文書、リスク領域、PoC対象範囲を決定
2. Week 2: Quality Pack と高リスク質問ケースを作成
3. Week 3: gate 実行、before / after または baseline / current 比較
4. Week 4: レポート提出、改善方針、Monitor移行判断

## 成果物

- Quality Pack
- 高リスク質問ケース `cases.csv`
- `gate-report.md`
- `gate-decision.json`
- `gate-report.json`
- before / after または baseline / current 比較メモ
- 月額Monitorで継続確認すべき項目

## 価格感

初回PoCは 30万〜80万円を想定します。対象文書数、既存RAG接続の有無、ケース作成数、報告会の範囲で調整します。

## よくある質問

### 最初から安全なRAGを作ればよいのでは？

安全なRAGを作ることは前提です。ただし、FAQ・規約・料金表・プロンプト・モデル・検索設定は運用中に変わります。Proof Gate は、変更後も高リスク回答が安全かを継続確認する仕組みです。

### 既存RAGでも使えますか？

使えます。既存RAGの検索APIに接続し、返ってきた根拠と回答を Proof Gate の評価形式に正規化します。RAG本体を置き換える必要はありません。

### 顧客データはどう扱いますか？

PoC開始前に、保存場所、外部送信有無、APIキー管理、ログ保持期間を合意します。ローカルPoCでは、文書・ケース・評価ログは指定した作業ディレクトリに保存されます。
