# Assetization Policy

## 基本方針

PoC、診断案件、改善案件から得た学びは、案件終了後に共通資産へ変換する。
ただし、資産化するのは顧客文書そのものではなく、**抽象化された失敗パターン・テスト観点・判定ルール** である。

## 何を資産化するか

以下は共通資産化の対象にする。

- failure patterns
- case templates
- gate policies
- quality packs
- report templates
- intake sheets
- improvement playbooks
- adapter configs

## 資産化の判断基準

共通資産に入れるのは、以下を満たすものに限る。

- 顧客名や固有文書に依存しない
- 別案件でも再利用できる
- 匿名化・抽象化されている
- 説明責任のある判定ルールとして残せる
- repo に置いても機密性の問題がない

## 抽象化の単位

資産化の単位は、文書本文ではなく次のような再利用可能要素にする。

- どの業務でどんな failure が起きるか
- どの質問形式が高リスクか
- どの evidence が必要か
- どの条件で BLOCK / REVIEW にするか
- 顧客説明で何をレポートへ載せるべきか

## 資産化してはいけないもの

- 顧客の実文書
- 契約書や社内規程の原本
- 顧客名
- 個人情報
- API キー
- 実際の問い合わせログ
- 未匿名の顧客レポート
- 個社事情が残った case や playbook

## 案件終了後の運用

- すべての PoC / 診断案件で資産化レビューを行う
- レビューでは、再利用可能な failure pattern、case template、policy 変更点、レポート改善点を抽出する
- 抽出結果は repo へ入れる前に匿名化・抽象化・重複整理を行う
- reusable でない内容は repo に入れず、案件側の保管先に残す
