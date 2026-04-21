# External RAG Quickstart On Localhost

このガイドは、外部 RAG endpoint をまだ持っていない状態でも、RQG から見た「外部 `/search` contract」を最短で 1 本通すための onboarding です。

最後に確認できること:

1. `serve-http-rag` で内蔵 RAG を外部 endpoint として公開できる
2. `validate-connection` で失敗系と成功系の contract を確認できる
3. `gate --dry-run` と通常 `gate` を external mode で通せる
4. `notify` と `history` が gate の後続としてつながる
5. `gate-report.json` を weekly review 用の downstream payload に変換できる
6. localhost の次段として tunnel 越しの準備に進める

## 前提

まず editable install を入れます。

```bash
pip install -e ".[dev,serve]"
```

このガイドで使うサンプル:

- documents: `packs/hr/documents`
- cases: `packs/hr/cases.csv`
- proof root: `runs/external-http-proof`

PowerShell では 2 つターミナルを使うと進めやすいです。

- Terminal A: `serve-http-rag` を起動したままにする
- Terminal B: `validate-connection -> gate --dry-run -> gate -> notify -> history -> export-weekly-review` を順番に流す

## 1. 外部 endpoint を localhost で立てる

Terminal A:

```powershell
$env:RQG_LOCAL_RAG_KEY='demo-secret'
rqg serve-http-rag `
  --docs-dir packs/hr/documents `
  --index-dir runs/external-http-proof/index `
  --host 127.0.0.1 `
  --port 8011 `
  --api-key-env RQG_LOCAL_RAG_KEY
```

使う endpoint:

- search: `http://127.0.0.1:8011/search`
- health: `http://127.0.0.1:8011/health`
- notify sink: `http://127.0.0.1:8011/notify`
- notify events: `http://127.0.0.1:8011/notify/events`

期待結果:

- `/health` が `ok: true` を返す
- `chunk_count` と `ingested_files` が 1 以上になる

## 2. まず失敗系の contract を確認する

Terminal B:

```powershell
rqg validate-connection `
  --endpoint http://127.0.0.1:8011/search `
  --query "paid leave" `
  --top-k 3 `
  --output runs/external-http-proof/connection-auth-error.json
```

Bearer token を付けていないので、ここは失敗するのが正しい挙動です。`auth_error` を先に確認しておくと、外部 contract の境界が曖昧になりません。

## 3. validate-connection 正常系を通す

```powershell
rqg validate-connection `
  --endpoint http://127.0.0.1:8011/search `
  --query "paid leave" `
  --top-k 3 `
  --api-key-env RQG_LOCAL_RAG_KEY `
  --output runs/external-http-proof/connection-validation.json
```

期待結果:

- `Connection: OK`
- `Chunks: 1+`
- source として HR 文書名が返る

## 4. notify つき config を用意する

`runs/external-http-proof/rqg-local-external.yml`:

```yaml
notifications:
  - type: webhook
    webhook_url: http://127.0.0.1:8011/notify
    notify_on: [fail, warn, pass]
```

この設定で、通常 gate の結果を localhost の sink に戻せます。

## 5. gate dry-run を external mode で通す

```powershell
rqg gate packs/hr/cases.csv `
  --mock `
  --rag-endpoint http://127.0.0.1:8011/search `
  --rag-api-key-env RQG_LOCAL_RAG_KEY `
  --log-dir runs/external-http-proof/gate `
  --config runs/external-http-proof/rqg-local-external.yml `
  --quality-pack packs/hr/quality-pack.yml `
  --dry-run
```

dry-run で見るポイント:

- isolated log dir が `runs/external-http-proof/gate/dry-run/...` に作られる
- gate 自体は PASS/WARN/FAIL まで評価される
- 通知は送られない
- `gate-decisions.jsonl` には append されない

## 6. 通常 gate を流す

```powershell
rqg gate packs/hr/cases.csv `
  --mock `
  --rag-endpoint http://127.0.0.1:8011/search `
  --rag-api-key-env RQG_LOCAL_RAG_KEY `
  --log-dir runs/external-http-proof/gate `
  --config runs/external-http-proof/rqg-local-external.yml `
  --quality-pack packs/hr/quality-pack.yml `
  --reset-log-dir
