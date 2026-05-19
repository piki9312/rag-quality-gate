# Release Review Demo Pack

この demo pack は 5 分で Proof Gate の変更後リリースレビュー価値を説明するための再現用セットです。

題材は架空の SaaS である OrbitDesk の料金と返金と解約 FAQ 変更事故です。`docs/demo/` には v1 と v2 の差分文書を置き、`packs/release_review_demo/documents/` には意図的に v1 のままの current corpus を置いています。つまり `change-event.yml` は v2 更新を示す一方で、評価対象の RAG corpus は旧情報を参照し続ける想定です。

## この demo で見せること

- FAQ と料金表と規約を変えたのに RAG corpus が旧文書を参照すると No-Go になる
- `change-event.yml` を渡すと Change Event Card と Report Preview の Change Summary が埋まる
- 返金と解約の S1 failure が Major Failures と Decision Card に出る
- Document Corpus Card で現在の corpus 証跡を確認できる
- Production Readiness Card で `not_ready` を示せる

## 変更元文書

- [docs/demo/pricing_policy_v1.md](../../docs/demo/pricing_policy_v1.md)
- [docs/demo/pricing_policy_v2.md](../../docs/demo/pricing_policy_v2.md)
- [docs/demo/refund_policy_v1.md](../../docs/demo/refund_policy_v1.md)
- [docs/demo/refund_policy_v2.md](../../docs/demo/refund_policy_v2.md)
- [docs/demo/cancellation_policy_v1.md](../../docs/demo/cancellation_policy_v1.md)
- [docs/demo/cancellation_policy_v2.md](../../docs/demo/cancellation_policy_v2.md)

## 実行手順

1. change-event.yml を書く
   - この pack には安全な [packs/release_review_demo/change-event.yml](change-event.yml) を同梱しています。
   - raw path と `target_release` と顧客名は入れていません。

2. Pack を確認する

```powershell
.\.venv\Scripts\python -m rqg.cli validate-pack --pack packs\release_review_demo --strict-s1-governance
```

3. rqg gate --change-event change-event.yml を実行する

```powershell
.\.venv\Scripts\python -m rqg.cli gate --pack packs\release_review_demo --mock --change-event packs\release_review_demo\change-event.yml --index-dir index\release_review_demo --log-dir demo_runs\release_review_demo --reset-log-dir
```

4. dashboard を起動する

```powershell
.\.venv\Scripts\python -m rqg.cli serve-dashboard --workspace-dir . --runs-dir demo_runs\release_review_demo --port 8012
```

5. `/runs` を開いて最新 run を選ぶ

6. Run Detail で次を順に見る
   - Change Event Card
   - Decision Card
   - Major Failures
   - Document Corpus Card
   - Production Readiness Card

7. `Report Preview` を開く
   - Change Summary
   - Production Readiness

## 期待される見え方

- Decision は `No-Go`
- `policy_status` は `block`
- Production Readiness は `not_ready`
- 返金と解約の S1 failure が `Critical` または `High` で出る
- Document Corpus Card に `pricing_policy.md` と `refund_policy.md` と `cancellation_policy.md` が出る
- Report Preview に Change Summary と Production Readiness が出る

## safe / full 境界

- この demo の文書と change-event はすべて架空です。
- CI-safe artifact に raw path や顧客名を出しません。
- full metadata は local / private / customer-controlled 前提です。
- `change-event.yml` は bounded な名前と hash だけを使っています。