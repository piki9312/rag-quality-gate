# Proof Gate Release Control Design

## 1. 背景

Proof Gateは従来、RAG / AI回答の品質評価ツールとして始まった。高リスク質問を`cases.csv`に整理し、RAGや顧客対応AIの回答を評価し、Gate ReportやGateDecisionとして結果を残すことが中心だった。

しかし、Anthropic、OpenAI、Googleなどの大手AI企業は、ケース生成、RAG評価、LLM Judge、脆弱性発見、修正提案、監査補助を高度化している。AGI/ASIや大手AI評価システムが進むほど、「評価する知能」そのものはコモディティ化しやすい。ケース生成、RAG評価、LLM Judge、レポート生成をProof Gateの中核価値に置くと、将来的に代替される可能性が高い。

そのため、Proof Gateは評価エンジンを中核にするのではなく、評価結果を業務上の承認・証跡・ReleaseDecisionに変換する方向へ移る。現在のGate engineは捨てない。下層部品として再位置づけ、AI回答変更のリリース判断を支える評価実行・証跡収集の部品として扱う。

## 2. 新しい定義

Proof Gateは、AI Answer Release Control layerである。

別の言い方をすると、Proof GateはCustomer-facing AI Release Controlであり、顧客対応AIの変更管理・承認・証跡・リリース判定レイヤーである。

顧客向けには、次のように説明する。

FAQや料金表、規約、プロンプトを変更したときに、AI回答をそのまま本番に出してよいかを確認し、人間レビューと承認記録を残す仕組み。

投資家向けには、次のように説明する。

Proof Gate is not an AI evaluator. It is a control plane for customer-facing AI changes: what changed, what risks were detected, who approved the release, what evidence was retained, and whether the AI output can be released.

## 3. Before / After

| 観点 | Before | After |
|---|---|---|
| プロダクト定義 | RAG評価ツール | AI Answer Release Control |
| 顧客向け価値 | AI回答リスク診断 | AI回答変更の承認・証跡・リリース判定 |
| 主成果物 | Gate Report | ReviewPacket / ReleaseDecision |
| 中心概念 | Case / Evaluator / GateDecision | ChangeEvent / ReviewPacket / Approval / ReleaseDecision |
| 評価器 | LLM Judgeやケース生成に価値を置く | Evaluatorは交換可能なAdapter |
| GateDecision | 最終判断に近い扱い | ReleaseDecisionの材料 |
| Gate Report | 評価レポート | ReviewPacketへ昇格 |
| 証跡境界 | 評価ログ中心 | safe/full evidence boundaryを維持 |

このAfterでは、評価そのものは重要だが主役ではない。主役は、変更イベントに対して、どのリスクが見つかり、誰が確認し、どの証跡を根拠に、どの条件で本番反映するかを判断する流れである。

## 4. 中核データモデル

### ChangeEvent

顧客対応AIの回答に影響し得る変更を表す。例:

- FAQ update
- pricing change
- terms update
- prompt change
- model change
- RAG index update

ChangeEventは、何が変わったか、なぜ変えたか、どの文書・設定・モデル・プロンプトが対象か、いつ本番反映したいかを持つ。

### ImpactScope

ChangeEventが影響し得る範囲を表す。例:

- affected docs
- affected risk domains
- affected cases
- affected customer-facing answers

ImpactScopeは、すべての質問を網羅するためのものではない。高リスクな変更に対して、どの業務領域と回答パターンを重点確認するかを明確にするためのもの。

### GateRun

内部Gate engineまたは外部Evaluatorの実行を表す。現在の`rqg gate`、外部AI評価、Zendesk QA、人間レビューなどがGateRunの入力になり得る。GateRunは評価実行そのものであり、ReleaseDecisionではない。

### EvaluatorResult / NormalizedEvaluatorResult

EvaluatorResultは、OpenAI、Anthropic、Google、Zendesk QA、internal RQG、人間レビューなどから返る評価結果である。

