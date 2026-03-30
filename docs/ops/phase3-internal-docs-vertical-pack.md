# Phase3 Internal Documents Vertical Pack Guide

## 0. Scope and Principle

このドキュメントは、Phase3 で「社内文書を知識源とする業務支援 AI 向け」の縦パックを整備するための実装基準です。

固定原則:

- 中身は水平、売り方は縦
- 本体は品質ゲート基盤（ingest / eval / check / impact / review / CI）
- 縦パックは導入と価値訴求の入口
- AI を賢くすることではなく、安全な更新と運用を目的にする

---

## 1. 社内文書向け縦パックの最小構成

### 目的

社内文書ユースケースで最短導入できる最小パッケージを固定する。

### なぜ必要か

導入初期に構成が過多だと、セットアップ失敗と運用未定着が増えるため。

### 最小実装

必須ファイル:

- documents/（規程、FAQ、手順書、ナレッジ記事）
- cases.csv（代表ケース + severity + owner + last_reviewed_at）
- gate.yml（実行ゲート閾値）
- quality-pack.yml（業務向け品質方針、KPI/SLO、ROI 仮説）
- README.md（導入手順、レビュー手順、よくある失敗）

### 共通基盤への影響

共通 CLI やドメインモデルの変更は不要。

### 縦パック側の責務

文書セット、ケース設計、閾値方針、運用手順を明示する。

### 完了条件

新規利用者が 60 分以内に ingest -> eval -> check -> impact -> review を再現できる。

### 反映先

- README.md
- docs/README.md
- templates/sample_pack/README.md
- templates/sample_pack/cases.csv
- templates/sample_pack/gate.yml
- templates/sample_pack/quality-pack.yml
- packs/hr/cases.csv
- packs/hr/quality-pack.yml

---

## 2. HR 特化か汎用社内文書か

### 目的

市場説明の分かりやすさと将来展開性を両立する。

### なぜ必要か

HR 専用に固定すると FAQ/Wiki への拡張時に再設計コストが高くなるため。

### 最小実装

- 製品メッセージは「汎用的な社内文書向け」
- 実例は HR を第一見本として提供

### 共通基盤への影響

なし。

### 縦パック側の責務

カテゴリ語彙を「社内文書一般」で再利用可能な粒度に保つ。

### 完了条件

README 冒頭と pack README で「汎用社内文書 + HR 見本」の二層構造が伝わる。

### 反映先

- README.md
- templates/sample_pack/README.md
- packs/hr/quality-pack.yml

---

## 3. cases.csv の代表ケース設計

### 目的

影響分析と重大ケース保護を同時に成立させる。

### なぜ必要か

ケースが偏ると impact の妥当性と release 判定の説明可能性が下がるため。

### 最小実装

代表ケース類型を固定:

- 規程事実（例: 対象者、適用条件）
- 手順（例: 申請フロー、提出先）
- 期限・金額（例: 締め日、上限）
- 例外条件（例: 特例、免除、除外）
- エスカレーション（例: 問い合わせ先、承認責任者）

S1 は各重要領域へ最低 1 ケース配置する。

### 共通基盤への影響

なし。既存 CSV 形式を維持。

### 縦パック側の責務

expected_chunks と expected_keywords の保守、owner と last_reviewed_at の更新。

### 完了条件

文書差分を 3 種（規程変更、期限変更、手順変更）で流した際に impacted cases が想定と一致する。

### 反映先

- templates/sample_pack/cases.csv
- packs/hr/cases.csv
- docs/demo/impact-cycle.md

---

## 4. severity の切り方

### 目的

pass/warn/fail の判断基準を技術者以外にも説明可能にする。

### なぜ必要か

severity 基準が曖昧だと、同じ結果でも判断が揺れるため。

### 最小実装

- S1: 法令・規程違反、金銭/権利への重大影響、期限誤案内
- S2: 補足情報不足、説明粒度不足、軽微な利便性低下

推奨 min_pass_rate:

- S1: 100
- S2: 80-90

### 共通基盤への影響

なし。

### 縦パック側の責務

各ケースに severity を付与し、境界が曖昧な項目は notes で根拠を残す。

### 完了条件

週次レビューで S1 の定義がチーム内で一致し、運用時に再解釈が発生しない。

### 反映先

- packs/hr/cases.csv
- templates/sample_pack/cases.csv
- docs/ops/phase2-5-case-quality-weekly-review.md

---

## 5. quality-pack.yml の初期値

### 目的

業務サイドへ「何を守る品質か」を明示する。

### なぜ必要か

gate.yml だけでは業務 KPI/SLO とつながりにくいため。

