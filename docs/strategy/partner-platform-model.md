# Proof Gate Partner Platform Model

## Purpose

この文書は、Proof Gate を RAG / FAQ AI 導入ベンダー向けの **Partner Platform（パートナー提供方式）** として整理するための設計文書です。

Proof Gate は、納品前品質診断、納品後変更レビュー、月次品質レビューをベンダーの納品・保守フローへ組み込めるようにします。ただし、ベンダーに「使える状態」は渡しても、Proof Gate の評価資産・中核資産まで渡し切って内製できる状態にはしません。

## 1. 基本コンセプト

Proof Gate Partner Platform とは、RAG / FAQ AI を導入するベンダーが、自社の delivery flow に以下を組み込むための提供方式です。

- 納品前 AI 回答品質診断
- 納品後変更事故防止レビュー
- 月次 AI 回答品質レビュー
- 顧客提出 safe report（顧客提出 safe レポート）
- delivery review dashboard（ベンダー社内レビュー）

Proof Gate 側は、test pack、failure pattern、判定基準、safe/full boundary、customer-facing report の設計原則を保持します。ベンダー側は、顧客接点、RAG 構築、Proof Gate 実行、修正、顧客提出、月次運用を担います。

この方式では、Proof Gate は単なるツール販売ではなく、**Partner Kit を渡してベンダーの商品化を支援しつつ、中核資産は Proof Gate 側に保持する** ことを前提にします。

## 2. 役割分担

| 領域 | Proof Gate側 | ベンダー側 |
|---|---|---|
| 顧客接点 | 原則持たない | 持つ |
| 顧客文書管理 | 原則持たない | 持つ |
| full/raw evidence | 原則持たない | ベンダー / 顧客環境で管理 |
| 評価基準 | 保持・更新 | 利用 |
| test pack | 保持・提供 | 選択・実行 |
| failure pattern | 保持・更新 | 結果を確認 |
| delivery review dashboard | 提供 | 社内レビューに利用 |
| customer-facing report | 生成機能を提供 | 確認して提出 |
| 顧客説明 | 支援資料を提供 | 実施 |
| 月次改善 | safe 集計から支援 | 運用実績を共有 |

補足:

- dashboard は顧客提出物ではなく、ベンダー社内レビュー用です。
- customer-facing report は safe な顧客提出物です。
- full/private detail は local、private runner、customer-controlled environment に留めます。
- Proof Gate 側は原則 safe 集計のみを受け取ります。

## 3. 渡すもの / 見せるもの / 渡さないもの

### 3.1 渡すもの

Partner Kit でベンダーへ渡すもの:

- Proof Gate 実行手順
- demo pack
- sample `change-event.yml`
- runbook
- safe/full 運用ルール
- 顧客向け説明文サンプル
- 提出前チェックリスト
- サンプルレポート

主な導線:

- demo pack: `examples/demo-client-pack/`, `examples/vendor-poc-pack/`, `examples/vendor-poc-pack-pass/`
- sample `change-event.yml`: `templates/change-event.example.yml`
- runbook: `../user-guide/poc-monitor-runbook.md`

### 3.2 見せるが渡し切らないもの

ベンダーが利用判断や顧客説明に必要な範囲で見せるが、正本や全量は渡さないもの:

- 評価カテゴリ一覧
- サンプルテストケース
- Failure Pattern 概要
- S1 / S2 基準の概要
- Go / No-Go 基準の概要
- レポート出力例

ここでは、概要、説明用サンプル、顧客説明に必要な境界だけを見せます。判定ロジックの詳細、全量データ、業種別閾値差分、テンプレート運用ノウハウまでは開示しません。

### 3.3 渡さないもの

Proof Gate 側に保持する中核資産:

- テストケース DB 全量
- Failure Pattern DB 全量
- 判定ロジック詳細
- 業種別評価基準の詳細
- レポート生成テンプレート全量
- 過去案件から得た失敗パターン集
- 改善ノウハウ集の全量

## 4. Test Case Responsibility

Partner Platform では、**標準 test pack** と **顧客固有の実行ケース** を分けて扱います。

### 4.1 標準 test pack の責任

Proof Gate 側が保持・更新するもの:

- 汎用的な評価カテゴリ
- 再利用可能な test pack の骨格
- failure pattern の設計資産
- S1 / S2 設計原則
- サンプルケース
- ケース作成・レビューの runbook

これらは、ベンダーが顧客案件へ適用するときの出発点です。ただし、これだけでは顧客案件の executable source of truth にはなりません。

### 4.2 顧客固有の実行ケースの責任

