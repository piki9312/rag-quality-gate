# Data Management Policy

## Current Terminology Note

In current Proof Gate design, `case templates` in shared assets means reusable Case Intent / Question Variation / Expected Behavior Template assets. It does not mean customer-specific answer-key cases.

Customer-specific `expected_answer`, customer-specific `expected_behavior`, raw question, raw answer, and raw evidence are client-specific full/private data by default. They should remain in vendor-controlled or customer-controlled environments unless a separate agreement explicitly permits sharing.

## データ分類

Proof Gate の内部運用では、データを次の 3 区分で扱う。

| 区分 | 例 | 保存先方針 |
| --- | --- | --- |
| client-specific data | 顧客文書、契約書、顧客名、個人情報、実ログ、未匿名レポート、秘密情報 | 顧客別Drive または顧客ごとに合意した安全な保管先。repo へ入れない |
| shared assets | 匿名化済み Quality Pack、failure patterns、case templates、gate policies、report templates、demo data | repo で管理する |
| business / operation knowledge | 商談メモ、案件学び、営業メッセージ、運用ナレッジ、顧客温度感 | Notion で管理する |

## 保存先の役割分担

### Repo

repo には次だけを置く。

- 匿名化・抽象化された共通資産
- 仕様書
- テンプレート
- デモデータ
- 再利用前提の adapter / policy / pack 定義

repo に置いてはいけないもの:

- 顧客の実文書
- 顧客名
- 個人情報
- API キーや secrets
- 実際の問い合わせログ
- 未匿名の顧客提出レポート

### Notion

Notion では、事業運営や案件推進の知識を管理する。

- 営業仮説
- 商談で刺さったメッセージ
- 運用上の学び
- monthly operation の要求整理
- プロダクト化前の論点メモ

### 顧客別Drive

顧客別Drive では、案件ごとの原本と作業中データを管理する。

- 顧客文書
- 顧客専用ケース
- 中間レポート
- 実ログ
- 契約関連資料
- 削除対象を含む一時成果物

## 運用ルール

- client-specific data は repo に入れない
- shared assets は repo を source of truth にする
- business / operation knowledge は Notion を source of truth にする
- 顧客別Drive は案件単位の実務保管先とし、共通資産の正本にはしない
- repo に移す前に、必ず匿名化・抽象化・権限確認を行う
