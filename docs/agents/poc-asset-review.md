# PoC Asset Review

## 目的

PoC 終了後に、案件成果を単発受託で終わらせず、共通資産へ変換できる要素をレビューする。

## 実施方針

- すべての PoC / 診断案件の終了後に実施する
- client-specific data と shared asset 候補を分けて確認する
- 抽出内容は、匿名化・抽象化したうえで repo 反映可否を判断する

## レビュー観点

- どの failure pattern が再利用できるか
- どの case template が別案件でも使えるか
- Gate Policy にどんな修正が必要か
- report template にどんな改善が必要か
- 手作業のうち何を automation 候補にできるか
- monthly operation 需要が見えたか

## テンプレート

```text
project name:
target domain:
target documents:
number of cases:
number of S1 cases:
number of gate runs:
number of BLOCK decisions:
customer's main concern:
sales message that worked:
sales message that did not work:
reusable failure patterns:
new case templates:
gate policy changes:
report template improvements:
manual work to automate:
potential monthly operation needs:
next actions:
```

## レビュー後の扱い

- shared asset にできるものは packs / templates / docs / examples へ戻す
- 個社事情が残るものは Notion または顧客別Driveに留める
- repo へ反映する際は stable ID、version、CHANGELOG を忘れない
