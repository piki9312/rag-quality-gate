# CI / Release Gate Policy

## Purpose

Proof Gate の CI と Release Gate 運用方針を定義する。
目的は、顧客データ・API キー・外部 RAG 環境を安全に扱いながら、mock / local docs / external RAG の Gate を使い分けること。

## Default CI Policy

- 開発 repo の通常 CI では mock / demo / local docs を標準とする
- PR では外部 RAG や顧客本番 API を原則叩かない
- unit tests, pack validation, mock gate, report generation を中心に検証する
- 顧客固有 secrets がなくても通る CI を維持する

## External RAG Gate Policy

- 外部 RAG 接続は明示的な workflow でのみ行う
- 初期は `workflow_dispatch` による手動実行を基本とする
- `run_connection_validation` を有効にしてから Gate を実行する
- 本番 endpoint ではなく staging / test / read-only endpoint を優先する
- 外部接続に失敗した場合は Gate 本体を走らせない

## Secrets Policy

- API key や endpoint は GitHub Actions Secrets に保存する
- repo ファイル、Notion、Slack、メール本文、Issue、PR コメントに secret を書かない
- endpoint も初期は secret 扱いにする
- secret 名には顧客名ではなく顧客 ID を使う

推奨命名:

- `CL_001_RAG_API_ENDPOINT`
- `CL_001_RAG_API_KEY`
- `CL_001_SLACK_WEBHOOK_URL`

workflow での参照例:

- `${{ secrets.CL_001_RAG_API_ENDPOINT }}`
- `${{ secrets.CL_001_RAG_API_KEY }}`

## Repository Separation

- `rag-quality-gate` repo はプロダクト開発 repo であり、顧客固有データを入れない
- 顧客 PoC を自社側で回す場合は、別の private repo を作ることを推奨する
- 例:
  - `rag-quality-gate`: product source, demo packs, docs, templates
  - `proofgate-client-ops-private`: client-specific cases, run configs, client reports
- 顧客固有 cases や reports を開発 repo に混ぜない

## Client PoC Operation

- 初期 PoC では顧客の本番 API に直接つながない
- 優先順:
  1. mock / local docs で検証
  2. 顧客の検証用 RAG API に手動接続
  3. 顧客 repo で顧客自身が secrets 管理して実行
- PoC 終了後は secret を削除または顧客側でローテーションしてもらう

## Workflow Types

### `rqg-gate-mock.yml`

- PR や通常 CI で使う
- mock / local docs 用
- secrets 不要または通知 secret のみ

### `rqg-gate-external.yml`

- 外部 RAG 接続用
- `RAG_API_ENDPOINT` / `RAG_API_KEY` が必要
- 初期は `workflow_dispatch` 中心

### `rqg-gate-external-notify.yml`

- 外部 Gate + Slack 通知用

### `rqg-gate-weekly-review.yml`

- 定期レビューや運用レポート向け

## Do / Do not

### Do

- keep mock CI runnable without client secrets
- use workflow_dispatch for early external RAG gates
- use staging/read-only endpoints
- delete or rotate secrets after PoC
- keep gate artifacts free from secrets
- record pack version and gate policy version in reports

### Do not

- commit API keys
- print secrets in logs
- run external RAG calls automatically on every PR during early PoC
- use production endpoints unless explicitly approved
- mix client-specific data into shared packs
- store raw customer documents in the product repo

## Example Workflow

顧客 ID `CL_001` の初期外部 Gate は次の流れを基本にする。

1. `templates/github/rqg-gate-external.yml` を private repo 側 workflow のたたき台にする
2. trigger はまず `workflow_dispatch` のみ、または `pull_request` を無効化した状態で使う
3. Secrets に以下を登録する
   - `CL_001_RAG_API_ENDPOINT`
   - `CL_001_RAG_API_KEY`
4. workflow 内で `rag_api_endpoint` / `rag_api_key` へ secrets をマッピングする
5. `run_connection_validation: true` を維持し、接続確認が通った場合のみ Gate を進める
6. 接続先は顧客本番ではなく、staging / test / read-only endpoint を使う
7. PoC 終了後は secret を削除するか、顧客側でローテーションする

短い例:

```yaml
on:
  workflow_dispatch:

jobs:
  rqg-gate:
    uses: ./.github/workflows/rqg-reusable-gate.yml
    with:
      run_pack_validation: true
      run_connection_validation: true
    secrets:
      rag_api_endpoint: ${{ secrets.CL_001_RAG_API_ENDPOINT }}
      rag_api_key: ${{ secrets.CL_001_RAG_API_KEY }}
```

## Existing Template Relationship

- repo 標準 CI は `.github/workflows/ci.yml` と `.github/workflows/rqg-gate-mock.yml` を基準に、mock / local docs で安全に回す
- 外部接続は `templates/github/rqg-gate-external.yml` と `templates/github/rqg-gate-external-notify.yml` を caller 例として提供する
- 定期運用や follow-up は `templates/github/rqg-gate-weekly-review.yml` を参照する
- reusable contract の中心は `.github/workflows/rqg-reusable-gate.yml` にある
