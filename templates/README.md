# 共通テンプレート

このディレクトリは、pack や導入時に再利用するテンプレートをまとめる場所です。

## 置くもの

- sample pack
- customer onboarding template
- GitHub 用テンプレート
- `change-event.example.yml` のような安全な入力サンプル
- 汎用 policy / questionnaire / report の雛形

## 置かないもの

- 顧客の実文書
- 顧客固有ケースの原本
- 未匿名レポート

既存テンプレートは `sample_pack/`、`customer-rqg-template/`、`github/` を起点にし、個社事情はここへ直接混ぜないでください。

`change-event.example.yml` は、FAQ / 規約 / 料金表 / プロンプト / モデル / retrieval 設定の変更を release review に渡すための安全サンプルです。顧客名、実在文書名、絶対パス、内部 release 名は入れず、bounded な ID、version、hash、category だけで表現してください。
