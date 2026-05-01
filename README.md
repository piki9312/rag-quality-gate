# Proof Gate

Proof Gate は、RAG や LLM を用いた業務AIに対して、重大な誤回答、品質劣化、外部送信リスクを検知し、必要に応じて遮断・人手確認・記録を行う品質保証基盤です。

現時点の提供形態は SaaS ではなく、CLI、Quality Pack、外部RAG adapter、Markdown/JSONレポートを中心にした PoC/運用支援です。RAGエンジンそのものを置き換えるのではなく、既存または新規の RAG/FAQ AI の外側に品質ゲートを置きます。

## 解決する課題

RAG AI は、FAQ・規約・料金表・社内ルールが変わった後も、古い条件で自然に答えてしまうことがあります。特に返金、解約、料金、契約条件、期限、資格条件の誤回答は、顧客対応事故や社内説明責任につながります。

Proof Gate は、こうした高リスク質問を `cases.csv` として管理し、RAG AI の回答をリリース前または定期運用で再チェックします。

- S1重大失敗を検知したら `policy_status=block`
- 評価器や検索の信頼性が落ちたら `policy_status=needs_human_review`
- 結果を `gate-report.md`、`gate-decision.json`、`gate-report.json` に記録
- 月額Monitorで品質劣化や未解決リスクを継続確認

## 2つの導入パターン

### A軸: RAG未導入企業向け

**Proof Gate付き RAG AI導入診断PoC**

自社FAQ・規約・料金表を使って、簡易RAG体験と高リスク回答の品質診断を同時に行います。PoC後は、安全化した本格RAG構築と Proof Gate Monitor へ進みます。

### B軸: 既存RAGあり企業向け

**既存RAG品質診断PoC**

既存RAG APIに Proof Gate を接続し、返金・解約・料金・契約条件などの高リスク質問で品質診断を行います。PoC後は、改善支援と Proof Gate Monitor へ進みます。

## 最短の営業デモ

FAQ が v1 から v2 に変わった後も、AI が古い条件で答える変更事故を before / after で見せます。

```powershell
.\.venv\Scripts\python -m pip install -e ".[dev]"
.\.venv\Scripts\python scripts\create_customer_support_faq_change_sales_demo.py
```

見るファイル:

- `demos/customer_support_faq_change/reports/before_stale_v1/gate-report.md`
- `demos/customer_support_faq_change/reports/after_v2_reference/gate-report.md`
- `demos/customer_support_faq_change/before_after_onepager.md`
- `demos/customer_support_faq_change/demo_summary.json`

期待する見せ方:

- before: `NG`, `policy_status=BLOCK`
- after: `要確認`, `policy_status=NEEDS_HUMAN_REVIEW`
- after は S1 pass rate 100%、S1重大失敗 0件
- ローカルfallbackがある場合は、人手確認が必要な運用品質リスクとして説明
- 月額Monitorで継続監視する理由につなげる

## ダッシュボードデモ

固定デモ artifact を作って、最小ダッシュボードで PASS / BLOCK / NEEDS_HUMAN_REVIEW を見せます。

```powershell
.\.venv\Scripts\python scripts\create_customer_support_demo_artifacts.py
.\.venv\Scripts\python -m rqg.cli serve-dashboard --workspace-dir . --runs-dir packs\customer_support_pack\reports\demo_runs --port 8012
```

開くURL:

- `http://127.0.0.1:8012/packs`
- `http://127.0.0.1:8012/runs`
- `http://127.0.0.1:8012/cases/failures`
- `http://127.0.0.1:8012/reports/monthly`

## 通常の gate 実行

```powershell
.\.venv\Scripts\python -m rqg.cli gate --pack packs\customer_support_pack --mock --log-dir runs\customer_support_pack --reset-log-dir
```

出力:

- `runs/customer_support_pack/gate-report.md`
- `runs/customer_support_pack/gate-decision.json`
- `runs/customer_support_pack/gate-report.json`
- `runs/customer_support_pack/gate-decisions.jsonl`

## PoC資料

- [Proof Gate PoCガイド](docs/user-guide/proof-gate-poc.md)
- [営業デモ手順](demos/customer_support_faq_change/README.md)
- [A軸/B軸 PoC提案1枚](docs/sales/proof-gate-poc-offer.md)
- [Customer Support AI Quality Pack](packs/customer_support_pack/README.md)
- [既存RAG接続ガイド](docs/demo/external-rag-walkthrough.md)
- [Windows PowerShellガイド](docs/user-guide/windows-powershell.md)

## 今はやらないこと

Proof Gate は、当面は CLI、Quality Pack、外部RAG adapter、レポートを中心に整備します。SaaS、認証、課金、マルチテナント、重い管理画面は、顧客PoCで繰り返し価値が確認できるまで後回しにします。
