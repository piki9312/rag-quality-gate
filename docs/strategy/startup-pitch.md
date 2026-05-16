# Startup Pitch Narrative

## Purpose

This document turns the current repository strategy into a startup pitch storyline.
The core message stays fixed:

> Proof Gate is not a company that replaces RAG/FAQ AI itself. It is a business that provides a quality gate for deciding whether customer-facing RAG/FAQ AI is safe enough to release.

## 1. Title

- **Proof Gate: 顧客向けRAG/FAQ AIの本番判断を支える品質ゲート**
- 補助見出し: **重大誤回答を公開前に止め、変更後も継続監視する**

このタイトルで最初に示すべきことは、Proof Gate が AI をより賢くする主体ではなく、AI を安全に更新・運用できる状態を作る主体だという定義です。

## 2. Problem

課題は、AI 利用側の顕在課題と、その課題に向き合う導入会社/ベンダー側の運用課題に分けて示します。

### 顕在化している課題

- FAQ、規約、料金表、社内ルールが変わった後も、AI が古い条件で自然に答えてしまう
- 返金、解約、料金、契約条件、期限、資格条件などの誤回答が事故、炎上、説明責任につながる
- PoC は動いても、本番 Go の判断材料が弱い

### その課題に取り組む企業側の課題

- ベンダーや導入会社は、品質説明が属人的になりやすい
- 納品後の誤回答責任が重い
- FAQ や規約変更後の再確認が人手運用で重い
- 単発売上で終わりやすく、保守メニュー化しにくい

### このスライドで言い切ること

Proof Gate が捉える本質課題は、AI の性能不足そのものよりも、**本番判断の不在**と**変更後品質運用の不在**です。

## 3. Solution

Proof Gate は、既存または新規の RAG/FAQ AI の**外側**に品質ゲートを置きます。

- 高リスク質問を `cases.csv` として管理し、S1/S2 の重大度で整理する
- `rqg gate` により `PASS` / `BLOCK` / `NEEDS_HUMAN_REVIEW` を出す
- Markdown/JSON レポートで顧客説明用と内部運用用の成果物を分けて残す
- 文書変更、prompt 変更、model 変更、retrieval 変更の前後比較を行う

### 強調すべきこと

- RAG を置き換えない
- 既存 RAG に後付けできる
- 単発診断で終わらず Monitor に接続できる

## 4. Core Technology

ここで語るべきコアは、生成 AI の性能向上技術ではなく、品質ガバナンス技術です。

- 高リスクケースを形式知化する **Quality Pack**
- S1/S2 で本番停止レベルを扱う **重大度設計**
- 外部 RAG 差分を吸収する **adapter 境界**
- 人向け/機械向けの両方に出せる **説明可能なレポート設計**
- 変更前後比較を前提にした **回帰検査運用**

言い換えると、Proof Gate のコア技術は「より賢く答えさせる技術」ではなく、**どの条件なら出してよいかを再現可能に判定する技術**です。

## 5. Market Potential

市場は「RAG 市場」や「汎用 LLMOps 市場」ではなく、**高リスクな RAG/FAQ AI を本番判断・継続運用したい市場**として定義します。

### TAM

- 顧客対応 AI、FAQ AI、社内文書検索 RAG、社内規程/HR/労務/契約系 AI を運用する企業全体
- 特に、誤回答が信頼低下や説明責任につながる領域

### SAM

- 日本の RAG 導入会社
- AI/DX 支援会社
- 既存 AI チャットボット導入企業
- 高リスク文書を扱う FAQ / 社内文書系ユースケース

### SOM

- 初期は 0→10 社導入を狙う
- 入口商品は PoC / 本番前診断
- 継続商品は変更時チェック / 月次 Monitor
- 価格仮説は、初回 PoC 20万〜80万円、継続 Monitor 月額5万〜20万円をベースに考える

### Pitch での注意点

- この repository から強く言えるのは、市場の切り方、単価仮説、SOM 仮説です
- TAM/SAM の絶対額は外部データで補強する前提で扱います
- ただし資料では、**汎用 LLMOps 市場ではなく、本番判断と変更時 QA の市場である**ことを先に定義します

## 6. Business Model Overview

