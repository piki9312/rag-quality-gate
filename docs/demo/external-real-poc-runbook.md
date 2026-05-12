# External Real PoC Runbook

この runbook は、既存の customer-controlled または vendor-controlled な RAG API に対して、
Proof Gate を **外付け** で実行する `external_real` PoC の標準手順です。

新しい RAG 本体を作るための文書ではありません。目的は、既存 RAG API に接続する前提で、
何を確認し、どの順番で実行し、どの成果物を残し、どこで Go / No-Go を判断するかを固定することです。

関連資料:

- [External RAG Adapter Contract](../engineering/external-rag-adapter-contract.md)
- [External RAG Walkthrough](./external-rag-walkthrough.md)
- [Customer RQG Template](../../templates/customer-rqg-template/README.md)
- [Internal S1 Case Authoring Demo](./internal-s1-case-authoring.md)

> Security warning:
> `adapter_config.yml` に secret を書きません。
> token は環境変数または CI secrets のみで管理します。
> `.invalid` endpoint は placeholder なので、実運用前に顧客またはベンダーの安全な endpoint に置き換えます。

## 1. 目的

- `external_real` PoC runbook は、既存 RAG API に Proof Gate を外付けして評価するための手順です。
- 対象は `mock` / simulation ではなく、customer-controlled endpoint または vendor-controlled endpoint です。
- real evidence を出す run では `--mock` を使いません。
- 初回接続先は production write-capable endpoint ではなく、**staging / test / read-only endpoint** を推奨します。
- Proof Gate は品質保証そのものではありません。高リスク誤回答の診断・可視化・リリース判断支援のための gate です。
- PASS means the configured checks passed for the specified cases, documents, model, and settings in this run.
- PASS does not guarantee overall production safety, legal compliance, or correctness for all questions.

## 2. 前提条件

- 顧客またはベンダーが既存 RAG API を保有している
- Proof Gate からその API に HTTP POST で問い合わせ可能である
- API token は環境変数または CI secrets で管理する
- `adapter/adapter_config.yml` に live secret を書かない
- 外部 RAG API が回答と根拠 context を返せる
- `response_mapping` で少なくとも `text_path` を指定できる
- `answer_path` が取得できる
- S1 cases は human-authored / reviewed / active である
- `cases.csv` が Gate 実行の正本である
- mock 結果は顧客品質証跡ではない

## 3. 入力物

PoC 開始前に、最低限次を揃えます。

| 入力 | 用途 |
|---|---|
| `cases.csv` | Gate 実行の正本。S1 / S2 ケース定義。 |
| `gate.yml` | Pass / BLOCK 閾値。`s1_pass_rate` を弱めない。 |
| `quality-pack.yml` | Pack metadata、review owner、next action の基礎情報。 |
| `adapter/adapter_config.yml` | 外部 RAG 接続と response mapping。 |
| customer-approved documents or references | expected evidence の正当性確認に使う。 |
| S1 review artifact (if available) | S1 の human review / approval trail。 |
| secret env (`CUSTOMER_RAG_API_TOKEN` など) | bearer token や API key。 |
| endpoint URL | 実接続先。docs には `.invalid` などの placeholder を使う。 |
| contact / owner / reviewer | 実行責任者、API owner、S1 reviewer。 |
| expected evidence policy | source / text / redaction の取り扱い基準。 |
| report mode | `ci` / `redacted` / `full` の使い分け。 |
| log directory | 例: `logs/external-real` |
| index directory | 例: `indexes/external-real` |

## 4. `adapter_config.yml` 設定手順

`templates/customer-rqg-template/adapter/adapter_config.example.yml` をコピーして、
`adapter/adapter_config.yml` を作成します。

```yaml
adapter:
  type: http
  endpoint: https://rag.customer-example.invalid/rag/search
  method: POST
  timeout_seconds: 30
  auth:
    type: bearer
    token_env: CUSTOMER_RAG_API_TOKEN

request_mapping:
  question_field: question

response_mapping:
  answer_path: answer
  results_path: sources
  chunk_id_path: id
  source_path: url
  text_path: content
  score_path: score
```

上記の `.invalid` endpoint は説明用 placeholder です。live endpoint を docs に貼らず、
実際の接続先は顧客またはベンダー管理の安全な設定で差し替えます。

確認ポイント:

- `adapter.endpoint`: customer / vendor 管理の endpoint を設定する
- `adapter.method`: 現在は `POST`
- `adapter.timeout_seconds`: 初回は保守的に 30 秒前後から始める
- `adapter.auth.token_env`: live token ではなく環境変数名を書く
- `request_mapping.question_field`: 上流 API が期待する質問フィールド名
- `response_mapping.answer_path`: 回答フィールドの dot path
- `response_mapping.results_path`: retrieval results 配列の dot path
- `response_mapping.chunk_id_path`: 各 result の chunk ID
- `response_mapping.source_path`: 各 result の reviewable source
- `response_mapping.text_path`: 各 result の根拠本文。**必須**
- `response_mapping.score_path`: 各 result の retrieval score

