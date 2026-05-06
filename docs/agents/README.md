# Agent Docs Entry

このフォルダは、Proof Gate 事業における共通資産・データ管理・Quality Pack・バージョン管理の内部方針を、開発エージェントと共同開発者向けにまとめた入口です。

## 先に理解すること

- Proof Gate の主役は **RAG構築そのものではなく、品質保証 / Release Gate** です。
- RAG構築支援は、初期導入や PoC 価値提示のための補助線です。
- repo に入れるのは、匿名化・抽象化された共通資産、仕様、テンプレート、デモデータのみです。

## 最初に読む順番

1. [business-context.md](business-context.md)
2. [data-management-policy.md](data-management-policy.md)
3. [assetization-policy.md](assetization-policy.md)
4. [quality-pack-spec.md](quality-pack-spec.md)
5. [asset-versioning.md](asset-versioning.md)
6. [poc-asset-review.md](poc-asset-review.md)
7. [repository-rules.md](repository-rules.md)

## 各ファイルの役割

- `business-context.md`: 事業背景と差別化の軸
- `data-management-policy.md`: repo / Notion / 顧客別Drive の役割分担
- `assetization-policy.md`: PoCや診断案件から何を共通資産化するか
- `quality-pack-spec.md`: 再利用可能な Quality Pack の共通仕様
- `asset-versioning.md`: 資産変更の追跡・版管理ルール
- `poc-asset-review.md`: 案件終了後の資産化レビュー手順
- `repository-rules.md`: repo に置いてよいもの / 置いてはいけないもの

## 他ドキュメントとの関係

- docs 全体の案内: [../README.md](../README.md)
- 製品概要: [../../README.md](../../README.md)
- 固定方針の ADR:
  - [ADR 0002](../adr/0002-product-charter-and-development-priorities.md)
  - [ADR 0005](../adr/0005-quality-asset-governance.md)
  - [ADR 0008](../adr/0008-rqg-scope-and-non-goals.md)

## 読み方の原則

- 実装判断より先に、資産境界とデータ境界を確認する
- 顧客固有情報を共通資産へ混ぜない
- 既存の CLI / report / adapter 契約を壊す変更は、別途 migration plan を前提に扱う