Proof Gate は、サービス支援型プロダクトとして売ります。

1. **Build**: Proof Gate 付き RAG 構築 PoC
2. **Improve**: 既存 RAG 診断・改善 PoC
3. **Monitor**: 変更時・月次の継続品質監視

このスライドで伝えるべき一言は、**単発の診断売上ではなく、本番判断 → 改善 → 継続監視の運用売上を作るモデル**だということです。

## 7. Competition

競合は「RAG を構築する会社」ではなく、**本番判断をどう作るか、変更後 QA をどう回すかを解いている代替手段すべて**です。

### 競合の置き方

1. **手作業・スプレッドシート・属人的レビュー**
   - 実運用では最も強い競合
2. **汎用 RAG 評価 / LLMOps ツール**
   - 指標は出せるが、顧客提出用レポートや Go/No-Go 判断に直結しにくい
3. **RAG 構築ベンダーの内製 QA**
   - 案件ごとで再現性、標準化、第三者性が弱い
4. **チャットボット/RAG 製品そのものの標準機能**
   - 構築はできても、変更後の高リスク回帰検査が弱いことがある

### 自社優位として主張すべきこと

- 高リスク質問に絞った品質ゲート
- 既存 RAG に後付け可能
- 顧客提出用レポートまで含む
- 変更時チェックを月額運用に変えられる
- 失敗パターン、S1/S2 分類、業界別 Gate Policy を案件横断で資産化できる

### 正直に言うべきこと

参入障壁はまだ強くありません。したがって優位性は機能量ではなく、**失敗パターン資産・レポート型・運用導線の蓄積**に置くべきです。

## 8. Revenue Ladder

この項目では、売上の階段を明示します。

### 入口商品

- 本番前リスク診断
- 納品品質レポート作成 PoC
- FAQ / 規約変更後チェック

### 継続商品

- Monthly Quality Operation / Proof Gate Monitor

### 拡張商品

- 既存 RAG 改善支援
- Proof Gate 付き RAG 構築支援
- ベンダー向け保守メニュー組み込み支援

このスライドの結論は、**初回 PoC で終わらず、変更管理と品質レビューを継続収益化できる**こと、そして**ベンダー経由だと 1 社から複数案件へ横展開できる**ことです。

## 9. Roadmap

- まずは 0→10 導入で CLI / Quality Pack / adapter / report の型を磨く
- 実案件から失敗パターンを資産化する
- 業界別 Gate Policy を整備する
- レポートテンプレートを磨く
- 変更時レビューを標準運用にする
- その後に必要なら UI や SaaS 化を検討する

### Pitch での言い方

- 先に SaaS を作るのではなく、先に品質運用を成立させる
- 将来は第三者検査に近い立場まで進化できる

## Storyline To Keep Through The Deck

1. RAG/FAQ AI の本当の問題は、精度の低さだけでなく、本番判断と変更後運用が弱いこと
2. Proof Gate は、高リスク回答を止める品質ゲートとしてその空白を埋める
3. 既存 RAG にも後付けでき、顧客提出用レポートまで出せる
4. 単発診断で終わらず、変更時チェックと月次 Monitor で継続事業化できる
5. 競争優位は RAG 構築力ではなく、失敗パターン・重大度設計・レポート運用資産の蓄積にある

## Highest-Priority Slides

特に作り込むべきスライドは次の 3 枚です。

### 課題

- 顧客の課題: 誤回答事故が怖い、本番 Go 判断ができない
- ベンダーの課題: 品質説明が属人的、納品後責任が重い、保守商品化しにくい

### 市場ポテンシャル

- 市場を「RAG」ではなく「高リスク AI の本番判断 / 変更時 QA 市場」と定義する
- SOM は価格仮説付きで具体化する
- TAM/SAM は外部数字で補強する

### 競合比較

- 比較軸は「RAG を作れるか」ではなく「本番判断を作れるか / 変更時に回せるか / 顧客に説明できるか」で置く
- 手作業、汎用評価ツール、内製 QA も競合に入れる

## Suggested Next Step

If this pitch is turned into slides, keep it within 10 slides and preserve the section order above so the story moves from problem framing to quality-gate differentiation, then to market, revenue, and roadmap.