注意事項:

- `text_path` は必須です
- `chunk_id_path` / `source_path` / `score_path` は不足しても fallback される場合があります
- `mapping_warnings` は必ずレビューしてください
- `source_path` が取れないと customer-facing な説明力が落ちます
- `answer_path` が空または欠落する場合は PoC を進めません

## 5. 実行手順

以下の順で実行します。

### A. 環境変数設定

Bash:

```bash
export CUSTOMER_RAG_API_TOKEN="replace-with-session-token"
```

PowerShell:

```powershell
$env:CUSTOMER_RAG_API_TOKEN="replace-with-session-token"
```

チェック:

- token は shell session または CI secret のみで管理する
- `.env`、docs、report に token を残さない

### B. `validate-pack`

Bash:

```bash
python -m rqg.cli validate-pack --pack . --strict-s1-governance
```

PowerShell:

```powershell
python -m rqg.cli validate-pack --pack . --strict-s1-governance
```

目的:

- `cases.csv` / `gate.yml` / `quality-pack.yml` の整合性確認
- S1 governance 確認
- active S1 に必要情報があるか確認

進行条件:

- `validate-pack` が OK
- S1 active が human-authored / reviewed / active である
- mock 由来のケースや自動生成 S1 active を正本扱いしない

### C. `validate-connection`

Bash:

```bash
python -m rqg.cli validate-connection \
  --endpoint https://rag.customer-example.invalid/rag/search \
  --query "password reset" \
  --top-k 3 \
  --api-key-env CUSTOMER_RAG_API_TOKEN \
  --output reports/connection-check.json
```

PowerShell:

```powershell
python -m rqg.cli validate-connection `
  --endpoint https://rag.customer-example.invalid/rag/search `
  --query "password reset" `
  --top-k 3 `
  --api-key-env CUSTOMER_RAG_API_TOKEN `
  --output reports/connection-check.json
```

ここでも `.invalid` endpoint は placeholder です。

目的:

- endpoint へ接続できるか
- answer / context が取れるか
- `mapping_warnings` を確認する
- secret や raw payload が出ないことを確認する

確認項目:

- `Connection: OK` または期待どおりの NG 理由
- `answer_path` / `results_path` / `text_path` の整合
- `connection-check.json` が redacted 出力であること
- endpoint、token、raw answer、raw external payload が露出していないこと

### D. `gate --adapter-config` を `--mock` なしで実行

**`--mock` を使わないこと。**

Bash:

```bash
python -m rqg.cli gate --pack . \
  --adapter-config adapter/adapter_config.yml \
  --strict-s1-governance \
  --reset-log-dir \
  --index-dir indexes/external-real \
  --log-dir logs/external-real
```

PowerShell:

```powershell
python -m rqg.cli gate --pack . `
  --adapter-config adapter/adapter_config.yml `
  --strict-s1-governance `
  --reset-log-dir `
  --index-dir indexes/external-real `
  --log-dir logs/external-real
```

customer-facing 成果物が必要な場合の追加条件:

- 初回は private / customer-controlled 環境で internal artifact を確認する
- 共有用は `--customer-facing` と `--report-mode redacted` を優先する
- `--report-mode full` は customer-controlled/private env に限定する

例:

```bash
python -m rqg.cli gate --pack . \
  --adapter-config adapter/adapter_config.yml \
  --strict-s1-governance \
  --customer-facing \
  --report-mode redacted \
  --reset-log-dir \
  --index-dir indexes/external-real \
  --log-dir logs/external-real