NormalizedEvaluatorResultは、それらをProof Gateの判断ワークフローで扱える形に正規化した結果である。外部AIのfree-form outputをそのまま使わず、safe reason code、severity、risk domain、evidence pointer、数値スコア、review needなどへ変換する。

### ReviewPacket

人間が承認判断するための資料である。ReviewPacketには、ChangeEvent、ImpactScope、GateRun結果、NormalizedEvaluatorResult、検出リスク、必要な人間レビュー、承認候補、証跡参照をまとめる。

ReviewPacketはsafe版とfull版を分ける。safe版は顧客共有、CI、承認フローで扱いやすい集計・判断中心の資料にする。full版は質問文、回答本文、根拠本文、詳細ログなどを含む可能性があるため、顧客管理環境またはprivate/local環境で扱う。

### Approval

誰が、どの役割で、何を承認・差し戻し・保留・リスク受容したかを表す。Approvalは人間判断として記録する。AI評価結果が良いだけで自動的に本番反映してよいとは扱わない。

### RiskAcceptance

残ったリスクを誰がどう受け入れたかを表す。既知のリスク、許容理由、期限、監視条件、再確認条件を記録する。RiskAcceptanceは、問題が存在しないという意味ではない。残リスクを認識したうえで条件付きに進める判断である。

### ReleaseDecision

ChangeEventを本番反映してよいかを表す最終判断である。例:

- approved
- blocked
- needs legal review
- deferred
- approved with risk

ReleaseDecisionはGateDecisionと混同しない。GateDecisionは評価・Gate実行の結果であり、ReleaseDecisionは業務上のリリース判断である。

### EvidencePolicy

証跡の扱いを定義する。特に、CIに出してよいもの、顧客環境に残すもの、retention、deletion/archiveを分ける。

CIにはsafe summaryのみを出す。質問文、回答本文、根拠本文、自由記述の失敗理由、raw logs、JSONL、full reportはCI artifactにしない。full evidenceはcustomer-controlled environmentに置く。

### AuditTrail

ChangeEventからReleaseDecisionまでの履歴を表す。何が変わり、何を評価し、どのReviewPacketを見て、誰が承認し、どの証跡を残したかを時系列で追えるようにする。

## 5. 現在実装との関係

既存CLI / Gate / report / safe summary / CI-safe hardeningは捨てない。ただし、これらは中核ではなく、Gate engine / evaluator adapter / evidence collectionとして扱う。

- `rqg gate`はGate engineとして扱う。
- GateDecisionはReleaseDecisionの材料になる。
- Gate ReportはReviewPacketへ昇格する。
- CI-safe outputはEvidencePolicyの一部になる。
- retrieval / answer / judge evaluatorは交換可能な評価器の1つになる。
- gate-report-ci、safe summary、fixed reason taxonomyはsafe ReviewPacketの材料になる。
- full report、raw JSONL、raw cases、raw quality pack、raw gate configはcustomer-controlled environmentに残す。

現在の実装は、Release Controlへ移行するための評価実行層として残す。プロダクトの主語は「評価する」から「変更を承認可能な形にする」へ移す。

## 6. 大手AI評価システム前提の設計原則

Proof Gate does not own intelligence. Proof Gate owns decision workflow.

評価器は交換可能にする。OpenAI、Anthropic、Google、Zendesk QA、internal RQG、人間レビューをadapterとして受けられるようにする。

外部AIのfree-form outputをそのままCI-safe outputに出さない。必ずsafe reason code、severity、risk domain、evidence pointerに正規化する。特に顧客名、制度名、契約条件、質問本文、回答本文、根拠本文、自由記述の失敗理由をCI-safe outputへ混ぜない。

full evidenceはcustomer-controlled environmentに置く。Proof Gate側が持つべきものは、判断に必要な安全なメタデータ、証跡への参照、承認履歴、ReleaseDecisionである。

## 7. ROIと運用負荷の設計原則

Proof Gateは全AI回答を常時監査しない。高リスクな変更イベントに絞る。

