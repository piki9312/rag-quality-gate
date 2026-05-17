# AI Answer Release Control

## 1. 背景

フロンティアAI企業は、RAG評価、ケース生成、LLM Judge、脆弱性検出、修正提案を急速に高度化している。評価器そのものやケース生成をProof Gateの中核価値に置くと、より強い基盤モデルや大手AIプラットフォームに代替されやすい。

Proof Gateは、RAG評価ツールではなく、AI回答の変更を業務上の承認・証跡・リリース判断へ変換するレイヤーへ移る。評価エンジンは重要な部品だが、Proof Gateが持つべき中核は「評価結果を誰が見て、何を根拠に、どの条件で本番反映してよいと判断したか」を残す変更管理と統制である。

この方針では、Proof Gateを「AI Answer Release Control」、つまり顧客対応AIの変更管理・承認・証跡・リリース判定レイヤーとして位置づける。

## 2. Before / After

| 観点 | Before | After |
|---|---|---|
| 位置づけ | RAG / AI回答の品質評価ツール | Customer-facing AI Release Control |
| 中心成果物 | Gate Report | ReviewPacket / ReleaseDecision |
| 中心概念 | Case / Evaluator / GateDecision | ChangeEvent / ReviewPacket / Approval / ReleaseDecision |
| 評価器 | 内部評価器中心 | 外部AI、大手AI、顧客指定モデル、人間レビューを含むpluggable adapter |
| 顧客価値 | 回答品質の可視化 | AI回答変更を本番反映してよいかの判断補助と証跡化 |
| 運用対象 | 評価実行 | 変更イベント、影響範囲、評価結果、承認、リスク受容、監査証跡 |

## 3. 中核概念

### ChangeEvent

FAQ、規約、料金表、プロンプト、モデル、検索設定、RAG接続先など、顧客対応AIの回答に影響し得る変更を表す。変更理由、対象範囲、変更前後の参照、実施者、予定リリース日を持つ。

### ImpactScope

ChangeEventが影響し得る業務領域、ユーザー種別、文書、FAQカテゴリ、重大リスク領域を表す。すべての利用者質問を網羅するものではなく、事前に定義した高リスク領域の確認範囲を明確にする。

### EvaluatorAdapter

OpenAI、Anthropic、Google、Zendesk QA、internal RQG、人間レビューなど、評価結果を返す外部または内部の評価器を接続する境界。Proof Gateは評価知能そのものを所有せず、評価結果を正規化して判断ワークフローへ渡す。

### NormalizedEvaluationResult

EvaluatorAdapterから得た評価結果を、ReleaseDecisionで扱える共通形式に変換したもの。評価器固有の自由記述をそのままCI-safe outputへ出さず、固定taxonomy、集計値、安全な参照に正規化する。

### ReviewPacket

顧客担当者や上長が本番反映可否を判断するための主資料。ChangeEvent、ImpactScope、NormalizedEvaluationResult、GateDecision、重要リスク、必要な人間レビュー、承認状況をまとめる。現在のGate Reportは、運用詳細ではなくReviewPacketの一部または根拠資料へ昇格させる。

### Approval

本番反映、差し戻し、条件付き承認、人間レビュー待ちなどの判断を、誰が、いつ、どの根拠で行ったかを表す記録。承認はAI品質の完全保証ではなく、定義済み範囲に対するリリース判断である。

### RiskAcceptance

既知の残リスクを把握したうえで、条件付きで本番反映する判断を表す。残リスク、許容理由、期限、監視条件、再評価条件を明記する。

### ReleaseDecision

ChangeEventを本番反映してよいかを表す最終判断。例として、`pass`、`block`、`needs_human_review`、`conditional`、`review`を扱う。GateDecisionはReleaseDecisionの材料であり、ReleaseDecisionそのものではない。

### EvidencePolicy

証跡の保存場所、保存期間、閲覧範囲、CI-safe summaryとfull evidenceの境界を定義する。GitHub Actionsにはsafe summaryのみを出し、full evidence、full report、detailed logsはlocal、private runner、customer-controlled environmentに置く。sanitizerはDLPではなく最後の保険である。

### AuditTrail

ChangeEvent、評価実行、ReviewPacket、Approval、RiskAcceptance、ReleaseDecision、関連証跡への参照を時系列で残す監査記録。顧客データ本文ではなく、必要最小限の安全な参照と判断履歴を中心にする。

## 4. 現在実装との関係