```

この段階で確認すること:

- 実行記録が `mock` / `simulation` ではない
- `execution_mode` が `external_real` または同等の real 外部実行として記録される
- customer-facing 成果物に simulation warning を持ち込んでいない

### E. report 確認

確認対象:

- `logs/external-real/gate-report.md`
- `logs/external-real/gate-report.json`
- `logs/external-real/gate-decision.json`
- `logs/external-real/customer-summary.md`
- `logs/external-real/run-provenance-*.json`
- `reports/connection-check.json`

見方:

- `gate-report.md`: 内部運用・診断用
- `gate-report.json`: machine-readable な bundle
- `gate-decision.json`: Go / No-Go 判定の source of truth
- `customer-summary.md`: customer-facing summary
- `run-provenance-*.json`: execution mode, hash, config provenance
- `connection-check.json`: 接続確認と redaction 確認

## 6. Customer-facing report checklist

- [ ] `execution_mode` が `mock` ではない
- [ ] real run に不要な mock / simulation warning が残っていない
- [ ] PASS の限定定義がある
- [ ] 未保証範囲が明記されている
- [ ] S1 / S2 summary がある
- [ ] `NEEDS_REVIEW` が表示される
- [ ] `policy_status` が読める
- [ ] secret / token / env name が出ていない
- [ ] raw external payload が出ていない
- [ ] private endpoint が出ていない
- [ ] redacted mode で顧客文書名 / private path が漏れていない
- [ ] S1 failure 時に BLOCK 理由が読める

## 7. Internal report checklist

- [ ] adapter diagnostics
- [ ] `mapping_warnings`
- [ ] failure taxonomy
- [ ] judge fallback
- [ ] provenance
- [ ] prompt hash
- [ ] adapter config hash
- [ ] retrieval config hash
- [ ] doc snapshot / case set version
- [ ] S1 manual review status
- [ ] gate decision reason codes
- [ ] before / after 比較がある場合は差分

## 8. Go / No-Go 判定基準

### GO

- `validate-pack` OK
- `validate-connection` OK
- `mapping_warnings` reviewed
- `gate` が `--mock` なしで完了
- `execution_mode=external_real` を確認
- customer-facing report が safe
- internal report を安全に archive 済み
- S1 manual review path が存在
- raw secret leakage がない
- PASS semantics が含まれる

### CONDITIONAL GO

- optional `source_path` / `score_path` がなくても `text_path` と evidence review が成立する
- 軽微な `mapping_warnings` が残るがレビュー済み
- S2 failures は残るが S1 pass かつ顧客が review scope を受容
- `NEEDS_REVIEW` が残るが reviewer が割り当て済み

### NO-GO

- `answer_path` が missing または empty
- `text_path` が missing または empty
- S1 governance が失敗
- S1 failure が release 判断時点で未解決
- customer-facing artifact に secret または raw payload が出る
- `execution_mode` が mock / simulation なのに real evidence 扱いされている
- customer endpoint が production write-capable または unsafe
- S1 `NEEDS_REVIEW` の reviewer がいない

## 9. S1 handling

- S1 は **1件 fail でも BLOCK** します
- `gate.yml` の `s1_pass_rate` を弱めません
- S1 を CI 通過目的で S2 へ下げません
- S1 failure 時は `case_id` / `source_doc` / `expected_answer` / `expected_evidence` を確認します
- 必要なら human review / approval trail に回します
- S1 active は自動生成しません

## 10. Security / privacy

- token は環境変数 / CI secret のみ
- `adapter_config.yml` に secret を書かない
- raw external response を保存しない
- full report は customer-controlled/private env のみ
- shared artifact は `redacted` / `ci` / `customer-facing` mode を使い分ける
- endpoint URL や private doc path を必要以上に出さない
- CodeQL / security scan の運用状態を PoC checklist に入れる

推奨の確認:

- [ ] CI secret のみで token を渡している
- [ ] shared artifact は redacted になっている
- [ ] `connection-check.json` に raw endpoint / token / payload がない
- [ ] `customer-summary.md` に private source URL が露出していない
- [ ] CodeQL / security scan が有効で、重大アラート未対応のまま PoC を進めていない

## 11. Troubleshooting

| 症状 | 対応 |
|---|---|
| Missing `answer_path` | `response_mapping.answer_path` を見直す。answer が空または欠落なら PoC を止める。 |
| Empty answer | 上流 API が空回答を返していないか、`answer_path` が誤っていないか確認する。 |
| Missing `results_path` | response の list path を `results_path` に合わせる。 |
| Missing `text_path` | `text_path` を修正する。根拠本文が取れない run は No-Go。 |
| Empty results | upstream retrieval、query、権限、staging index 状態を確認する。 |
| Missing optional `source_path` | fallback は可能だが customer-facing 説明力が下がるため、Go 判定前にレビューする。 |
| Missing optional `score_path` | fallback は可能。relevance の補助情報が減る前提でレビューする。 |
| Auth error 401/403 | token の有効性、secret 名、権限範囲、staging endpoint の ACL を確認する。 |
| Timeout | `timeout_seconds`、endpoint 健全性、top-k、network 経路を確認する。 |
| 5xx server error | vendor / customer owner へ連絡し、PoC 側では retry 前に障害切り分けを残す。 |
| S1 BLOCK | `cases.csv`、根拠文書、expected answer/evidence、manual review trail を確認する。 |
| Unsupported `notification_kind` | workflow / CI 設定を見直し、`webhook` / `slack` / `teams` のサポート値に合わせるか通知を無効化する。 |

## 12. Non-goals

この runbook でやらないこと:

- SaaS UI
- dashboard
- auth / billing
- multi-tenant
- new RAG implementation
- external adapter rewrite
- customer-specific hardcoding
- schema redesign
- asset registry
- usage log
- seen_count
- failure pattern parser
- `gen-cases` から S1 active 生成

## 推奨運用メモ

- mock / simulation の E2E 通過は onboarding の前提条件として扱い、customer evidence には使わない
- 初回 PoC は少数の human-reviewed S1 と reviewable な S2 に絞る
- 顧客共有前に internal artifact と customer-facing artifact を分けてレビューする
- Go / No-Go は `gate-decision.json` と manual review trail をセットで残す
