# Vendor Review Guide

## 1. 概要

Proof Gate は、顧客固有の正式な `expected_answer` を自動確定しません。`gen-cases` や PatternDraft が生成する case は、Gate 実行用の正式ケースではなく、ベンダーが確認するための draft case です。

Proof Gate の役割は、業務上チェックすべき観点や失敗パターンをもとに、レビューしやすい候補を提示することです。顧客文書、業務ルール、運用上の正しさを確認し、正式に採用するかどうかを決める責任はベンダー側にあります。

承認された case だけが `status=active` になり、Gate 実行対象になります。AI が生成しただけの case や、未確認の `expected_answer` を含む case を `active` にしてはいけません。

## 2. 全体フロー

```text
cases_draft.csv
  ↓ export-case-review
review_cases.yaml / review_cases.md
  ↓ vendor review
approve-cases
  ↓
cases.csv
  ↓
rqg gate
```

標準的な流れは次の通りです。

1. `cases_draft.csv` を作成します。
2. `rqg export-case-review` で `review_cases.yaml` と `review_cases.md` を生成します。
3. ベンダーが `review_cases.yaml` を編集します。
4. `rqg approve-cases` で承認済み case を `cases.csv` に反映します。
5. `rqg gate` は `status=active` の case だけを実行対象にします。

`review_cases.md` は人間が読みやすい preview です。編集元の正本は `review_cases.yaml` です。

## 3. `review_cases.yaml` の見方

`review_cases.yaml` は、ベンダーが編集するレビュー正本です。主な field は次の意味を持ちます。

| field | 意味 |
| --- | --- |
| `case_id` | draft case を一意に識別する ID |
| `decision` | ベンダーの判断。`pending` / `approve` / `reject` |
| `status` | 現在の状態。draft は通常 `needs_review` |
| `suggestion` | Proof Gate が提示した候補情報 |
| `vendor_review` | ベンダーが確認・入力する正式レビュー情報 |
| `expected_answer` | ベンダーが確認した期待回答 |
| `expected_evidence` | 回答を支える文書、セクション、chunk などの根拠 |
| `expected_keywords` | 回答に含まれるべき重要語句 |
| `severity` | `S1` / `S2` の重大度 |
| `eval_mode` | 評価方法。例: `exact`, `evidence_keyword`, `grounded_judge` |
| `reviewed_by` | レビュー担当者 |
| `reviewed_at` | レビュー日時 |
| `notes` | 判断理由、補足、注意点 |

`suggestion` は参考情報です。`vendor_review` に入力された値が、`approve-cases` 後の `cases.csv` に反映されます。

## 4. `decision` の意味

| decision | 意味 | `approve-cases` 後 |
| --- | --- | --- |
| `pending` | まだ承認しない | `needs_review` |
| `approve` | Gate 対象として承認 | `active` |
| `reject` | 不採用 | `deprecated` |

判断に迷う場合は `pending` のままにしてください。`approve` は、Gate 実行対象にしてよいと説明できる場合だけ使います。

## 5. `expected_answer` の確認方法

generated `expected_answer` は正式正解ではありません。AI や Proof Gate が作った文章を、そのまま顧客承認済みの回答として扱ってはいけません。

確認時は次を見てください。

- 顧客文書や業務ルールと一致しているか
- 質問に対して過不足なく答えているか
- 誤解を招く表現、断定しすぎる表現、古いルールが含まれていないか
- 顧客に提出しても問題ない表現になっているか

不明な場合は `decision: pending` にしてください。明らかに誤っている場合は、修正してから `approve` するか、`decision: reject` にします。

## 6. `expected_evidence` の確認方法

`expected_evidence` は、回答の根拠になる文書、セクション、chunk を示します。Gate は、回答が根拠に基づいているかを確認するためにこの情報を使います。

確認時は次を見てください。

- 回答に必要な根拠が含まれているか
- 文書やセクションの参照が正しいか
- `expected_answer` と根拠が矛盾していないか
- 根拠が古い文書や対象外文書を指していないか

根拠が曖昧な場合は `pending` にしてください。根拠が誤っている場合は、正しい値へ修正するか `reject` にします。

## 7. `severity` の決め方

`severity` は原則 `S1` / `S2` のみを使います。

| severity | 目安 |
| --- | --- |
| `S1` | 重大。失敗した場合に block 相当で扱うべき case |
| `S2` | 通常の重要 case。品質劣化や回答ズレを検知する case |

`severity_hint` は参考値であり、最終判断ではありません。顧客業務上のリスク、誤回答時の影響、リリース判定への重みを踏まえてベンダーが確定してください。

`S3` / `S4` / `high` / `critical` / `unknown` などの未対応値は使わないでください。判断が難しい場合は `decision: pending` にして、レビューを継続します。

## 8. `eval_mode` の選び方

既存の `cases.csv` では、主に次の `eval_mode` を使います。

| eval_mode | 使う場面 |
| --- | --- |
| `exact` | `expected_answer` と照合する必要がある case |
| `evidence_keyword` | 根拠と重要語句の両方を確認したい case |
| `grounded_judge` | 回答が根拠に基づいているかを judge で確認したい case |

迷う場合は、まず `expected_answer`, `expected_evidence`, `expected_keywords` のどれを品質ゲートで必ず見たいかを決めてください。評価条件が曖昧なまま `approve` しないでください。

## 9. `active` にしてよい条件

`decision: approve` にする前に、少なくとも次を確認してください。

- `expected_answer` をベンダーが確認した
- `expected_evidence` が妥当で、回答を支えている
- `severity` が `S1` / `S2` のどちらかである
- `eval_mode` が case の評価目的に合っている
- 質問文が顧客業務に合っている
- `reviewed_by` / `reviewed_at` が入力されている
- `decision: approve` にする理由を説明できる

どれかが満たせない場合は `pending` にしてください。

## 10. `approve-cases` の使い方

レビュー後、承認結果を `cases.csv` に反映します。

```bash
rqg approve-cases \
  --draft cases_draft.csv \
  --review review_cases.yaml \
  --output cases.csv
```

`approve-cases` は、`decision: approve` の case を `status=active` にします。`decision: pending` は `needs_review` のまま、`decision: reject` は `deprecated` になります。

生成された `cases.csv` を確認したら、通常の Gate 実行に進みます。

```bash
rqg gate --pack path/to/quality-pack
```

## 11. やってはいけないこと

- generated `expected_answer` をそのまま正式正解扱いしない
- `needs_review` を手動で雑に `active` にしない
- `S3` / `S4` / `high` / `critical` などの未対応 `severity` を使わない
- `review_cases.md` を編集正本にしない
- `cases_draft.csv` をそのまま Gate に使わない
- 根拠が不明な case を `approve` しない
- AI 生成だけで顧客固有の正確性を承認済みにしない

## 12. legacy `review.csv` との関係

legacy `gen-cases` が出力する `review.csv` や review markdown も review artifact です。正式な `cases.csv` ではありません。

`answer_status:unapproved-draft` が `notes` に含まれている場合、その `expected_answer` は未承認の draft です。ベンダーが顧客文書や業務ルールに照らして確認するまでは、正式正解として扱わないでください。

legacy `review.csv` を使う場合も、原則は同じです。

- 生成物は未承認候補として扱う
- ベンダーが業務正しさを確認する
- 承認済み case だけを正式な Gate 対象にする
- `active` 化は説明可能な判断に基づいて行う
