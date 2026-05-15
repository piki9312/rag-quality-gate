# Quality Pack S1/S2設計ガイド

このガイドは、顧客向けRAG/FAQエージェントのQuality Packを作るときに、`cases.csv` の `severity` をどう割り当てるかを説明します。

`validate-pack` は、まず警告としてこれらの設計リスクを表示します。既存packを壊さずに、設計ミスを早期に見つけることが目的です。

## Severityの意味

| Severity | 意味 | 典型的な用途 |
| --- | --- | --- |
| `S1` | 本番反映を止めるべきケース。失敗した場合はリリース停止、または明示的な承認が必要。 | 誤回答が信頼、コンプライアンス、HR/労務対応、エスカレーション、顧客説明責任に影響する高リスク回答。 |
| `S2` | 通常の回帰検査ケース。失敗した場合は確認・修正が必要だが、単独では毎回リリース停止にしないことが多い。 | 通常FAQの表現、網羅性確認、低リスクのポリシー詳細、補助的な業務フロー。 |

`S1` は少数に絞りつつ、意図的に設定します。S1がないpackはblocking gateとして弱く、すべてがS1のpackは運用負荷が高くなりすぎます。

## 推奨されるS1ケースの形

activeな `S1` ケースには、通常、次の情報を入れます。

- `expected_answer`: 顧客が承認した短い正答。
- `expected_evidence` またはlegacyの `expected_chunks`: 回答の根拠となる文書セクションまたはchunk。
- `expected_keywords`: 明らかな回答ずれを検知するための業務上重要な語句を2から5個。
- `category`: `deadline`, `eligibility`, `procedure`, `exception`, `escalation` などのリスク分類。

例:

```csv
case_id,severity,eval_mode,question,expected_answer,expected_evidence,expected_keywords,category
HR001,S1,evidence_keyword,有給休暇はいつまでに申請する必要がありますか？,有給休暇は5営業日前までに申請する必要があります。,leave_policy.md#sec-1,有給休暇;5営業日前;事前申請,deadline
```

## validate-packの警告

`validate-pack` は、次のようなS1/S2設計リスクを警告します。

- `Quality Pack has 0 active S1 cases.`
- `Quality Pack has only 1 S1 case across ... active cases.`
- `S1 case has no expected_answer.`
- `S1 case has no expected_evidence.`
- `S1 case has no expected_keywords.`
- `All active cases are S1.`
- `All active cases are S2.`
- `Category coverage is concentrated in ...`

既存のvalidation errorがない限り、警告だけではexit codeを変えません。月額運用に入る前にQuality Packを改善するためのオンボーディング指摘として扱います。

## 実務上の開始ライン

最初の顧客packでは、次の構成から始めます。

- 顧客への約束や重大リスクを検査する `S1` ケースを3から5件。
- 広い回帰確認を担う `S2` ケースを10から30件。
- 1つの業務フローに偏りすぎないよう、少なくとも3カテゴリ。
- retrieval miss、期限誤り、根拠のない回答、エスカレーション/連絡先誤りなど、主要failure modeごとにレビュー担当者が説明できるS1ケースを1件以上。

## Failure Patternとの追跡性

生成候補をactiveな `cases.csv` に昇格する前に、AI/RAGがどのような業務リスクを起こし得るかをfailure patternとして定義します。failure patternは実行ケースではありません。1つ以上のケースが必要である理由を説明する設計資産です。

active caseから設計資産へ軽く戻れるよう、`notes` 列に次の形式で参照を残します。

```text
pattern:FP-REFUND-001
```

activeな `S1` ケースで `notes` に `pattern:FP-...` 参照がない場合、`validate-cases` は警告を出します。これはerrorではなくwarningです。既存packとの互換性を保ちつつ、新しいPoCや月額運用packをレビューしやすくするためです。

推奨するレビュー手順は次の通りです。

1. failure patternを定義または更新する。
2. case候補を生成する。
3. 候補をfailure patternと照らしてレビューする。
4. 承認済みの行だけを `cases.csv` に昇格する。
5. `notes` に `pattern:<ID>` を残す。
6. 月額運用では `last_reviewed_at` を更新する。

## 顧客向け Gate 判定ルール

Proof Gate の判定は「対象 Quality Pack と今回実行したケースの範囲で、定義済み基準を満たしたか」を示します。PASS でも、AI/RAG の全回答が完全に保証されたという意味ではありません。

| 状態 | 顧客向け判断 |
| --- | --- |
| `S1` fail | `BLOCK`。本番反映を止め、原因調査と再実行結果を確認する。 |
| `S1` judge fallback | `NEEDS_HUMAN_REVIEW`。自動判定の信頼性が不足しているため、`BLOCK` 相当として人手確認する。 |
| `S2` のみ失敗 | `REVIEW`。単独では常に本番停止とはしないが、影響範囲と修正要否を確認する。 |
| `S1` 重大失敗なしの全体しきい値未達 | `REVIEW`。S1重大事故は出ていないが、全体品質の低下として人手確認する。 |
| judge unavailable | 判定信頼性が不足している状態として明示し、人手確認または再実行を求める。 |
| gate pass | 対象ケースとしきい値の範囲では基準を満たした状態。完全保証ではない。 |

`needs_human_review` が `true` の場合、顧客向けには「自動判定だけで本番反映を決めない」状態として扱います。
