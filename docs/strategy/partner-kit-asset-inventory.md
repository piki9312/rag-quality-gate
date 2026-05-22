# Partner Kit Asset Inventory

## 目的

この文書は、Proof Gate を RAG / FAQ AI 導入ベンダー向けの Partner Platform 方式で提供するときに、repo 内の既存資産を次の3分類へ棚卸しするためのものです。

1. **ベンダーに渡すもの**
2. **ベンダーに見せるが渡し切らないもの**
3. **Proof Gate側に保持するもの**

目的は、商談・オンボーディング・PoC開始時に、何を安全に渡してよいか、何を画面共有や抜粋説明に留めるか、何を中核資産として守るかを明確にすることです。

この文書はドキュメント整理です。CLI、Dashboard、ReviewPacket、`gate-report.json`、safe/full 実装、reporting logic は変更しません。

## 前提

- Partner Kit は、ベンダーが自社または顧客環境で Proof Gate の価値を理解し、最小PoCを再現するための配布物です。
- 顧客raw data、raw questions、raw answers、retrieved evidence、full logs、full reports は Proof Gate側へ送らない前提です。
- GitHub-hosted CI は sample/mock/dummy data のみを扱います。
- Dashboard はベンダー社内レビュー用の表示例です。顧客提出物そのものではありません。
- `cases.csv` は最終ケース正本ですが、標準pack全量や過去案件由来のfailure pattern全量はPartner Kitには含めません。
- safe artifact は共有可能性を下げるための境界です。DLPや完全な漏洩保証ではありません。

## A. ベンダーに渡すもの

ベンダーが手元で再現・検証・説明できるように渡してよいものです。原則として demo / sample / template / runbook に限定し、実顧客データや中核判断資産は含めません。

| 資産 | 代表ファイル | 渡す理由 | 注意点 |
|---|---|---|---|
| Partner Kit入口 | `docs/strategy/partner-kit-asset-inventory.md` | 何を渡してよいかの境界を共有する | この文書自体は配布可 |
| デモpack | `examples/demo-client-pack/`, `examples/vendor-poc-pack-pass/`, `examples/vendor-poc-pack/` | ベンダーが最小pack構造、PASS/FAIL例、`cases.csv` を理解できる | demo/anonymized data限定 |
| Release Review demo pack | `packs/release_review_demo/README.md`, `quality-pack.yml`, `gate.yml`, `cases.csv`, `change-event.yml` | change-event付きのリリースレビュー価値を5分で再現できる | 架空データであることを明記して渡す |
| sample change event | `templates/change-event.example.yml`, `packs/release_review_demo/change-event.yml` | 変更イベントmetadataの書き方を示す | 顧客名、raw document name、path、target_releaseを入れない |
| customer project template | `templates/customer-rqg-template/` | 顧客環境・ベンダー環境に複製する初期形 | placeholder文書のみ。実顧客データは各環境で管理 |
| sample pack template | `templates/sample_pack/` | Quality Packの最小構造を説明する | sample data限定 |
| GitHub workflow templates | `templates/github/`, `templates/github/workflows/` | CI-safe gate運用の参考 | artifact allowlistとmock/sample前提を外さない |
| 実行runbook | `docs/user-guide/proof-gate-poc.md`, `docs/user-guide/poc-monitor-runbook.md`, `docs/user-guide/windows-powershell.md` | ベンダーがローカル/PoCで実行できる | customer-controlled環境でfull evidenceを扱う |
| review stage guide | `docs/user-guide/review-stages-and-customer-reports.md` | pre-delivery / post-delivery / monthly review の使い分けを説明する | Dashboardは内部レビュー用である境界を維持 |
| safe/full policy | `docs/security/logging-and-evidence-policy.md` | 顧客データ、artifact、stdout、CIの境界を共有する | 「sanitizerがあるから実データをCIへ出してよい」と読ませない |
| external RAG adapter guide | `docs/engineering/external-rag-adapter-contract.md`, `examples/external-rag-fixtures/` | ベンダーごとのRAG API差分をadapter境界で吸収する説明 | token、endpoint、raw responseは渡さない |
| customer-facing sample docs | `docs/sales/customer_gate_report_template.md`, `docs/sales/customer_data_handling_onepager.md`, `docs/sales/post_poc_options_onepager.md`, `docs/sales/rag_build_scope.md`, `docs/sales/poc-readiness-checklist.md` | 顧客説明と提出前確認に使える | 案件名・顧客名を入れる前はtemplateとして渡す |
| sample reports | `demos/customer_support_faq_change/customer_gate_report.md`, `before_after_onepager.md`, committed demo reports | 顧客提出物の完成イメージを示す | 架空デモであることを明記。full bundleは渡さない |

