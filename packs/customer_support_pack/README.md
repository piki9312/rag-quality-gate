# Customer Support AI Quality Pack

この Pack は、Proof Gate付きRAG AI導入診断PoC で使う、顧客向けFAQ RAG のテンプレートです。
返金・解約・料金・契約条件など、高リスク質問で誤回答が起きると顧客影響が大きい領域に焦点を当てています。

## この Pack がカバーする範囲

- S1: 本番反映を止めるべき顧客向け重大誤回答。たとえば、返金不可の商品を返金可能と案内する、解約期限を誤って案内する、といったケースです。
- S2: すぐに block ではないものの、不十分または曖昧で、推奨アクションや追加確認が必要な回答です。
- Documents: refund policy、cancellation policy、pricing FAQ、terms summary を使います。

## デモの見せ方

安定した PoC 画面共有を行う場合は、まず決定論的なデモartifactを作成します。

```powershell
.\.venv\Scripts\python scripts\create_customer_support_demo_artifacts.py
.\.venv\Scripts\python -m rqg.cli serve-dashboard --workspace-dir . --runs-dir packs\customer_support_pack\reports\demo_runs --port 8012
```

そのあと、次の run を順に見せます。

1. `csp-pass-202604`: clean baseline, `policy_status=pass`, no fallback.
2. `csp-block-refund-202604`: confirmed S1 business risk, `policy_status=block`, `fallback_summary.block_origin=business_risk`.
3. `csp-needs-review-fallback-202604`: evaluator uncertainty, `policy_status=needs_human_review`, `judge_reliability=low`, `fallback_summary.block_origin=evaluator_reliability`.

`/packs`、`/runs`、`/cases/failures`、`/reports/monthly` を開くと、Pack の内容、最新 run、失敗ケース、月額Monitor の価値を説明しやすくなります。

その場で live follow-up を見せる場合は、`rqg gate --pack packs/customer_support_pack --mock --log-dir runs/customer_support_pack --reset-log-dir` のあとに、`rqg report-monthly --log-dir runs/customer_support_pack --month 2026-04` を実行します。

## 結果の読み方

- `status` は従来の機械向け契約で、`pass`、`warn`、`fail` のままです。
- `policy_status` は Proof Gate の業務判断で、`pass`、`warn`、`block`、`needs_human_review` を使います。
- 顧客向け更新を承認する前に、`fallback_summary` と `judge_reliability` を確認します。
- S1重大失敗がある場合は、失敗した回答と根拠を確認するまで本番反映しません。
- business risk による block は、評価器の信頼性が十分で、回答が S1 ケースに違反していたことを意味します。
- fallback 起因の review は、安全に出してよいと断定できないため、本番反映前に人手確認が必要であることを意味します。

## 別顧客向けに複製する場合

`rqg init-pack packs/new_customer_support --profile customer_support --force` を使い、そのあと `quality-pack.yml` の tenant metadata を更新し、文書を差し替え、初回 run 前に S1 / S2 ケースを見直します。
