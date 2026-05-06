# Business Context

## Proof Gate の目的

Proof Gate は、顧客対応AI・社内RAG・FAQ RAGを本番に出す前に、重大誤回答、文書変更、プロンプト変更、モデル変更による品質劣化を検査し、**リリース可否を判定する AI 品質保証 / Release Gate** です。

## 事業の立ち位置

- 主役は Release Decision と品質保証フロー
- 主な成果物は CLI、Quality Pack、外部RAG adapter、machine-readable / human-readable reports
- 本番 RAG 構築は主力商品ではなく、必要に応じた実装支援

## なぜ初期は Proof Gate 付き PoC を入口にするか

- Proof Gate 単体では、初期顧客に ROI を伝えにくい
- 顧客はまず「自社文書で AI が危険回答しないか」を見たい
- そのため、必要最小限の RAG 実装支援や既存RAG接続支援を入口にしつつ、価値の中心は Gate 判定に置く
- PoC のゴールは「RAG を作ること」ではなく「安全に出せるかを判断できる状態を作ること」

## 受託 PoC から共通資産を作る戦略

- 各案件を単発受託で終わらせない
- 顧客文書そのものではなく、抽象化された失敗パターン、ケース設計、Gate Policy、レポート形式、改善提案を蓄積する
- 抽出した共通資産を Quality Pack と周辺テンプレートに戻し、将来的なプロダクト化へつなげる
- repeatable な部分だけを repo に戻し、個社事情は案件ごとの保管先へ分離する

## 競争環境の認識

- RAG 構築そのものはコモディティ化しやすい
- 汎用品質評価ツールも差別化が難しくなりやすい
- 差別化の中心は以下に置く
  - 業務別 failure patterns
  - Release Decision の判定ルール
  - Gate Policy
  - 監査証跡
  - Quality Pack

## この repo で重視する判断

- RAG 構築の広がりより、品質ゲートの再現性を優先する
- 汎用 LLMOps ではなく、顧客AIの出荷判定基盤として判断する
- SaaS、認証、課金、重いUIは、反復的な顧客証拠が揃うまで後回しにする
