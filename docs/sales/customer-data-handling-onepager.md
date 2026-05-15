# 顧客データ取扱い説明

## 基本方針

Proof Gate の営業デモと公開CIでは、sample、mock、dummy、aggregate metadata のみを扱います。顧客データをそのままGitHub Actionsに載せる前提にはしません。

## PoCで扱うデータ

| 区分 | 扱い |
|---|---|
| サンプルFAQ・モック回答 | 営業デモ、公開CI、公開artifactで利用可能 |
| 顧客FAQ・規約・料金表 | PoC前に保存場所、外部送信有無、アクセス範囲、削除方法を合意 |
| 高リスク質問ケース | 顧客文書を要約して作成。必要に応じて匿名化 |
| 評価結果 | 顧客提出版は集計と要約中心。詳細ログは別紙扱い |

## GitHub Actions / artifacts / logs に載せないもの

- APIキー、アクセストークン、認証情報
- 顧客の非公開文書全文
- 顧客固有の問い合わせ本文、期待回答、AI回答、検索根拠本文
- raw JSONL、full gate report、FAISS index、FAISS meta raw payload
- 接続検証時のraw HTTP payload
- ローカル絶対パス、CI workspace path、一時作業ディレクトリ名、内部ディレクトリ構造

## 顧客提出レポートに含めるもの

- 本番反映可否
- `policy_status` とその意味
- 重大失敗件数、S1 pass rate、overall pass rate
- 重大リスクの領域別要約
- 改善事項と次の推奨
- 月次Monitorで継続確認すべき領域

## 顧客提出レポートに含めないもの

- APIキー、顧客文書全文、問い合わせ全文、AI回答全文
- retrieved evidence本文
- raw JSONL、検索index、debug用full report
- 開発者PCやCIの内部パス

## 本格運用時の選択肢

本格運用では、顧客環境、private runner、顧客管理のobject storage、閉域または制限付きネットワーク、既存監査ログ基盤との接続を前提に設計します。

Proof Gate はRAG本体の代替ではありません。RAG AIを安全に変更・運用するための品質ゲートとして、必要な証跡だけを残し、顧客データ露出を最小化します。
