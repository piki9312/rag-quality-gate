# Customer Support AI Quality Pack

この pack は、Proof Gate PoC の標準テンプレートです。顧客向けFAQ RAGで誤回答が起きると影響が大きい、返金・解約・料金・契約条件・期限・資格条件を中心に確認します。

## 何を確認するか

- S1: 本番反映を止めるべき重大誤回答
- S2: すぐに止めるほどではないが、追跡・改善が必要な回答
- fallback: 評価器や検索の信頼性が落ち、人手確認が必要な状態

## 主なファイル

- `cases.csv`: 実行する高リスク質問ケース
- `template_cases.csv`: PoC case set作成用のテンプレート
- `gate.yml`: S1 pass rate、overall pass rate、evidence recall などの閾値
- `quality-pack.yml`: pack metadata、risk domain、失敗時の推奨アクション
- `documents/`: 返金、解約、料金、規約のサンプル文書
- `reports/demo_runs/`: ダッシュボードデモ用の固定artifact

## デモ実行

固定artifactで見せる場合:

```powershell
.\.venv\Scripts\python scripts\create_customer_support_demo_artifacts.py
.\.venv\Scripts\python -m rqg.cli serve-dashboard --workspace-dir . --runs-dir packs\customer_support_pack\reports\demo_runs --port 8012
```

通常のgateを実行する場合:

```powershell
.\.venv\Scripts\python -m rqg.cli gate --pack packs\customer_support_pack --mock --log-dir runs\customer_support_pack --reset-log-dir
```

## 結果の読み方

- `status`: 互換性維持の機械判定。`pass`, `warn`, `fail`
- `policy_status`: Proof Gate の業務判定。`pass`, `warn`, `block`, `needs_human_review`
- `policy_status=block`: S1重大失敗またはハード閾値違反。リリース停止。
- `policy_status=needs_human_review`: 評価器や検索の信頼性が低下。人手確認後に判断。

## 別顧客向けに複製する場合

```powershell
rqg init-pack packs/new_customer_support --profile customer_support --force
```

その後、`quality-pack.yml` の顧客情報を更新し、`documents/` と `cases.csv` を顧客文書に合わせて差し替えます。初回実行前に、S1/S2ケースと `expected_evidence` を必ずレビューしてください。