顧客案件で実際に gate を回すための `cases.csv`、expected behavior、case ごとの active / draft / deprecated 管理は、原則としてベンダー側が持ちます。必要に応じて顧客確認を受けながら、ベンダーが顧客環境またはベンダー管理環境で更新します。

ベンダー側が持つものの例:

- 顧客固有の実行ケース (`cases.csv`)
- 顧客固有の `expected_answer`
- 顧客固有の `expected_evidence`
- 顧客固有の `expected_keywords`
- 顧客業務に合わせた category / severity / notes
- 変更後に見直すべき expected behavior

つまり、**Proof Gate 側は標準化された評価資産を保持し、ベンダー側は顧客固有の実行可能なケース資産を持つ** という責任分界にします。

### 4.3 expected behavior の更新責任

顧客固有 expected behavior の更新トリガーは、FAQ、規約、料金表、社内ルール、プロンプト、モデル、retrieval 設定など、顧客向け回答に影響する変更です。

このときの原則:

- 顧客固有 expected behavior を更新する主体はベンダー側
- 顧客承認が必要な expected answer は、ベンダーが顧客確認を取って反映する
- Proof Gate 側は、更新観点、failure pattern、review 観点、品質基準の助言はするが、顧客固有ケースの正本は原則持たない
- Proof Gate 側が受け取るのは、必要最小限の safe 集計と改善に必要な bounded metadata に留める

### 4.4 初回オンボーディング時の例外

初回 1 案件目では、Proof Gate 側がケース設計を併走支援することがあります。ただし、この場合でも最終的な executable case の保管場所と運用責任はベンダー側に置きます。

初回支援で Proof Gate 側が行うもの:

- S1 / S2 の切り方の助言
- failure pattern との対応づけの支援
- sample case の提示
- expected behavior の書き方の支援

初回支援でも Proof Gate 側が引き取らないもの:

- 顧客固有 `cases.csv` の継続保守責任
- 顧客固有 expected behavior の日常更新
- 顧客 raw case data の保管

### 4.5 月次運用で確認すること

月次 partner review では、少なくとも次を確認します。

- どの change-event があり、どのケースを追加・更新・deprecated にしたか
- `expected_answer` / `expected_evidence` の更新漏れがないか
- S1 ケースが顧客の現行リスクをまだ表しているか
- failure pattern と active case の対応が崩れていないか
- stale なケースや説明不能なケースが残っていないか

ここでの Proof Gate 側の役割は、safe 集計と運用知見からレビュー観点を返すことです。顧客固有ケースの正本管理そのものは、引き続きベンダー側の責任にします。

## 5. なぜ渡し切らないか

Proof Gate が中核資産を渡し切らない理由は以下です。

- 中核資産を保護するため
- ベンダーによる内製化・模倣リスクを下げるため
- 継続的な価値提供を維持するため
- test pack・failure pattern・レポートテンプレートを継続更新するため
- Proof Gate の競争優位を守るため

つまり、Proof Gate は「一度渡して終わり」ではなく、月次品質運用と改善支援を通じて継続利用される構造を取ります。

## 6. 初回オンボーディング導線

Partner onboarding（初回オンボーディング）は次の流れを前提にします。

1. NDA / 利用条件の合意
2. Partner Kit 提供
3. demo pack 実行
4. 初回 1 案件で併走
5. dashboard の読み方を説明
6. 顧客向け safe report の確認方法を説明
7. 2 案件目以降はベンダーが自走
8. 月次で safe 集計をもとに改善支援

この導線では、初回案件で safe/full boundary、review stage、`customer_shareability`、`customer_submission_readiness` の考え方を必ずすり合わせます。

## 7. 通常運用導線

通常運用では、`pre_delivery`、`post_delivery_change`、`monthly_review` の review stage を使い分けます。

1. 顧客が FAQ / 規約 / 料金表 / プロンプト等を変更
2. ベンダーが `change-event.yml` を作成
3. ベンダー環境で Proof Gate を実行
4. No-Go ならベンダーが修正
5. 再検査
6. Go / Conditional なら safe な customer-facing report を生成
7. ベンダーが顧客へ提出
8. Proof Gate 側は safe 集計のみ受け取り、test pack・文言・基準を改善

運用上の読み替え:

- `pre_delivery`: 納品前品質診断
- `post_delivery_change`: 納品後変更事故防止レビュー
- `monthly_review`: 月次 AI 回答品質レビュー

提出判断の原則:

- `customer_shareability` は、safe に共有できるかの判断です。
- `customer_submission_readiness` は、正式な顧客提出物として推奨できるかの判断です。
- No-Go でも safe draft が shareable な場合はありますが、通常は正式提出には使いません。