## B. ベンダーに見せるが渡し切らないもの

商談、オンボーディング、共同レビューでは画面共有・抜粋・説明に使ってよいが、ファイル全量や詳細定義を渡し切らないものです。ベンダーが価値を理解するには必要ですが、Proof Gate側の判断資産やノウハウを守る必要があります。

| 資産 | 代表ファイル | 見せ方 | 渡し切らない理由 |
|---|---|---|---|
| 評価カテゴリとseverity概要 | `docs/user-guide/quality-pack-s1-s2-design.md`, `docs/glossary.md` | S1/S2の考え方、BLOCK/REVIEW/PASS例を説明する | 詳細な業種別基準や蓄積済み境界判断は保持 |
| failure pattern概要 | `docs/demo/internal-s1-case-authoring.md`, `docs/adr/0005-quality-asset-governance.md`, `docs/adr/0007-auto-generated-review-and-merge-policy.md` | S1ケース作成の補助線として説明する | failure pattern DB全量や過去案件由来のパターンは保持 |
| Go/No-Go基準概要 | `docs/strategy/proof-gate-release-control-design.md`, `docs/user-guide/review-stages-and-customer-reports.md` | GateDecisionとReleaseDecisionの違い、ReviewPacketの位置づけを説明する | 判定ロジック詳細、承認設計詳細、業種別基準は保持 |
| ReviewPacket概念 | `src/rqg/domain/review_packet.py`, `tests/test_review_packet.py` | safe/full境界やcustomer submission readinessの概念を説明する | schema/logicの詳細運用や生成ロジックを配布物化しない |
| Dashboard画面 | `src/rqg/serving/dashboard.py`, `docs/user-guide/proof-gate-poc.md` | demo runで画面共有する | Dashboardは内部レビュー用。顧客提出artifactではない |
| レポート出力例 | `demos/customer_support_faq_change/reports/`, `templates/sample_pack/reports/example-impact-report.json` | sample reportとして抜粋表示する | full report bundleや顧客案件用report template全量は保持 |
| reason taxonomy概要 | `src/rqg/quality/reason_taxonomy.py`, `docs/security/logging-and-evidence-policy.md` | CI-safe reason codeの考え方を説明する | taxonomy設計・normalization詳細はProof Gate側で管理 |
| artifact exposure policy概要 | `src/rqg/quality/artifact_exposure_policy.py`, `tests/test_artifact_exposure_policy.py` | safe artifact allowlistの考え方を説明する | 実装詳細は保持し、契約としてはpolicy docsを渡す |
| case generation / merge flow概要 | `src/rqg/casegen/`, `src/rqg/quality/case_merge.py`, related tests | generated候補は正本ではないことを説明する | S1設計ノウハウや生成プロンプト/評価改善ノウハウは保持 |

## C. Proof Gate側に保持するもの

中核資産として保持し、Partner Kitには含めないものです。必要に応じて共同作業や有償支援の中で、safeな抜粋・説明・結果だけを共有します。