変更イベント単位でROIを出す。たとえば料金改定、規約変更、返金条件変更、FAQ大幅更新、AIチャットボット公開前など、誤回答が業務事故につながるタイミングに絞って確認する。

最初の対象は10から30ケース程度に絞る。顧客ごとの過剰カスタムを避ける。ReviewPacketは1から2枚に収まるようにする。月次monitorより、変更イベント課金・変更時チェックから始める。

対象イベント:

- 料金改定
- 規約変更
- 返金条件変更
- 解約条件変更
- FAQ大幅更新
- AIチャットボット公開前
- プロンプト/モデル/RAG設定変更

## 8. データ管理原則

Proof Gate側に持ってよいもの:

- ChangeEvent metadata
- risk domain
- severity count
- safe reason code
- safe ReviewPacket summary
- Approval status
- ReleaseDecision
- full evidence pointer
- timestamp
- approver role

顧客環境に残すもの:

- 質問文
- 回答本文
- 根拠本文
- raw logs
- JSONL
- full report
- full ReviewPacket
- raw cases
- raw quality pack
- raw gate config

この分離は、CI-safeが完全な漏洩保証であるという意味ではない。露出リスクを下げる設計であり、顧客データを扱う場合は保存場所、保持期間、削除・archive手順を事前に決める。

## 9. MVP

最初のMVPは、UI、DB、権限管理、SaaS multi-tenantを持たない。CLIとファイルベースのschemaで、ChangeEventからReleaseDecisionまでの最短経路を作る。

MVP成果物:

- `change-event.yml`
- `review-packet.md`
- `review-packet.json`
- `release-decision.json`
- `approval-log.json`
- `evidence-policy.yml`

CLI例:

```powershell
rqg gate --change-event change-event.yml
rqg review create --change-event change-event.yml
rqg release decide --review-packet review-packet.json
```

最初のデモは、FAQや料金表の変更をChangeEventとして定義し、GateRunを実行し、ReviewPacketを作り、人間レビューを経てReleaseDecisionを残す形にする。

## 10. やること / やらないこと

### Must

- ChangeEvent schema
- ReviewPacket schema
- ReleaseDecision schema
- EvidencePolicy接続
- change-event based demo

### Should

- ExternalEvaluatorAdapter
- GitHub Issue or Slack approval stub
- 顧客向け資料のAI Answer Release Controlへの言い換え

### Later

- dashboard
- SaaS multi-tenant
- fine-grained RBAC
- LLM Judge高度化
- 業界別Pack大量生産

### Stop

- 単独RAG評価SaaSとしての機能追加
- LLM Judge精度競争
- 業界別ケース資産を堀とみなすこと
- full evidenceをProof Gate側で保持すること
- 汎用ダッシュボードへの過投資

## 11. 設計上の注意

- GateDecisionとReleaseDecisionを混同しない。
- ReviewPacketはsafe/fullを分ける。
- 外部Evaluator出力は必ず正規化する。
- free-formをCI-safeに出さない。
- sanitizerはDLPではなく最後の保険である。
- full evidenceは顧客環境に置く。
- Approvalは人間判断として記録する。
- UIは後回しにする。
- まずChangeEvent demoを作る。

## 12. 成果物のトーン

顧客向けには、非エンジニアにも分かる説明を入れる。たとえば、FAQや料金表を変更したときに、AI回答をそのまま本番に出してよいかを確認し、人間レビューと承認記録を残す仕組み、と説明する。

一方で、設計資料としては、データモデルと実装方針を明確に書く。ChangeEvent、ImpactScope、GateRun、NormalizedEvaluatorResult、ReviewPacket、Approval、RiskAcceptance、ReleaseDecision、EvidencePolicy、AuditTrailの責務を混ぜない。

「完全保証」「PASSなら安全」「AI回答品質を保証」とは書かない。「リリース判断を補助する」「人間レビューに回す」「証跡を残す」と表現する。