## 8. 継続提供価値

monthly partner review を含む継続提供価値は以下です。

- test pack 更新
- Failure Pattern 更新
- Severity / Go-NoGo 基準の改善
- 顧客提出レポート文言の改善
- 月次 safe 集計レビュー
- ベンダーの商品化支援
- 顧客向け説明資料の改善

Proof Gate の価値は、単発の実行環境提供ではなく、評価資産と説明資産を継続改善し続けることにあります。

## 9. 禁止 / 注意事項

- ベンダーにテストケース DB 全量を渡さない
- Failure Pattern DB 全量を渡さない
- 判定ロジック詳細を渡さない
- レポートテンプレート全量を渡さない
- 顧客 raw data を Proof Gate 側へ送らない前提を維持する
- safe/full 境界を壊さない
- Proof Gate を監視代行業務にしない

特に、full/raw evidence、raw question、raw answer、raw document、raw endpoint、full/private detail はベンダーまたは顧客の管理環境に留めます。Proof Gate 側は原則 safe summary、safe report、集計値、固定 taxonomy、運用改善に必要な bounded metadata のみを扱います。

## 10. Safe/Full Boundary

Partner Platform における safe/full boundary は次のとおりです。

| 区分 | 扱う場所 | 主な内容 |
|---|---|---|
| safe report / safe summary | ベンダー提出物、顧客共有物、safe 集計 | review stage、Go / No-Go 概要、S1/S2 件数、reason code、改善アクション、bounded metadata |
| full/private detail | ベンダー環境、private runner、customer-controlled environment | raw question、raw answer、retrieved evidence、source path、full logs、full report、customer-specific metadata |

原則:

- customer report は safe な顧客提出物として扱う
- delivery review dashboard は vendor internal review 用に使う
- full/raw evidence はベンダー / 顧客管理環境に留める
- Proof Gate 側は原則 safe 集計のみを受け取る

## 11. 契約で守るべき論点

これは法的断定ではなく、将来の契約・利用条件で守るべき論点の整理です。

- テストケース、Failure Pattern、判定基準、テンプレートの複製・再配布禁止
- 模倣目的の解析禁止
- 提供物の利用範囲は契約案件 / 契約顧客に限定
- 顧客向けレポートの改変ルール
- Proof Gate 中核資産の第三者提供禁止
- ベンダーは顧客データを自社責任で管理する
- Proof Gate 側は原則 full data を受け取らない

将来契約では、Partner Kit の利用範囲、sample/report の再利用範囲、safe report の改変許容範囲、full/private detail の持ち出し禁止、契約終了後の資産利用制限も論点になります。

## 12. 用語整理

この文書では以下の語を優先して使います。

| Preferred term | 日本語での併記 | 意味 |
|---|---|---|
| Partner Platform | パートナー提供方式 | Proof Gate の提供モデル全体 |
| Partner Kit | パートナーキット | ベンダーへ渡す実行環境・runbook・サンプル一式 |
| safe report | 顧客提出 safe レポート | 顧客共有可能な report |
| full/private detail | full / private detail | raw evidence を含む非共有詳細 |
| test pack | テストパック | 実行対象として提供するケース群 |
| failure pattern | failure pattern / 失敗パターン | 業務事故リスクを説明する設計資産 |
| delivery review dashboard | ベンダー社内レビュー | 社内確認用 dashboard |
| customer-facing report | 顧客向けレポート | safe な顧客提出物 |
| partner onboarding | 初回オンボーディング | 初回導入の併走導線 |
| monthly partner review | 月次パートナーレビュー | safe 集計ベースの継続改善 |

また、資産境界を説明するときは、**渡すもの / 見せるもの / 渡さないもの** を明示します。

## 13. Related Documents

- [Review stages and customer reports](../user-guide/review-stages-and-customer-reports.md)
- [PoC / Monitor runbook](../user-guide/poc-monitor-runbook.md)
- [AI Answer Release Control](ai-answer-release-control.md)
- [Proof Gate Release Control Design](proof-gate-release-control-design.md)
- [Demo vs production settings](../engineering/demo-vs-production-settings.md)
- [Logging and evidence policy](../security/logging-and-evidence-policy.md)
- [ADR 0005: Quality Asset Governance](../adr/0005-quality-asset-governance.md)

次PR候補として、`partner-operating-model.md` を追加し、誰が・いつ・何を・どの順番で実行するか、オンボーディング後の自走手順、monthly partner review の確認項目を別文書で整理する想定です。