| 資産 | 代表ファイル / 領域 | 保持する理由 |
|---|---|---|
| 標準test pack全量 | `packs/customer_support_pack/`, `packs/hr/`, `packs/wiki/`, accumulated customer-derived variants | 業種別・案件横断の品質資産。配布すると差別化要素が薄まる |
| failure pattern DB全量 | `docs/agents/*`, internal notes, future registry | 過去案件から得た失敗パターン集は中核資産 |
| severity / Go-NoGo詳細基準 | `docs/strategy/proof-gate-release-control-design.md`, internal PM rules, future release decision rules | S1/S2境界やリスク受容判断は事業ノウハウ |
| 判定ロジック詳細 | `src/rqg/domain/gate_decision.py`, `src/rqg/quality/check.py`, `src/rqg/quality/reporting.py`, `src/rqg/quality/reason_taxonomy.py` | GateDecision / reporting / reason normalization の実装は保持 |
| ReviewPacket生成・readiness logic | `src/rqg/domain/review_packet.py`, `src/rqg/quality/reporting.py`, related tests | Partner Platformの中核となる承認・提出判断ロジック |
| report template / reporting logic全量 | `src/rqg/quality/reporting.py`, `src/rqg/locales/`, report tests | 顧客提出物の型と生成品質はProof Gate側の資産 |
| safe/full実装詳細 | `src/rqg/quality/report_mode_policy.py`, `src/rqg/security/sanitizer.py`, `src/rqg/quality/artifact_exposure_policy.py` | data boundaryの品質を担保する内部実装 |
| external adapter implementation | `src/rqg/serving/external_adapter.py`, `src/rqg/serving/connection_validation.py` | ベンダー差分を吸収する実装ノウハウ |
| テストスイート | `tests/` | 契約・regression・安全境界を保証する内部品質資産 |
| 過去案件から得た改善ノウハウ | `docs/strategy/notion-business/`, `docs/ops/`, internal review notes | 共通化前の事業/運用メモ。配布物ではない |
| 顧客raw data / full evidence | customer-controlled storage only | Proof Gate側に集約しない。必要時も保存場所・保持期間・削除手順を合意する |

## Partner Kit 推奨構成

最初に安全に渡すPartner Kitは、次の範囲に絞ります。

```text
docs/user-guide/proof-gate-poc.md
docs/user-guide/review-stages-and-customer-reports.md
docs/user-guide/windows-powershell.md
docs/security/logging-and-evidence-policy.md
docs/engineering/external-rag-adapter-contract.md
docs/sales/customer_gate_report_template.md
docs/sales/customer_data_handling_onepager.md
docs/sales/post_poc_options_onepager.md
docs/sales/rag_build_scope.md
docs/sales/poc-readiness-checklist.md
examples/demo-client-pack/
examples/vendor-poc-pack-pass/
templates/customer-rqg-template/
templates/change-event.example.yml
templates/github/
packs/release_review_demo/
```

除外するもの:

- `runs/`, `demo_runs/`, `index/`
- real customer documents
- raw JSONL
- full `gate-report.json` generated from customer data
- full ReviewPacket generated from customer data
- internal failure pattern DB
- accumulated customer-derived packs
- implementation internals under `src/`
- full tests under `tests/`
- `docs/strategy/notion-business/`
- `docs/agents/`

## オンボーディング導線

ベンダーには次の順で見せます。

1. **価値説明**: `docs/strategy/proof-gate-product-map.md` と顧客提出サンプルを見せる。
2. **安全境界**: `docs/security/logging-and-evidence-policy.md` で safe/full と raw data非送付を確認する。
3. **再現デモ**: `packs/release_review_demo/` または `examples/demo-client-pack/` をローカル実行する。
4. **顧客環境テンプレート**: `templates/customer-rqg-template/` を複製し、placeholderを顧客/ベンダー管理環境で差し替える。
5. **提出前確認**: `docs/sales/poc-readiness-checklist.md` と customer report template を使う。
6. **本番判断**: Dashboardはベンダー内部レビューに使い、顧客提出はcustomer-safe reportに限定する。

## 運用ルール

- ベンダーに渡す `cases.csv` は sample/demo/template のみ。
- 実顧客 `cases.csv` はベンダーまたは顧客管理repoで保持し、共通repoへ戻さない。
- `change-event.yml` は bounded metadata のみを入れる。
- Dashboardのスクリーンショット共有は、sample dataまたはredacted/safe dataに限定する。
- `full` report mode は local / private runner / customer-controlled environment のみ。
- GitHub Actions artifact は allowlist運用を維持し、whole `log_dir` uploadは禁止。
- Proof Gateは監視代行業務そのものにはしない。ベンダーが顧客接点・一次運用を持ち、Proof Gate側はkit、基準、改善支援、Release Gate設計を提供する。

## 今回まだ作らないもの

- Partner Kit自動生成CLI。
- asset registry。
- failure pattern DB公開形式。
- usage log / seen_count。
- SaaS tenant workspace。
- partner portal。
- dashboardの顧客提出UI化。
- `GateDecision` / `ReviewPacket` / `gate-report.json` schema変更。

## 棚卸し上の注意

この作業ツリーでは `docs/strategy/partner-platform-model.md` は確認できませんでした。別ブランチまたは未反映文書として存在する場合、この棚卸し文書はその方針文書の実資産マッピングとして扱ってください。