```

ここで `gate-report.json` が downstream の基準成果物になります。通常 gate の後には次のファイルが残ります。

- `runs/external-http-proof/gate/gate-report.md`
- `runs/external-http-proof/gate/gate-decision.json`
- `runs/external-http-proof/gate/gate-report.json`
- `runs/external-http-proof/gate/gate-history-summary.json`
- `runs/external-http-proof/gate/gate-decisions.jsonl`

## 7. notify 着弾を確認する

```powershell
curl http://127.0.0.1:8011/notify/events
```

期待結果:

- `count: 1+`
- payload に `event: rqg.gate_decision` が入る
- payload に `status`, `run_id`, `report_path`, `decision_path` が入る

## 8. history を確認する

```powershell
rqg history --log-dir runs/external-http-proof/gate --last 5 --compare-offset 1 --trend-window 5
```

期待結果:

- `Entries: 1+`
- 最新 run の status が読める
- trend summary が出る

## 9. gate-report.json を weekly review payload に変換する

`gate-report.json` は downstream consumer 向けの single bundle です。ここから weekly review issue payload を 1 コマンドで作れます。

downstream consumer が安定して参照するフィールド:

- `schema_version`: bundle schema version。現在は `1.0`
- `bundle_type`: `rqg.gate_report_bundle`
- `contract`: contract name, version, stable fields, compatibility rule
- `run`: `run_id`, `status`, `created_at` の軽量 summary
- `decision`: gate 判定の machine-readable 本体
- `history_summary`: recent history / stale / uncovered category の運用 summary
- `report_markdown`: 人が読む gate report
- `artifact_paths`: 同じ run で生成された artifact path

互換性方針:

- minor change は additive とし、既存 stable field の意味を壊さない
- downstream はまず `bundle_type` と `schema_version` を確認する
- weekly review, GitHub issue, Slack 要約などの後続連携は `decision` と `history_summary` を主に読む
- `report_markdown` は表示用であり、判定ロジックの入力にはしない

```powershell
rqg export-weekly-review `
  --bundle-file runs/external-http-proof/gate/gate-report.json `
  --output runs/external-http-proof/gate/weekly-review-issue.json
```

期待結果:

- `weekly-review-issue.json` が生成される
- title / body / labels / summary が入る
- `summary.latest_status`, `summary.latest_run_id`, `summary.week_start` が downstream でそのまま使える

この 1 ファイルがあれば、GitHub issue 作成、Slack 要約生成、週次レビュー会議資料への転記を分岐しやすくなります。

## 10. localhost の次は tunnel 越しで 1 段進める

localhost proof の次に軽いのは HTTPS tunnel です。RQG 側の使い方は変えず、endpoint だけ public URL に置き換えます。

例: `cloudflared` を使う場合

```powershell
cloudflared tunnel --url http://127.0.0.1:8011
```

発行された HTTPS URL が `https://<random>.trycloudflare.com` なら、次の 2 本を先に流します。

```powershell
rqg validate-connection `
  --endpoint https://<random>.trycloudflare.com/search `
  --query "paid leave" `
  --top-k 3 `
  --api-key-env RQG_LOCAL_RAG_KEY

rqg gate packs/hr/cases.csv `
  --mock `
  --rag-endpoint https://<random>.trycloudflare.com/search `
  --rag-api-key-env RQG_LOCAL_RAG_KEY `
  --log-dir runs/external-http-proof/tunnel-gate `
  --config runs/external-http-proof/rqg-local-external.yml `
  --quality-pack packs/hr/quality-pack.yml `
  --dry-run
```

ここまで通れば、localhost 専用の証明ではなく「外から見える HTTPS endpoint 契約」として次段に進めます。

## 完了条件

次の 6 点がそろえば、「外部 contract で 1 本通り、その結果を downstream に流せる」と判断してよい状態です。

1. `validate-connection` の失敗系で `auth_error` を確認した
2. `validate-connection` の成功系が OK になった
3. `rqg gate --dry-run` が external endpoint 経由で通った
4. 通常 `rqg gate` の通知 payload が notify sink に入った
5. `rqg history` が append 済み履歴を読めた
6. `gate-report.json` から weekly review payload を生成できた
