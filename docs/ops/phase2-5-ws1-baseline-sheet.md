# Phase2.5 WS1 Baseline Measurement Sheet

WS1 (Onboarding/Ops bottleneck reduction) の baseline 計測を、同じ条件で再現できるようにするための記録シートです。

## 1. Measurement Scope (fixed)

- 対象: sample repo への導入（基準: packs/hr）
- 判定対象外: 既存顧客 repo への組み込み
- 計測除外: 初回ケース設計・ケース追加の作業時間

## 2. Time Window Definition (fixed)

- 初回導入時間:
  - 開始: 手順開始
  - 終了: 初回 gate 実行結果の確認完了
- 週次運用時間:
  - 開始: 週次更新開始
  - 終了: 週次レポート確認完了

## 3. Measurement Procedure

1. 対象リポジトリが sample repo 条件を満たすことを確認する。
2. 計測除外作業（ケース設計・追加）を先に完了する。
3. 上記 time window 定義に従って開始/終了時刻を記録する。
4. 所要時間（分）を算出し、evidence に run URL またはログを残す。

## 4. Baseline Log

| measured_date | operator | sample_repo | onboarding_start | onboarding_end | onboarding_time_minutes | weekly_ops_start | weekly_ops_end | weekly_ops_time_minutes | evidence | notes |
| --- | --- | --- | --- | --- | ---: | --- | --- | ---: | --- | --- |
| YYYY-MM-DD | owner-name | packs/hr | YYYY-MM-DD hh:mm | YYYY-MM-DD hh:mm | 0 | YYYY-MM-DD hh:mm | YYYY-MM-DD hh:mm | 0 | run URL / log path | condition notes |

## 5. Target Reference

- 初回導入: 30分以内
- 週次運用: 15分以内

Target は baseline の後に改善傾向で判断し、単発値だけでは判定しない。