### 最小実装

quality-pack.yml に次を記載:

- pack metadata
- severity policy
- KPI（例: keyword_match_rate, retrieval_hit_rate, reference_accuracy）
- SLO（例: s1_pass_rate, overall_pass_rate, regression_tolerance）
- weekly review focus
- common failure patterns

### 共通基盤への影響

なし。quality-pack.yml は運用契約ドキュメントとして扱う。

### 縦パック側の責務

業務文脈に合わせた KPI/SLO 更新と reviewer 合意の記録。

### 完了条件

非技術者に「守る対象」「目標水準」「逸脱時のアクション」を 5 分で説明できる。

### 反映先

- templates/sample_pack/quality-pack.yml
- packs/hr/quality-pack.yml
- templates/sample_pack/README.md

---

## 6. review / weekly ops で何を見るか

### 目的

fail を改善アクションへ確実に接続する。

### なぜ必要か

評価結果の確認だけでは運用改善につながらないため。

### 最小実装

週次レビュー固定観点:

- S1 fail の有無
- failure_action_coverage_rate
- overdue_exceptions_count
- stale cases（last_reviewed_at > 30 日）
- impacted_case_count の急増/急減
- 未クローズ investigate の滞留

### 共通基盤への影響

既存 weekly workflow を利用し、レビュー項目を明確化するのみ。

### 縦パック側の責務

週次 issue 上でアクション owner / due date / close 条件を必ず残す。

### 完了条件

毎週の review issue で改善アクションが 1 件以上起票される。

### 反映先

- docs/ops/phase2-5-case-quality-weekly-review.md
- docs/ops/phase2-5-weekly-metrics-register.md
- .github/workflows/phase2-5-weekly-review-issue.yml
- .github/workflows/phase2-5-weekly-metrics.yml

---

## 7. README 冒頭での価値伝達

### 目的

初見 30 秒で製品価値を理解できる状態にする。

### なぜ必要か

導入判断の多くは README 冒頭で行われるため。

### 最小実装

冒頭メッセージを次の順で固定:

1. 何を守るか（安全な更新と運用）
2. どこで壊れるか（文書更新、プロンプト変更、retrieval 変更）
3. どう守るか（impact + eval/check + release gate）

### 共通基盤への影響

なし。

### 縦パック側の責務

社内文書ユースケース例と守るべき重大ケースを簡潔に示す。

### 完了条件

README だけで「中身は水平、売り方は縦」が理解される。

### 反映先

- README.md
- docs/demo/onboarding-quickstart.md
- docs/demo/impact-cycle.md
- docs/demo/fail-fix-cycle.md

---

## 8. Pack と基盤の責務分離

### 目的

縦パック追加時に共通層へドメイン依存が混入することを防ぐ。

### なぜ必要か

共通層が縦化すると将来の再利用性が下がるため。

### 最小実装

責務境界を固定:

- 共通基盤: CLI、domain、loader、eval/check、impact、CI
- 縦パック: documents、cases、gate/quality 設定、運用ルール

### 共通基盤への影響

なし（原則明文化）。

### 縦パック側の責務

追加要求はまず pack 側で吸収し、2 つ以上の縦パックで共通化需要が確認されてから基盤へ昇格する。

### 完了条件

PR レビュー時に「共通基盤へ入れる理由」が明示される。

### 反映先

- docs/adr/0001-model-boundaries.md
- docs/adr/0002-product-charter-and-development-priorities.md
- docs/ops/phase3-internal-docs-vertical-pack.md

---

## 9. FAQ / Wiki への将来展開を邪魔しない構成

### 目的

社内文書から近縁媒体へ自然に横展開する。

### なぜ必要か

Phase3 で固定した構成が次の市場ノードの実装コストを決めるため。

### 最小実装

- 変化しやすい要素は pack 側で管理（カテゴリ語彙、ケース例、週次観点）
- 変化しにくい要素は共通層で維持（CLI 引数、ドメインモデル、gate 判定）

### 共通基盤への影響

なし。

### 縦パック側の責務

FAQ/Wiki 向け派生 pack を作る際は、まず sample_pack から派生し、共通 API への要求変更を最小化する。

### 完了条件

FAQ/Wiki pack を追加する際の変更が packs/ と docs/ 中心で完結する。

### 反映先

- templates/sample_pack/
- packs/hr/
- docs/README.md

---

## 10. Definition of Done (Phase3 First Iteration)

- README で価値訴求が明確
- sample_pack が最小構成を満たす
- hr pack が見本製品として説明可能
- 週次 review 観点が固定される
- 責務分離原則が docs で参照可能
