# Proof Gate付きRAG AI導入診断PoC

このPoCでの Proof Gate は、顧客対応AI/RAGを安全に導入・本番運用するための診断・構築・継続監視に範囲を絞っています。
一般的な監視基盤を作ることが目的ではありません。営業デモでは、サポートAIの更新を、確認し、止め、レビューし、Gateレポート化し、顧客へ説明できることを、細かい内部artifactを追わずに理解できる形で伝えることを目的にします。

## 最短の営業デモ

画面共有で安定して見せたい場合は、決定論的なデモartifactを使います。
ここには、正常通過の例、業務リスクで止まる例、信頼性低下で人手確認に回る例が含まれています。

```powershell
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python scripts\create_customer_support_demo_artifacts.py
.\.venv\Scripts\python -m rqg.cli serve-dashboard --workspace-dir . --runs-dir packs\customer_support_pack\reports\demo_runs --port 8012
```

開く画面:

- `http://127.0.0.1:8012/packs`
- `http://127.0.0.1:8012/runs`
- `http://127.0.0.1:8012/runs/csp-pass-202604`
- `http://127.0.0.1:8012/runs/csp-block-refund-202604`
- `http://127.0.0.1:8012/runs/csp-needs-review-fallback-202604`
- `http://127.0.0.1:8012/cases/failures`
- `http://127.0.0.1:8012/reports/monthly`

## このリポジトリでの役割分担

このリポジトリでは、PoCの役割を次のように分けています。

- `src/rqg/`: Proof Gate本体のCLIと評価ロジック。
- `packs/customer_support_pack/`: カスタマーサポート向けの再利用可能な品質Pack。
- `demos/customer_support_faq_change/`: FAQ v1→v2変更事故デモのFAQ本文、ケース、比較要約、before / after report。
- `docs/user-guide/`: PoC実行や説明に使う利用者向けガイド。
- `docs/sales/`: 提案や営業説明に使う資料。

最小の before / after 営業デモは `demos/customer_support_faq_change/` にまとまっています。

## FAQ v1→v2変更事故デモ

このデモは、1つのわかりやすい変更事故を見せるために用意しています。

1. 古いFAQ v1のまま危ない回答が出る。
2. Proof GateがS1重大失敗を検知し、本番反映判定を `NG` にする。
3. FAQ v2で再評価すると危ない回答が解消する。
4. 同じ高リスク質問セットで改善を説明できる。

リポジトリのルートで次を実行します。

```powershell
.\.venv\Scripts\python scripts\create_customer_support_faq_change_sales_demo.py
```

主要ファイル:

- `demos/customer_support_faq_change/demo_faq_v1.md`
- `demos/customer_support_faq_change/demo_faq_v2.md`
- `demos/customer_support_faq_change/generated_cases.csv`
- `demos/customer_support_faq_change/cases.csv`
- `demos/customer_support_faq_change/case_set_summary.json`
- `demos/customer_support_faq_change/reports/before_stale_v1/gate-report.md`
- `demos/customer_support_faq_change/reports/after_v2_reference/gate-report.md`
- `demos/customer_support_faq_change/demo_summary.json`

見せる順番は、before report の `1. 本番反映判定`、`5. S1重大失敗一覧`、`8. 月額Monitorで継続確認すべき項目` の順です。そのあと after report を開き、同じ高リスク質問でS1重大失敗が解消していることを見せます。

## 営業トークの流れ

1. `/packs` から入り、`Customer Support AI Quality Pack` を、返金・解約・料金・契約条件などの高リスク質問を確認するためのテンプレートとして説明する。
2. `/runs/csp-pass-202604` を開き、`policy_status=pass`、S1 fail count `0`、judge reliability `high`、fallback なしの正常例を見せる。
3. `/runs/csp-block-refund-202604` を開き、legacy の `status=fail`、`policy_status=block`、S1重大失敗、理由、対象 case ID、推奨アクションを見せる。
4. `/runs/csp-needs-review-fallback-202604` を開き、legacy の `status=pass` でも `policy_status=needs_human_review` になり得ること、`judge_reliability=low`、fallback 使用、人手承認待ちという状態を説明する。
5. `/cases/failures` を開き、JSONを読まなくても、どのケースが危なく、何をすべきかが見えることを説明する。
6. `/reports/monthly` を開き、月額Monitorの価値として、確認した実行数、止めた更新、S1重大失敗、fallback の傾向、未解決事項、推奨アクションを説明する。

## 判定と信頼性の見方

従来の `status` フィールドは `pass`、`warn`、`fail` のままです。Proof Gateは、業務判断のために `policy_status` を追加します。

- `pass`: そのまま進めてよい状態。
- `warn`: 閾値は通っているが、追跡確認を推奨する状態。
- `block`: S1重大失敗やハード閾値違反があり、本番反映を止めるべき状態。
- `needs_human_review`: 判定の信頼性が下がっており、人手確認が必要な状態。

Gate artifact には、`judge_reliability`、`fallback_summary`、`retrieval_reliability`、`needs_human_review`、将来の承認フロー用 `approval` stub も含まれます。

次の2つのデモ run を並べると、確定した業務リスクと、評価器側の不確実性の違いを説明しやすくなります。

- `csp-block-refund-202604`: `policy_status=block`、`fallback_summary.block_origin=business_risk`、`judge_reliability=high`。顧客向け回答がS1の返金・解約条件で誤っているため止めています。
- `csp-needs-review-fallback-202604`: `policy_status=needs_human_review`、`fallback_summary.block_origin=evaluator_reliability`、`judge_reliability=low`。回答を安全に出せると判断するだけの信頼性が足りないため、人手確認に回しています。

要点は、Proof Gateは確定したS1業務リスクを止めるだけでなく、不確実な run も黙って通さず、人手確認へ送るということです。

## CLIでその場実行する場合

画面共有のあと、そのまま通常CLIフローで見せることもできます。

```powershell
.\.venv\Scripts\python -m rqg.cli gate --pack packs\customer_support_pack --mock --log-dir runs\customer_support_pack --reset-log-dir
.\.venv\Scripts\python -m rqg.cli report-monthly --log-dir runs\customer_support_pack --month 2026-04
```

初回のローカル文書デモでは、Windows PowerShell を UTF-8 にし、retrieval 依存や embedding model が既にそろっている場合を除いて、まずは決定論的artifactを優先するのが安全です。

## Windows実行メモ

コマンドはリポジトリのルートで PowerShell から実行します。`.\.venv\Scripts\python` を使うと、実行環境ごとの差異を減らせます。Windows で pytest 全体実行時に coverage や temp cleanup が権限エラーになる場合は、機能確認用として同じスイートを `--basetemp` と `--no-cov` 付きで再実行します。

```powershell
.\.venv\Scripts\python -m pytest --no-cov --basetemp=.pytest-tmp-full-hardening
```

## 月額Monitor / 月次レポート

月次artifactは `monthly-summary.json` と `monthly-summary.md` として出力されます。ここには、実行件数、block件数、S1重大失敗、主な理由、fallback傾向、未解決事項、推奨アクションが含まれます。

## 新しいPackの作成

新しい顧客向けFAQ Pack は次で作成できます。

```powershell
rqg init-pack packs/new_customer_support --profile customer_support
```

そのあと tenant metadata を更新し、文書を差し替え、初回実行前に S1 / S2 ケースを見直します。