現在のCLI、Gate、report、safe summary、CI-safe hardeningは捨てない。これらはAI Answer Release Controlの土台として再位置づける。

- `rqg gate` はGate engineとして、変更後AI回答の検査を実行する。
- Evaluator、retrieval check、LLM Judge、fallback判定はEvaluatorAdapterの一種として扱う。
- `GateDecision` はReleaseDecisionの材料になる。
- `gate-report.md`、`gate-report-ci.*`、`gate-decision.json` はReviewPacketを作るための根拠資料になる。
- CI-safe stdout、safe artifact allowlist、fixed reason taxonomyはEvidencePolicyの実装部品になる。
- full evidenceはGitHub-hosted CIでは扱わず、local、private runner、customer-controlled environmentに置く。

つまり、現在実装は「評価ツール」として廃棄するのではなく、Release Controlの評価・証跡収集エンジンとして残す。ただし、顧客向けの主語は「評価しました」から「この変更を本番反映してよいか判断できる状態にしました」へ移す。

## 5. 大手AI評価システム前提の設計原則

Proof Gate does not own intelligence. Proof Gate owns decision workflow.

評価精度、ケース生成、脆弱性検出は、外部AIや大手AIプラットフォームが継続的に強くなる前提で設計する。Proof Gateは、どの評価器を使ったか、結果をどう正規化したか、誰が承認したか、どの証跡を残したかを管理する。

設計原則:

- Evaluatorは交換可能にする。
- OpenAI、Anthropic、Google、Zendesk QA、internal RQG、人間レビューをadapterとして受けられるようにする。
- 外部AIのfree-form outputをそのままCI-safe outputへ出さない。
- CI-safe outputは集計値、固定taxonomyのreason code、安全なartifact参照に制限する。
- full evidence、raw answer、retrieved evidence、自由記述の失敗理由はlocal、private runner、customer-controlled environmentで扱う。
- sanitizerはDLPではなく最後の保険として扱う。
- GateのPASSは完全安全を意味しない。指定ケース、指定文書、指定設定に対する検査結果として扱う。

## 6. 今後90日の方針

### Must

- ChangeEvent schema
- ReviewPacket schema
- ReleaseDecision schema
- EvidencePolicyとの接続
- change-event based demo

### Should

- ExternalEvaluatorAdapter interface
- GitHub Issue or Slack approval stub
- 顧客向け資料の「AI回答変更管理」への言い換え

### Later

- dashboard
- SaaS multi-tenant
- LLM Judge高度化
- 業界別Pack大量生産

### Stop

- 単独RAG評価SaaSとしての機能追加
- LLM Judge精度で勝とうとすること
- 業界別ケース資産を堀とみなすこと
- 汎用ダッシュボードへの過投資

## 7. 顧客向け説明

Proof Gateは、FAQや料金表、規約、プロンプト、モデル、検索設定を変更したときに、AI回答をそのまま本番に出してよいかを確認し、必要な人間レビューと承認記録を残す仕組みです。

事前に定義した高リスク質問や重要業務領域を検査し、重大誤回答リスク、判定不能、根拠不足、人間確認が必要な箇所を可視化します。これはAI回答品質を完全保証するものではなく、公開前の判断を補助し、誰が何を根拠に承認したかを残すための変更管理レイヤーです。

GitHub ActionsなどのCIではsafe summaryのみを扱い、質問本文、回答本文、根拠本文、詳細ログなどのfull evidenceは顧客管理環境、private runner、またはlocal環境で扱います。

## 8. 投資家向け説明

Proof Gateは、RAG評価ツールではなく、customer-facing AI changesのcontrol plane / system of recordを目指す。

AI回答の品質評価は、基盤モデル企業や大手AIプラットフォームによって継続的に高度化される。一方で、企業が顧客対応AIを本番運用するには、変更イベント、影響範囲、評価結果、承認、リスク受容、リリース判断、監査証跡を一貫して管理する必要がある。

Proof Gateはこの運用レイヤーを担う。評価器はpluggableにし、外部AIや顧客指定モデルの結果も取り込む。そのうえで、顧客対応AIの変更を「評価結果」ではなく「承認可能なリリース判断」として管理する。

短期的にはCLI、Quality Pack、external adapter、ReviewPacket、ReleaseDecisionを中心に、paid PoCから月額運用へつながる半プロダクト・半サービスの形を取る。SaaS、multi-tenant、認証、課金、汎用ダッシュボードは、運用実績が積み上がるまで過投資しない。
