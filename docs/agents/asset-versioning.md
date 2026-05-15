# Asset Versioning

## 目的

共通資産のバージョン管理とは、**いつ・誰が・なぜ・何を変えたか追える状態** にすることです。

品質判定に使う資産が履歴なしで変わると、過去の Gate Decision を説明できなくなるため、版管理を必須にする。

## バージョン管理対象

以下は共通資産として必ず version 管理する。

- Quality Pack
- Gate Policy
- case templates
- failure patterns
- report templates

## 必須ルール

- 変更時は `CHANGELOG.md` を必ず更新する
- `pack.yml` の `version` も必ず更新する
- policy 単体版を持つ場合は、その version も明示する
- 顧客提出レポートや内部報告には、使用した pack version / gate policy version / run date を残す

## 記録すべき変更情報

最低限、次を残す。

- changed_at
- changed_by
- reason
- affected assets
- backward-compatibility note
- migration note（必要時のみ）

## バージョン番号の目安

- `v0.1.0`: initial draft
- `v0.2.0`: case or pattern additions
- `v0.3.0`: policy or report improvements
- `v1.0.0`: customer-ready stable version

## 運用原則

- shared asset の silent overwrite をしない
- 顧客提出資料に、どの資産版で判定したか残す
- policy の意味変更は README だけで済ませず、CHANGELOG に残す
- 既存 contract に影響する変更は migration plan 前提で扱う
