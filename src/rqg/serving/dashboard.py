"""Read-only dashboard for packs, runs, and monthly summaries."""

from __future__ import annotations

import html
import json
import re
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, PlainTextResponse

from ..quality.history import load_gate_decision_history
from ..quality.monthly_summary import build_monthly_summary_payload
from ..quality.reporting import build_customer_review_markdown

_DEFAULT_DASHBOARD_LANG = "ja"
_DASHBOARD_JA_TEXT = {
    "Packs": "パック一覧",
    "Pack": "パック",
    "Use Case": "用途",
    "Vertical": "業務領域",
    "Risk": "リスク",
    "Latest Gate": "最新判定",
    "Latest Run": "最新run",
    "S1 Fails": "S1失敗数",
    "Fallback": "フォールバック",
    "Runs": "run一覧",
    "Latest gate": "最新判定",
    "No runs found.": "run がありません。",
    "Run Detail": "検査結果詳細",
    "Review Packet": "レビュー情報",
    "ReviewPacket is not available for this run.": "この run にはレビュー情報がありません。",
    "Gate Details": "ゲート詳細",
    "Status": "状態",
    "Policy status": "判定ポリシー",
    "Overall pass rate": "全体合格率",
    "S1 pass rate": "S1合格率",
    "S1 fail count": "S1失敗数",
    "Judge reliability": "判定器信頼度",
    "Fallback summary": "フォールバック概要",
    "Needs human review": "人間確認要否",
    "Previous diff": "比較対象",
    "Reasons": "理由",
    "Next Actions": "次の対応",
    "Decision Card": "判定",
    "Delivery Review Summary": "納品判定サマリー",
    "Review stage": "レビュー段階",
    "Unresolved S1": "未解決S1",
    "Unresolved S2": "未解決S2",
    "Customer shareability": "顧客共有可否",
    "Formal submission readiness": "正式提出の推奨度",
    "Shareability": "共有安全性",
    "S1/S2 Blocking List": "S1/S2ブロッカー一覧",
    "Issue": "問題",
    "Blocks delivery": "納品停止",
    "Summary Card": "検査サマリー",
    "Scope Card": "検査範囲",
    "Change Event Card": "変更内容",
    "Document Corpus Card": "根拠文書",
    "Production Readiness Card": "本番移行準備度",
    "Severity Summary": "重大度サマリー",
    "Risk Breakdown": "リスク分類",
    "Major Failures": "重大な失敗",
    "Report Preview": "顧客提出レポート",
    "Blocking reasons": "本番反映を止める理由",
    "Required actions": "必要な対応",
    "Warnings": "注意事項",
    "Severity": "重大度",
    "Reason": "理由",
    "Affected": "影響件数",
    "Why it matters": "なぜ重要か",
    "Total": "総件数",
    "Passed": "合格",
    "Failed": "失敗",
    "Pass Rate": "合格率",
    "Report Mode": "レポート種別",
    "Target": "対象",
    "Type": "種別",
    "Documents": "文書",
    "Versions": "バージョン",
    "Change Event": "変更イベント",
    "Document Count": "文書数",
    "Source of Truth Type": "正文書種別",
    "Has Versions": "バージョン情報あり",
    "Stale Doc Policy": "旧文書参照ポリシー",
    "Version Hashes": "文書バージョンHash",
    "Full document metadata": "対象文書",
    "Title": "文書名",
    "Version": "バージョン",
    "Last Updated": "更新日",
    "Owner": "オーナー",
    "Snapshot ID": "スナップショットID",
    "Source Path": "ソースパス",
    "Change Type": "変更種別",
    "Summary": "変更概要",
    "Changed Assets": "変更対象数",
    "Affected Documents": "影響文書数",
    "Affected Categories": "影響カテゴリ",
    "Target Release": "対象リリース",
    "Retest reason:": "再検査理由:",
    "Full change assets": "変更対象の詳細",
    "Blockers": "移行ブロッカー",
    "Code": "コード",
    "Label": "項目",
    "Action": "対応",
    "Item": "項目",
    "Count": "件数",
    "Failure Pattern": "失敗パターン",
    "Category": "カテゴリ",
    "Evidence Status": "根拠状態",
    "Go/No-Go Impact": "本番反映への影響",
    "Next Action": "次の対応",
    "Detail": "詳細",
    "Customer Severity": "顧客向け重大度",
    "Internal Severity": "内部重大度",
    "Failure Category": "失敗カテゴリ",
    "Safe Reason Code": "安全理由コード",
    "Full Detail Ref": "詳細参照",
    "Full Detail Summaries": "詳細要約",
    "Question": "質問",
    "Expected": "期待値",
    "Actual": "実際の回答",
    "Back to Run Detail": "検査結果詳細に戻る",
    "Executive Summary": "要約",
    "Decision": "判定",
    "Change Summary": "変更概要",
    "Scope": "検査範囲",
    "Production Readiness": "本番移行準備度",
    "Major Risks": "主要リスク",
    "Blocking Issues": "本番反映を止める問題",
    "Required Actions": "必要な対応",
    "Residual Risks": "残留リスク",
    "Disclaimer": "検査範囲と注意事項",
    "Failure": "失敗詳細",
    "Run": "run",
    "Policy Status": "判定ポリシー",
    "Origin": "発生源",
    "Affected Cases": "影響ケース",
    "Recommended Action": "推奨対応",
    "Total runs": "総run数",
    "Blocked runs": "ブロックrun数",
    "S1 incidents detected": "検知したS1インシデント",
    "Fallback trend": "フォールバック傾向",
    "Trend summary": "推移サマリー",
    "Unresolved issues": "未解決事項",
    "Monthly summary": "月次サマリー",
    "Monthly summary for": "月次サマリー",
    "No failed or review-required cases found.": "失敗または要確認のケースはありません。",
    "None": "なし",
    "YES": "あり",
    "NO": "なし",
    "Not available in safe mode": "safeモードでは表示しません",
    "Document titles, owners, and source paths are not expanded in safe mode.": (
        "safeモードでは文書名、オーナー、ソースパスを展開しません。"
    ),
    "Changed asset names and affected document names are not expanded in safe mode.": (
        "safeモードでは変更対象名と影響文書名を展開しません。"
    ),
    "Safe packet: raw question, answer, and evidence text are not expanded here.": (
        "safe版では raw question、answer、evidence はここに表示しません。"
    ),
}
_DASHBOARD_JA_VALUES = {
    "Go": "本番反映可",
    "Conditional": "条件付き",
    "No-Go": "本番反映不可",
    "ready": "準備完了",
    "conditional": "条件付き",
    "not_ready": "未準備",
    "unknown": "不明",
    "aligned": "整合",
    "mismatch": "不一致",
    "retrieved_unverified": "取得済み未確認",
    "not_available": "情報なし",
    "blocks_release": "本番反映を止める",
    "requires_human_review": "人間確認が必要",
    "needs_fix_or_review": "修正または確認が必要",
    "informational": "参考情報",
    "document_update": "文書更新",
    "prompt_change": "プロンプト変更",
    "model_change": "モデル変更",
    "retriever_change": "検索設定変更",
    "chunking_change": "分割設定変更",
    "embedding_change": "埋め込み設定変更",
    "config_change": "設定変更",
    "approved_policy": "承認済みポリシー",
    "declared_source_of_truth": "宣言済み正文書",
    "document_snapshot": "文書スナップショット",
    "index_version": "インデックス版",
    "True": "あり",
    "False": "なし",
    "critical": "重大",
    "high": "高",
    "medium": "中",
    "low": "低",
    "major_misguidance": "重大な誤案内",
    "evidence_mismatch": "根拠不一致",
    "stale_reference": "旧情報参照",
    "business_rule_violation": "業務ルール違反",
    "human_review_required": "人間確認が必要",
    "pre_delivery": "納品前レビュー",
    "post_delivery_change": "納品後変更レビュー",
    "monthly_review": "月次レビュー",
    "deliverable": "納品可",
    "needs_fix": "修正が必要",
    "needs_approval": "承認が必要",
    "not_deliverable": "納品不可",
    "safe_to_share": "共有可",
    "needs_review": "要確認",
    "not_safe": "共有不可",
    "shareable": "共有可",
    "not_shareable": "共有不可",
    "recommended": "正式提出を推奨",
    "not_recommended": "正式提出は非推奨",
}
_DASHBOARD_JA_ISSUES = {
    "critical_failure_remaining": {
        "label": "重大な失敗が残っています",
        "reason": "本番反映前に解消すべき重大な失敗が検出されています。",
        "action": "該当ケースを修正し、再検査してください。",
    },
    "no_go_decision": {
        "label": "本番反映不可",
        "reason": "今回の検査結果は No-Go です。",
        "action": "No-Go の原因となった失敗を解消してから再実行してください。",
    },
    "decision_no_go": {
        "label": "本番反映不可",
        "reason": "今回の検査結果は No-Go です。",
        "action": "No-Go の原因となった失敗を解消してから再実行してください。",
    },
    "source_of_truth_missing": {
        "label": "正文書が未設定です",
        "reason": "どの文書を正しい根拠として扱うかが明確ではありません。",
        "action": "正文書を定義してから再検査してください。",
    },
    "required_stale_doc_policy_missing": {
        "label": "必須の旧文書参照ポリシーが未設定です",
        "reason": "旧文書参照ポリシーが必須なのに定義されていません。",
        "action": "旧文書参照ポリシーを定義してから本番移行を判断してください。",
    },
    "stale_doc_policy_missing": {
        "label": "旧文書参照ポリシーが未設定です",
        "reason": "古い FAQ や規約の扱いが明確に定義されていません。",
        "action": "旧文書を拒否するか、要確認にするかを設定してください。",
    },
    "document_versions_missing": {
        "label": "文書バージョン情報がありません",
        "reason": "安定した文書バージョン証跡を示せない状態です。",
        "action": "スナップショット ID、index version、文書 version を追加してください。",
    },
    "target_documents_missing": {
        "label": "対象文書が確認できません",
        "reason": "今回の検査で参照対象となる文書証跡が確認できません。",
        "action": "本番移行前に document corpus の証跡を添付してください。",
    },
    "human_review_required": {
        "label": "人間レビューが必要です",
        "reason": "自動判定だけでは本番反映可否を確定できないケースがあります。",
        "action": "担当者が該当ケースを確認してください。",
    },
    "needs_human_review": {
        "label": "人間レビューが必要です",
        "reason": "人手確認が必要なケースまたは信頼性シグナルが含まれています。",
        "action": "担当者が該当ケースを確認してください。",
    },
    "evidence_policy_unknown": {
        "label": "evidence policy が不明です",
        "reason": "safe か full かの証跡ポリシーが明示されていません。",
        "action": "production review 前に evidence policy mode を設定してください。",
    },
    "change_event_missing": {
        "label": "変更内容が未指定です",
        "reason": "今回何を変更したために検査したのかが明確ではありません。",
        "action": "change-event.yml を指定して再実行してください。",
    },
    "change_type_unknown": {
        "label": "変更種別が不明です",
        "reason": "変更が文書、プロンプト、モデル、検索設定のどれかに分類されていません。",
        "action": "bounded な change_type を設定してください。",
    },
    "changed_assets_missing": {
        "label": "変更対象が未記録です",
        "reason": "何が変わったのかを packet から特定できません。",
        "action": "changed_assets を bounded metadata として記録してください。",
    },
    "affected_documents_missing": {
        "label": "影響文書が未記録です",
        "reason": "document update なのに影響文書数が示されていません。",
        "action": "ChangeEvent に affected documents または件数を記録してください。",
    },
    "retest_trigger_unclear": {
        "label": "再検査理由が不明です",
        "reason": "なぜこの変更で再検査が必要なのかが説明できない状態です。",
        "action": "change-event.yml に retest_reason を記載してください。",
    },
    "s1_case_failed": {
        "label": "重大ケースが失敗しました",
        "reason": "高リスクのケースが失敗しており、本番反映できません。",
        "action": "該当ケースを修正して再検査してください。",
    },
    "s2_case_failed": {
        "label": "非重大ケースが失敗しました",
        "reason": "品質確認が必要なケース失敗が残っています。",
        "action": "該当ケースを見直し、必要に応じて再検査してください。",
    },
    "evidence_mismatch": {
        "label": "根拠不一致",
        "reason": "回答と期待される根拠文書の整合が取れていません。",
        "action": "根拠文書に沿って回答を修正し、再検査してください。",
    },
    "stale_reference": {
        "label": "旧情報参照",
        "reason": "古い文書や無効な情報に依拠している可能性があります。",
        "action": "最新の正文書を参照するように修正してください。",
    },
    "major_misguidance": {
        "label": "重大な誤案内",
        "reason": "顧客に不利益や誤解を与える重大な案内ミスが検出されています。",
        "action": "回答内容を修正し、再検査してください。",
    },
    "business_rule_violation": {
        "label": "業務ルール違反",
        "reason": "定義された業務ルールやポリシーに反する回答です。",
        "action": "業務ルールに沿うよう回答を修正してください。",
    },
    "expected_evidence_recall_below_threshold": {
        "label": "期待根拠の取得率不足",
        "reason": "期待される根拠文書を十分に取得できていません。",
        "action": "retrieval 設定と根拠文書の紐付けを見直してください。",
    },
    "keyword_match_below_threshold": {
        "label": "期待要素の欠落",
        "reason": "期待する回答要素が十分に含まれていません。",
        "action": "回答要件を満たすよう prompt または evaluator を見直してください。",
    },
    "overall_threshold_not_met": {
        "label": "全体閾値未達",
        "reason": "設定された overall quality threshold を満たしていません。",
        "action": "失敗ケースを解消して閾値を満たしてから再実行してください。",
    },
    "threshold_not_met": {
        "label": "品質閾値未達",
        "reason": "設定された品質閾値を満たしていません。",
        "action": "失敗ケースを解消してから再実行してください。",
    },
    "retrieval_fail": {
        "label": "検索失敗",
        "reason": "必要な根拠文書を十分に取得できていません。",
        "action": "retrieval 設定と索引対象を見直してください。",
    },
    "retrieval_miss": {
        "label": "検索漏れ",
        "reason": "必要な根拠文書が検索結果から漏れています。",
        "action": "検索設定や索引対象を見直してください。",
    },
    "answer_quality_fail": {
        "label": "回答品質の問題",
        "reason": "回答品質が期待水準を満たしていません。",
        "action": "回答生成ロジックまたは prompt を見直してください。",
    },
    "judge_fallback_used": {
        "label": "判定フォールバックが使われました",
        "reason": "通常の判定器ではなくフォールバック経路で判定されています。",
        "action": "判定器の安定性を確認し、必要なら再検査してください。",
    },
    "judge_unavailable": {
        "label": "判定器を利用できません",
        "reason": "判定器が利用できず、結果の信頼性に影響します。",
        "action": "判定器の状態を確認して再検査してください。",
    },
}
_DASHBOARD_JA_MESSAGES = {
    "No-Go: release should wait.": "本番反映不可です。リリースは見合わせてください。",
    "No-Go: release should wait until blocking issues are fixed.": "本番反映不可です。ブロッカーを解消するまでリリースは見合わせてください。",
    "Needs human review before release approval.": "本番反映判断の前に人間レビューが必要です。",
    "Conditional: review warnings and residual risk before release.": "条件付きです。注意事項と残留リスクを確認してから本番反映を判断してください。",
    "Go: configured checks passed for this scoped run.": "この検査範囲では configured checks を満たしています。",
    "Critical case failed.": "重大なケースが失敗しています。",
    "Critical case failed is the primary release concern for this run.": "重大なケースの失敗が、この run の主な本番反映リスクです。",
    "A high-risk case failed.": "高リスクのケースが失敗しています。",
    "A human review signal is present.": "人間レビューが必要なシグナルが含まれています。",
    "Release should wait.": "リリースは見合わせるべきです。",
    "No-Go (block)": "本番反映不可 (No-Go) です。",
    "Change event metadata is available.": "変更イベントのメタデータを確認できる状態です。",
    "Document update can change retrieval evidence.": "文書更新により検索根拠が変わる可能性があります。",
    "Document update can change retrieval evidence and answer behavior.": "文書更新により検索根拠や回答挙動が変わる可能性があります。",
    "Prompt change can change answer policy and tone.": "プロンプト変更により回答方針やトーンが変わる可能性があります。",
    "Model change can alter answer generation behavior.": "モデル変更により回答生成の挙動が変わる可能性があります。",
    "Retrieval configuration change can alter available evidence.": "検索設定の変更により利用可能な根拠が変わる可能性があります。",
    "Change event requires scoped retesting before release.": "この変更は、本番反映前に対象範囲を絞った再検査が必要です。",
    "Fix the critical case and rerun.": "重大なケースを修正して再検査してください。",
    "Fix the critical case and rerun": "重大なケースを修正して再検査してください。",
    "Fix and rerun": "修正して再検査してください。",
    "Fix and rerun.": "修正して再検査してください。",
    "Complete human review": "担当者が人間レビューを完了してください。",
    "Complete human review.": "担当者が人間レビューを完了してください。",
    "Route for human review before release approval.": (
        "リリース承認前に担当者レビューへ回してください。"
    ),
    "Route this run for human review before release approval.": (
        "リリース承認前にこの実行結果を担当者レビューへ回してください。"
    ),
    "Fix the Critical failure(s) and rerun before production release.": (
        "本番リリース前にCriticalの失敗を修正し、再実行してください。"
    ),
    "Resolve blocking issues and rerun the gate.": (
        "ブロッカーを解消し、gateを再実行してください。"
    ),
    "Define the source of truth for the document corpus.": (
        "文書コーパスの正本となる文書を定義してください。"
    ),
    "Define how stale documents are rejected, flagged, or reviewed.": (
        "古い文書を拒否、警告、レビュー対象のいずれで扱うか定義してください。"
    ),
    "Complete human review before treating this run as release evidence.": (
        "この実行結果をリリース判断の証跡として扱う前に、人間レビューを完了してください。"
    ),
    "Record affected documents or document count for the ChangeEvent.": (
        "ChangeEventに影響文書または文書件数を記録してください。"
    ),
    "Review customer-facing export before submission.": (
        "顧客提出前に、顧客向けエクスポート内容を確認してください。"
    ),
    "Review the evidence alignment.": "根拠文書との整合を確認してください。",
    "Align with approved evidence.": "承認済み根拠に沿って回答を修正してください。",
    "Not ready for production.": "本番移行の準備は未完了です。",
    "PASS is scoped.": "今回の判定はこの検査範囲に限定されます。",
    "Not a complete guarantee.": "完全な保証ではありません。",
    "Delivery is not recommended until blockers are fixed.": "ブロッカーが解消されるまで納品は推奨されません。",
    "Delivery review indicates this safe packet is ready for customer submission.": (
        "このsafe版パケットは顧客提出に進められる状態です。"
    ),
    "Fix production readiness blockers before treating this run as deliverable.": (
        "納品可能と判断する前に、本番移行準備のブロッカーを解消してください。"
    ),
    "Delivery review status is unknown.": "納品判定ステータスは不明です。",
    "Formal customer submission is not recommended.": "正式な顧客提出は推奨されません。",
    "Formal customer submission is recommended for the scoped quality review.": (
        "今回の検査範囲では、正式な顧客提出を推奨できます。"
    ),
    "Formal customer submission is conditional on PM approval and documented residual risk.": (
        "正式な顧客提出には、PM承認と残存リスクの記録が必要です。"
    ),
    "Review the unresolved item before customer submission.": (
        "顧客提出前に未解決項目を確認してください。"
    ),
    "Reviewer notes placeholder.": "レビュー担当者のメモ欄です。",
    "Reviewer notes: record approval, rejection, accepted risk, or required fixes here.": (
        "レビュー担当者メモ: 承認、差し戻し、許容リスク、必要な修正をここに記録してください。"
    ),
}

_DASHBOARD_JA_TEXT.update(
    {
        "Review Overview": "レビュー全体像",
        "Internal Review": "社内レビュー",
        "Customer Submission": "顧客提出",
        "Customer Submission Status": "顧客提出状態",
        "Improvement Actions": "優先度付き改善アクション",
        "Prioritized Improvement Actions": "次にやるべき改善アクション",
        "Improvement Order": "推奨される改善順序",
        "Priority": "優先度",
        "Owner": "推奨担当",
        "Next State": "次の状態",
        "Top blockers": "最重要ブロッカー",
        "Next priority actions": "次にやるべき対応",
        "Customer report": "顧客提出レポート",
        "Why this status": "この状態の理由",
        "Report title": "レポート名",
        "One-line summary": "1行要約",
        "Review scope": "検査範囲",
        "Cautions": "注意事項",
        "Internal Review Notes": "社内レビューの見方",
        "Customer Submission Notes": "顧客提出の見方",
    }
)

_DASHBOARD_JA_VALUES.update(
    {
        "Go": "本番反映可",
        "Conditional": "条件付き",
        "No-Go": "本番反映不可",
        "ready": "準備完了",
        "conditional": "条件付き",
        "not_ready": "未準備",
        "pre_delivery": "納品前品質診断",
        "post_delivery_change": "納品後変更レビュー",
        "monthly_review": "月次品質レビュー",
        "not_deliverable": "納品不可",
        "needs_fix": "修正が必要",
        "needs_approval": "承認が必要",
        "deliverable": "納品可能",
        "shareable": "情報共有可能",
        "safe_to_share": "情報共有可能",
        "needs_review": "要レビュー",
        "not_shareable": "共有不可",
        "not_safe": "共有不可",
        "recommended": "正式提出推奨",
        "not_recommended": "正式提出非推奨",
        "evidence_mismatch": "根拠不一致",
        "stale_reference": "古い情報参照",
        "major_misguidance": "重大な誤案内",
        "business_rule_violation": "業務ルール違反",
        "human_review_required": "人間レビューが必要",
        "document_update": "文書更新",
        "approved_policy": "承認済みポリシー",
        "blocks_release": "本番反映を止める",
        "requires_human_review": "人間レビューが必要",
        "needs_fix_or_review": "修正またはレビューが必要",
        "Critical": "重大",
        "High": "高",
        "Medium": "中",
        "Low": "低",
        "True": "あり",
        "False": "なし",
    }
)

_DASHBOARD_JA_MESSAGES.update(
    {
        "Delivery is not recommended until blockers are fixed.": (
            "未解決ブロッカーが残っているため、現時点での納品は推奨されません。"
        ),
        "Formal customer submission is not recommended.": (
            "正式な顧客提出は推奨されません。社内で修正・再検査してください。"
        ),
        "Formal customer submission is recommended for the scoped quality review.": (
            "今回の検査範囲では、正式な顧客提出レポートとして利用できます。"
        ),
        "Formal customer submission is conditional on PM approval and documented residual risk.": (
            "正式提出には、PM承認と残留リスクの明記が必要です。"
        ),
        "Change event metadata is available.": "変更イベント情報は記録されています。",
        "Document update can change retrieval evidence.": (
            "文書更新により、検索される根拠や回答内容が変わる可能性があります。"
        ),
        "Critical case failed.": "重大ケースが失敗しています。",
        "Fix the critical case and rerun.": "重大ケースを修正し、再検査してください。",
        "Review the evidence alignment.": "根拠文書との整合を確認してください。",
    }
)


def _dashboard_lang(request: Request | None) -> str:
    if request is None:
        return _DEFAULT_DASHBOARD_LANG
    raw = str(request.query_params.get("lang") or _DEFAULT_DASHBOARD_LANG).strip().lower()
    return "en" if raw == "en" else "ja"


def _tr(lang: str, text: str) -> str:
    if lang == "ja":
        return _DASHBOARD_JA_TEXT.get(text, text)
    return text


def _translate_value(lang: str, value: object, *, show_raw: bool = False) -> str:
    raw = "True" if value is True else "False" if value is False else str(value or "").strip()
    if lang != "ja" or not raw:
        return raw
    normalized = raw.lower().replace("-", "_")
    mapped = (
        _DASHBOARD_JA_VALUES.get(raw)
        or _DASHBOARD_JA_VALUES.get(raw.lower())
        or _DASHBOARD_JA_VALUES.get(normalized)
    )
    if not mapped:
        return raw
    if show_raw and mapped != raw:
        return f"{mapped} ({raw})"
    return mapped


def _normalize_code(value: object) -> str:
    return str(value or "").strip().lower().replace("-", "_").replace(" ", "_")


def _unique_texts(values: list[object]) -> list[str]:
    items: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        if not text or text in seen:
            continue
        seen.add(text)
        items.append(text)
    return items


def _translate_issue_label(
    code: object,
    fallback: object | None = None,
    *,
    lang: str,
    show_raw: bool = False,
) -> str:
    raw_code = _normalize_code(code)
    fallback_text = str(fallback or "").strip()
    if lang != "ja":
        return fallback_text or raw_code
    issue = _DASHBOARD_JA_ISSUES.get(raw_code)
    if issue:
        label = issue["label"]
        if show_raw and raw_code:
            return f"{label} ({raw_code})"
        return label
    translated = _translate_message(lang, fallback_text)
    if translated:
        if show_raw and raw_code and translated != raw_code:
            return f"{translated} ({raw_code})"
        return translated
    return raw_code or fallback_text


def _translate_issue_reason(code: object, fallback: object | None = None, *, lang: str) -> str:
    raw_code = _normalize_code(code)
    fallback_text = str(fallback or "").strip()
    if lang != "ja":
        return fallback_text or raw_code
    issue = _DASHBOARD_JA_ISSUES.get(raw_code)
    if issue and issue.get("reason"):
        return issue["reason"]
    return _translate_message(lang, fallback_text) or fallback_text or raw_code


def _translate_issue_action(code: object, fallback: object | None = None, *, lang: str) -> str:
    raw_code = _normalize_code(code)
    fallback_text = str(fallback or "").strip()
    if lang != "ja":
        return fallback_text or raw_code
    issue = _DASHBOARD_JA_ISSUES.get(raw_code)
    if issue and issue.get("action"):
        return issue["action"]
    return _translate_message(lang, fallback_text) or fallback_text or raw_code


def _translate_message(lang: str, text: object | None) -> str:
    raw = str(text or "").strip()
    if lang != "ja" or not raw:
        return raw
    mapped = _DASHBOARD_JA_MESSAGES.get(raw) or _DASHBOARD_JA_MESSAGES.get(raw.rstrip("."))
    if mapped:
        return mapped
    if match := re.fullmatch(
        r"Not ready for production: (\d+) blocker\(s\) and (\d+) warning\(s\) need attention\.?",
        raw,
    ):
        return (
            f"本番移行の準備は未完了です。{match.group(1)} 件のブロッカーと "
            f"{match.group(2)} 件の注意事項への対応が必要です。"
        )
    if match := re.fullmatch(
        r"Conditionally ready: no blockers, but (\d+) warning\(s\) should be reviewed before production migration\.?",
        raw,
    ):
        return (
            f"条件付きで準備完了です。ブロッカーはありませんが、"
            f"{match.group(1)} 件の注意事項を確認してください。"
        )
    if raw == "Ready for production review based on this scoped packet.":
        return "この検査範囲では本番移行レビューに進める状態です。"
    if raw == "Production readiness is unknown because required packet data is missing.":
        return "必要な packet 情報が不足しているため、本番移行準備度を判定できません。"
    if match := re.fullmatch(r"(\d+) Critical issue(?:s)?", raw):
        return f"重大な問題が {match.group(1)} 件あります。"
    if match := re.fullmatch(r"Critical:\s*([a-z0-9_\-]+)", raw):
        code = match.group(1)
        return f"重大: {_translate_issue_label(code, code, lang=lang, show_raw=True)}"
    if match := re.fullmatch(r"S1 pass rate: (.+)", raw):
        return f"S1合格率: {match.group(1)}"
    if match := re.fullmatch(r"Overall pass rate: (.+)", raw):
        return f"全体合格率: {match.group(1)}"
    if match := re.fullmatch(
        r"Document corpus: (\d+) document(?:s)?; has versions=(True|False)", raw
    ):
        return (
            f"根拠文書は {match.group(1)} 件で、"
            f"バージョン情報あり={_translate_value(lang, match.group(2))} です。"
        )
    if match := re.fullmatch(r"change_type=([a-z_]+); affected_documents=(\d+)", raw):
        change_type = _translate_value(lang, match.group(1), show_raw=True)
        return f"変更種別は {change_type} で、影響文書は {match.group(2)} 件です。"
    return raw


def _translate_reason_item(reason: object, *, lang: str) -> str:
    raw = str(reason or "").strip()
    if lang != "ja" or not raw:
        return raw
    normalized = _normalize_code(raw)
    if normalized in _DASHBOARD_JA_ISSUES:
        return _translate_issue_label(normalized, raw, lang=lang, show_raw=True)
    return _translate_message(lang, raw) or raw


def _translate_failure_pattern(value: object, *, lang: str, show_raw: bool = False) -> str:
    raw = str(value or "").strip()
    if not raw:
        return "-"
    return _translate_issue_label(raw, raw, lang=lang, show_raw=show_raw)


def _translate_decision_headline(
    decision: dict[str, Any],
    explanation: dict[str, Any],
    blocking_reasons: list[object],
    *,
    lang: str,
) -> str:
    fallback = str(explanation.get("headline") or "").strip()
    if lang != "ja":
        return fallback or "-"
    translated = _translate_message(lang, fallback)
    if translated and translated != fallback:
        return translated
    status = _normalize_code(explanation.get("decision") or decision.get("customer_status"))
    if status == "no_go":
        return "本番反映不可です。リリースは見合わせてください。"
    if status in {"needs_human_review", "needs_human_review_before_release_approval"}:
        return "本番反映判断の前に人間レビューが必要です。"
    if status == "conditional":
        return "条件付きです。注意事項と残留リスクを確認してください。"
    if status == "go":
        return "本番反映可能です。"
    for item in blocking_reasons:
        if isinstance(item, dict):
            return _translate_issue_label(
                item.get("reason_code"),
                item.get("label", fallback),
                lang=lang,
            )
    return translated or fallback or "-"


def _translate_decision_reason_text(
    decision: dict[str, Any],
    explanation: dict[str, Any],
    blocking_reasons: list[object],
    *,
    lang: str,
) -> str:
    fallback = str(explanation.get("plain_language_reason") or "").strip()
    if lang != "ja":
        return fallback or "-"
    translated = _translate_message(lang, fallback)
    if translated and translated != fallback:
        return translated
    reasons = _unique_texts(
        [
            _translate_issue_reason(
                item.get("reason_code"),
                item.get("why_it_blocks") or item.get("label"),
                lang=lang,
            )
            for item in blocking_reasons
            if isinstance(item, dict)
        ]
    )
    if reasons:
        return " / ".join(reasons[:2])
    if _normalize_code(decision.get("customer_status")) == "go":
        return "この検査範囲では指定されたケース、文書、設定で checks を満たしています。"
    return translated or fallback or "-"


def _decision_action_items(
    explanation: dict[str, Any],
    blocking_reasons: list[object],
    *,
    lang: str,
) -> list[str]:
    actions: list[str] = []
    for item in blocking_reasons:
        if not isinstance(item, dict):
            continue
        action = item.get("required_action")
        if action:
            actions.append(_translate_issue_action(item.get("reason_code"), action, lang=lang))
    for action in explanation.get("required_actions", []):
        actions.append(_translate_message(lang, action))
    return _unique_texts(actions)


def _readiness_action_items(readiness: dict[str, Any], *, lang: str) -> list[str]:
    actions: list[str] = []
    for item in readiness.get("blockers", []):
        if isinstance(item, dict):
            actions.append(
                _translate_issue_action(item.get("code"), item.get("required_action"), lang=lang)
            )
    for item in readiness.get("warnings", []):
        if isinstance(item, dict):
            actions.append(
                _translate_issue_action(
                    item.get("code"),
                    item.get("recommended_action"),
                    lang=lang,
                )
            )
    for action in readiness.get("required_actions", []):
        actions.append(_translate_message(lang, action))
    return _unique_texts(actions)


def _translate_readiness_summary(readiness: dict[str, Any], *, lang: str) -> str:
    fallback = str(readiness.get("readiness_summary") or "").strip()
    if lang != "ja":
        return fallback or "-"
    status = str(readiness.get("status") or "").strip()
    blockers = readiness.get("blockers", []) if isinstance(readiness.get("blockers"), list) else []
    warnings = readiness.get("warnings", []) if isinstance(readiness.get("warnings"), list) else []
    if status == "not_ready":
        return (
            f"本番移行の準備は未完了です。{len(blockers)} 件のブロッカーと "
            f"{len(warnings)} 件の注意事項への対応が必要です。"
        )
    if status == "conditional":
        return (
            f"条件付きです。{len(warnings)} 件の注意事項を確認してから本番移行を判断してください。"
        )
    if status == "ready":
        return "この検査範囲では本番移行レビューに進める状態です。"
    return _translate_message(lang, fallback) or fallback or "-"


def _report_preview_section_text(
    run: dict[str, Any], key: str, fallback: object, *, lang: str
) -> str:
    raw = str(fallback or "").strip() or "-"
    if lang != "ja":
        return raw
    packet = run.get("review_packet")
    if not isinstance(packet, dict):
        return _translate_message(lang, raw) or raw
    if key == "decision":
        decision = packet.get("decision", {}) if isinstance(packet.get("decision"), dict) else {}
        explanation = (
            packet.get("decision_explanation", {})
            if isinstance(packet.get("decision_explanation"), dict)
            else {}
        )
        blocking = explanation.get("blocking_reasons", [])
        if not isinstance(blocking, list):
            blocking = []
        parts = _unique_texts(
            [
                _translate_decision_headline(decision, explanation, blocking, lang=lang),
                _translate_decision_reason_text(decision, explanation, blocking, lang=lang),
            ]
        )
        return " ".join(parts) or (_translate_message(lang, raw) or raw)
    if key == "change_summary":
        change = (
            packet.get("change_summary", {})
            if isinstance(packet.get("change_summary"), dict)
            else {}
        )
        parts = [
            f"変更種別は {_translate_value(lang, change.get('change_type', 'unknown'), show_raw=True)} です。",
        ]
        if int(change.get("affected_documents_count") or 0) > 0:
            parts.append(f"影響文書は {int(change.get('affected_documents_count') or 0)} 件です。")
        if str(change.get("change_summary") or "").strip():
            parts.append(_translate_message(lang, change.get("change_summary")))
        if str(change.get("retest_reason") or "").strip():
            parts.append(f"再検査理由: {_translate_message(lang, change.get('retest_reason'))}")
        return " ".join(_unique_texts(parts)) or (_translate_message(lang, raw) or raw)
    if key == "scope":
        corpus = (
            packet.get("document_corpus", {})
            if isinstance(packet.get("document_corpus"), dict)
            else {}
        )
        return (
            f"根拠文書は {int(corpus.get('document_count') or 0)} 件で、"
            f"バージョン情報あり={_translate_value(lang, corpus.get('has_document_versions', False))} です。"
        )
    if key == "production_readiness":
        readiness = (
            packet.get("production_readiness", {})
            if isinstance(packet.get("production_readiness"), dict)
            else {}
        )
        parts = [
            f"本番移行準備度は {_translate_value(lang, readiness.get('status', 'unknown'), show_raw=True)} です。",
            _translate_readiness_summary(readiness, lang=lang),
        ]
        return " ".join(_unique_texts(parts)) or (_translate_message(lang, raw) or raw)
    if key == "major_risks":
        failures = (
            packet.get("major_failures", [])
            if isinstance(packet.get("major_failures"), list)
            else []
        )
        labels = _unique_texts(
            [
                _translate_failure_pattern(
                    item.get("failure_category") or item.get("failure_pattern"),
                    lang=lang,
                    show_raw=True,
                )
                for item in failures
                if isinstance(item, dict)
            ]
        )
        if labels:
            return f"主要リスク: {'、'.join(labels[:3])}"
        return _translate_message(lang, raw) or raw
    if key == "blocking_issues":
        readiness = (
            packet.get("production_readiness", {})
            if isinstance(packet.get("production_readiness"), dict)
            else {}
        )
        blockers = (
            readiness.get("blockers", []) if isinstance(readiness.get("blockers"), list) else []
        )
        labels = _unique_texts(
            [
                _translate_issue_label(
                    item.get("code"), item.get("label"), lang=lang, show_raw=True
                )
                for item in blockers
                if isinstance(item, dict)
            ]
        )
        if labels:
            return f"本番反映を止める問題: {'、'.join(labels)}"
        return _translate_message(lang, raw) or raw
    if key == "required_actions":
        explanation = (
            packet.get("decision_explanation", {})
            if isinstance(packet.get("decision_explanation"), dict)
            else {}
        )
        blocking = (
            explanation.get("blocking_reasons", [])
            if isinstance(explanation.get("blocking_reasons"), list)
            else []
        )
        readiness = (
            packet.get("production_readiness", {})
            if isinstance(packet.get("production_readiness"), dict)
            else {}
        )
        actions = _unique_texts(
            _decision_action_items(explanation, blocking, lang=lang)
            + _readiness_action_items(readiness, lang=lang)
        )
        if actions:
            return " / ".join(actions)
        return _translate_message(lang, raw) or raw
    if key == "residual_risks":
        failures = (
            packet.get("major_failures", [])
            if isinstance(packet.get("major_failures"), list)
            else []
        )
        labels = _unique_texts(
            [
                _translate_failure_pattern(
                    item.get("failure_category") or item.get("failure_pattern"),
                    lang=lang,
                    show_raw=True,
                )
                for item in failures
                if isinstance(item, dict)
            ]
        )
        if labels:
            return f"残留リスク: {'、'.join(labels[:3])}"
        return _translate_message(lang, raw) or raw
    return _translate_message(lang, raw) or raw


def _card_description(lang: str, title: str) -> str:
    descriptions_ja = {
        "Decision Card": "本番反映してよいかと、その判断理由をまとめています。",
        "Production Readiness Card": "本番移行前に残っているブロッカーと注意事項を整理しています。",
        "Change Event Card": "今回の検査対象となった変更内容と再検査理由を示します。",
        "Document Corpus Card": "どの文書を根拠として検査したかを示します。",
        "Major Failures": "顧客影響が大きい失敗だけを優先順で表示します。",
        "Report Preview": "顧客提出用の要約レポートを確認できます。",
        "Summary Card": "今回の run の件数と合格率をまとめています。",
        "Scope Card": "今回の検査範囲と対象情報を示します。",
        "Gate Details": "判定器や比較情報などの補足情報です。",
        "Review Packet": "release review 用の要約情報です。",
        "Failure": "この失敗の要点を確認できます。",
    }
    descriptions_en = {
        "Decision Card": "This card explains whether release should proceed and why.",
        "Production Readiness Card": "This card summarizes blockers and warnings before production migration.",
        "Change Event Card": "This card shows what changed and why this run was retested.",
        "Document Corpus Card": "This card shows which documents were used as review evidence.",
        "Major Failures": "This card highlights the most important customer-facing failures first.",
        "Report Preview": "This card links to the customer-facing report preview.",
        "Summary Card": "This card summarizes case counts and pass rates for the run.",
        "Scope Card": "This card shows the scoped target and review inputs.",
        "Gate Details": "This card keeps supplementary gate and comparison details.",
        "Review Packet": "This section contains release review information for this run.",
        "Failure": "This card summarizes the selected failure.",
    }
    items = descriptions_ja if lang == "ja" else descriptions_en
    return items.get(title, "")


def _badge_tone(value: object) -> str:
    normalized = _normalize_code(value)
    if normalized in {
        "no_go",
        "not_ready",
        "critical",
        "block",
        "blocks_release",
        "fail",
    }:
        return "danger"
    if normalized in {
        "conditional",
        "needs_human_review",
        "requires_human_review",
        "high",
        "warning",
    }:
        return "warning"
    if normalized in {"go", "ready", "pass", "approved", "success"}:
        return "success"
    if normalized in {"medium", "informational", "needs_fix_or_review"}:
        return "accent"
    return "neutral"


def _badge_html(text: str, *, tone: str | None = None, small: bool = False) -> str:
    if not text:
        return ""
    size_class = " badge--small" if small else ""
    return f"<span class='badge badge--{tone or 'neutral'}{size_class}'>{_esc(text)}</span>"


def _value_badge(value: object, *, lang: str, show_raw: bool = False, small: bool = False) -> str:
    translated = _translate_value(lang, value, show_raw=show_raw)
    return _badge_html(translated, tone=_badge_tone(value), small=small)


def _card_html(
    title: str,
    body: str,
    *,
    lang: str,
    description: str = "",
    badge_html: str = "",
    tone: str = "default",
    extra_class: str = "",
) -> str:
    description_text = description or _card_description(lang, title)
    description_html = (
        f"<p class='card__description'>{_esc(description_text)}</p>" if description_text else ""
    )
    extra = f" {extra_class}" if extra_class else ""
    badge_block = f"<div class='card__badge'>{badge_html}</div>" if badge_html else ""
    return (
        f"<section class='card card--{tone}{extra}'>"
        "<div class='card__header'>"
        "<div>"
        f"<h2 class='card__title'>{_esc(_tr(lang, title))}</h2>"
        f"{description_html}"
        "</div>"
        f"{badge_block}"
        "</div>"
        f"<div class='card__body'>{body}</div>"
        "</section>"
    )


def _label_text(lang: str, ja: str, en: str) -> str:
    return ja if lang == "ja" else en


def _meta_item_html(label: str, value_html: str) -> str:
    return (
        "<div class='meta-item'>"
        f"<span class='meta-item__label'>{_esc(label)}</span>"
        f"<div class='meta-item__value'>{value_html}</div>"
        "</div>"
    )


def _hero_panel_html(label: str, body_html: str) -> str:
    return (
        "<div class='hero__panel'>"
        f"<span class='hero__label'>{_esc(label)}</span>"
        f"{body_html}"
        "</div>"
    )


def _run_customer_status(run: dict[str, Any]) -> str:
    packet = run.get("review_packet")
    if isinstance(packet, dict) and packet:
        decision = packet.get("decision") if isinstance(packet.get("decision"), dict) else {}
        status = str(
            decision.get("customer_status")
            or decision.get("status")
            or run.get("policy_status")
            or ""
        ).strip()
        if status:
            return status
    normalized = _normalize_code(run.get("policy_status") or run.get("status"))
    if normalized in {"block", "fail", "no_go"}:
        return "No-Go"
    if normalized in {"conditional", "needs_human_review", "review"}:
        return "Conditional"
    if normalized in {"go", "pass", "ready"}:
        return "Go"
    return str(run.get("policy_status") or run.get("status") or "unknown")


def _run_readiness_status(run: dict[str, Any]) -> str:
    packet = run.get("review_packet")
    if isinstance(packet, dict) and packet:
        readiness = (
            packet.get("production_readiness")
            if isinstance(packet.get("production_readiness"), dict)
            else {}
        )
        status = str(readiness.get("status") or "").strip()
        if status:
            return status
    return "unknown"


def _review_stage_display(stage: object, *, lang: str) -> str:
    return _translate_value(lang, stage or "unknown")


def _review_stage_description(stage: object, *, lang: str) -> str:
    normalized = _normalize_code(stage)
    if lang != "ja":
        if normalized == "pre_delivery":
            return "This review checks AI answer quality before delivery."
        if normalized == "post_delivery_change":
            return "This review checks whether changes broke AI answers after delivery."
        if normalized == "monthly_review":
            return "This review summarizes AI answer quality for monthly operations."
        return "This review summarizes the scoped quality gate result."
    if normalized == "pre_delivery":
        return "このレビューは、納品前にAI回答品質を確認するためのものです。No-Goの場合は、顧客提出ではなく社内で改善・再検査してください。"
    if normalized == "post_delivery_change":
        return "このレビューは、FAQ・料金表・規約・プロンプトなどの変更後に、AI回答が壊れていないか確認するためのものです。"
    if normalized == "monthly_review":
        return "このレビューは、保守契約や月次報告でAI回答品質の状態を確認するためのものです。"
    return "このレビューは、設定された検査範囲に対する品質ゲート結果です。"


def _customer_report_title_for_stage(stage: object, *, lang: str) -> str:
    normalized = _normalize_code(stage)
    if lang != "ja":
        if normalized == "pre_delivery":
            return "AI Answer Quality Diagnostic Report"
        if normalized == "post_delivery_change":
            return "Change Impact Quality Review"
        if normalized == "monthly_review":
            return "Monthly Quality Review"
        return "Customer Review"
    if normalized == "pre_delivery":
        return "AI回答品質診断レポート"
    if normalized == "post_delivery_change":
        return "変更後品質確認レポート"
    if normalized == "monthly_review":
        return "月次AI回答品質レビュー"
    return "顧客向けレビュー"


def _submission_status_reason(packet: dict[str, Any], *, lang: str) -> list[str]:
    decision = packet.get("decision", {}) if isinstance(packet.get("decision"), dict) else {}
    delivery = (
        packet.get("delivery_review", {}) if isinstance(packet.get("delivery_review"), dict) else {}
    )
    submission = (
        packet.get("customer_submission_readiness", {})
        if isinstance(packet.get("customer_submission_readiness"), dict)
        else {}
    )
    blocking_items = packet.get("blocking_items", [])
    if not isinstance(blocking_items, list):
        blocking_items = []
    status = _normalize_code(submission.get("status"))
    decision_status = _normalize_code(decision.get("customer_status") or decision.get("status"))
    unresolved_s1 = int(delivery.get("unresolved_s1_count") or 0)
    unresolved_s2 = int(delivery.get("unresolved_s2_count") or 0)
    if lang != "ja":
        reasons: list[str] = []
        if decision_status == "no_go":
            reasons.append("The gate decision is No-Go.")
        if unresolved_s1:
            reasons.append(f"{unresolved_s1} unresolved S1 blocker(s) remain.")
        if unresolved_s2:
            reasons.append(f"{unresolved_s2} unresolved S2 item(s) remain.")
        if status == "conditional":
            reasons.append("Conditional submission requires documented residual risk.")
        if not reasons:
            reasons.append("The customer-facing output uses safe information only.")
        return reasons
    reasons = []
    if decision_status == "no_go":
        reasons.append("判定が本番反映不可です。")
    if unresolved_s1:
        reasons.append(f"未解決S1が {unresolved_s1} 件残っています。")
    if unresolved_s2:
        reasons.append(f"未解決S2が {unresolved_s2} 件残っています。")
    if status == "conditional":
        reasons.append("条件付きのため、残留リスクの明記が必要です。")
    if not reasons:
        reasons.append("顧客向けにはsafe情報のみで構成されています。")
    return reasons


def _stage_improvement_steps(stage: object, *, lang: str) -> list[str]:
    normalized = _normalize_code(stage)
    if lang != "ja":
        base = [
            "Review unresolved S1/S2 blockers.",
            "Fix failures in refund, cancellation, pricing, and document-corpus categories.",
            "Check evidence documents and document versions.",
            "Update the RAG index, retriever, prompt, or source documents.",
            "Rerun the gate with the same review_stage.",
        ]
        if normalized == "pre_delivery":
            return base + ["For No-Go, keep this internal and rerun before customer submission."]
        if normalized == "post_delivery_change":
            return base + ["Prioritize mismatch between the change event and document corpus."]
        if normalized == "monthly_review":
            return base + ["Compare residual risk and quality trend against the previous review."]
        return base
    base = [
        "未解決S1/S2ブロッカーを確認する",
        "返金・解約・料金・文書コーパスに関する失敗を修正する",
        "根拠文書と文書バージョンを確認する",
        "RAGのindex / retriever / prompt / 文書を修正する",
        "同じreview_stageで再検査する",
    ]
    if normalized == "pre_delivery":
        return base + ["納品前診断のNo-Goは顧客提出せず、社内で修正・再検査する"]
    if normalized == "post_delivery_change":
        return base + ["変更内容と文書コーパスの不一致を優先確認する"]
    if normalized == "monthly_review":
        return base + ["残留リスクと前回からの変化を確認する"]
    return base


def _action_priority(index: int, action: str) -> str:
    normalized = action.lower()
    if index == 0 or any(
        token in normalized for token in ("critical", "blocking", "blocker", "s1", "no-go")
    ):
        return "最優先"
    if index <= 2 or any(
        token in normalized for token in ("source of truth", "stale", "human review", "changeevent")
    ):
        return "高"
    return "中"


def _action_category(action: str, blocker: dict[str, Any] | None = None) -> str:
    if blocker and blocker.get("category"):
        return str(blocker.get("category"))
    normalized = action.lower()
    if "refund" in normalized:
        return "refund"
    if "cancellation" in normalized:
        return "cancellation"
    if "pricing" in normalized:
        return "pricing"
    if any(
        token in normalized for token in ("document", "source of truth", "stale", "changeevent")
    ):
        return "document_corpus"
    if "human review" in normalized:
        return "human_review"
    return "quality_gate"


def _action_owner(category: str, action: str, *, lang: str) -> str:
    normalized = f"{category} {action}".lower()
    if lang != "ja":
        if "human_review" in normalized or "customer" in normalized:
            return "PM / Customer reviewer"
        if "document" in normalized or "source" in normalized:
            return "PM / QA"
        return "Engineer / QA"
    if "human_review" in normalized or "customer" in normalized:
        return "PM / 顧客確認"
    if "document" in normalized or "source" in normalized:
        return "PM / QA"
    return "エンジニア / QA"


def _action_next_state(category: str, action: str, *, lang: str) -> str:
    normalized = f"{category} {action}".lower()
    if lang != "ja":
        if "human_review" in normalized or "customer" in normalized:
            return "Waiting for review"
        if "document" in normalized or "source" in normalized:
            return "Document update required"
        return "Rerun after fix"
    if "human_review" in normalized or "customer" in normalized:
        return "顧客確認待ち"
    if "document" in normalized or "source" in normalized:
        return "文書更新が必要"
    return "修正後に再検査"


def _action_reason(action: str, blocker: dict[str, Any] | None = None, *, lang: str) -> str:
    if blocker:
        issue = blocker.get("issue") or blocker.get("category")
        return _translate_issue_reason(issue, issue, lang=lang)
    category = _action_category(action)
    if lang != "ja":
        if category == "document_corpus":
            return "The source documents or change metadata are not sufficiently controlled."
        if category == "human_review":
            return "A human decision is required before this run can be used as release evidence."
        return "This action reduces release or customer-submission risk."
    if category == "document_corpus":
        return "正本・文書鮮度・変更影響が曖昧だと、回答品質の判断根拠が弱くなります。"
    if category == "human_review":
        return "自動判定だけではリリース証跡として扱えないため、担当者確認が必要です。"
    return "本番反映または顧客提出のリスクを下げるために必要です。"


def _render_summary_hero(run: dict[str, Any], *, lang: str) -> str:
    packet = run.get("review_packet")
    decision_status = _run_customer_status(run)
    readiness_status = _run_readiness_status(run)
    tone = _badge_tone(decision_status)
    primary_reason = "-"
    headline = "-"
    actions: list[str] = []
    if isinstance(packet, dict) and packet:
        decision = packet.get("decision") if isinstance(packet.get("decision"), dict) else {}
        explanation = (
            packet.get("decision_explanation")
            if isinstance(packet.get("decision_explanation"), dict)
            else {}
        )
        blocking = explanation.get("blocking_reasons", [])
        if not isinstance(blocking, list):
            blocking = []
        readiness = (
            packet.get("production_readiness")
            if isinstance(packet.get("production_readiness"), dict)
            else {}
        )
        headline = _translate_decision_headline(decision, explanation, blocking, lang=lang)
        primary_reason = _translate_decision_reason_text(decision, explanation, blocking, lang=lang)
        actions = _unique_texts(
            _decision_action_items(explanation, blocking, lang=lang)
            + _readiness_action_items(readiness, lang=lang)
        )[:2]
    else:
        decision = run.get("decision") if isinstance(run.get("decision"), dict) else {}
        reasons = decision.get("reasons", []) if isinstance(decision.get("reasons"), list) else []
        next_actions = (
            decision.get("next_actions", [])
            if isinstance(decision.get("next_actions"), list)
            else []
        )
        primary_reason = _translate_reason_item(reasons[0], lang=lang) if reasons else "-"
        headline = primary_reason
        actions = _unique_texts(
            [
                (
                    f"{_translate_issue_label(item.get('failure_category'), item.get('failure_category'), lang=lang, show_raw=True)}: "
                    f"{_translate_issue_action(item.get('failure_category'), item.get('action'), lang=lang)}"
                )
                for item in next_actions
                if isinstance(item, dict)
            ]
        )[:2]

    corpus = packet.get("document_corpus") if isinstance(packet, dict) else {}
    if not isinstance(corpus, dict):
        corpus = {}
    document_count = int(corpus.get("document_count") or 0)
    report_sections = packet.get("report_sections") if isinstance(packet, dict) else {}
    report_available = isinstance(report_sections, dict) and bool(report_sections)
    delivery = packet.get("delivery_review") if isinstance(packet, dict) else {}
    if not isinstance(delivery, dict):
        delivery = {}
    submission = packet.get("customer_submission_readiness") if isinstance(packet, dict) else {}
    if not isinstance(submission, dict):
        submission = {}
    review_stage = packet.get("review_stage", "unknown") if isinstance(packet, dict) else "unknown"
    blocking_items = packet.get("blocking_items", []) if isinstance(packet, dict) else []
    if not isinstance(blocking_items, list):
        blocking_items = []
    top_blockers = [
        _translate_issue_label(
            item.get("issue") or item.get("category"),
            item.get("issue") or item.get("category") or "-",
            lang=lang,
            show_raw=True,
        )
        for item in blocking_items
        if isinstance(item, dict)
    ][:2]
    blocker_html = (
        "<ul class='hero__list'>"
        + "".join(f"<li>{_esc(item)}</li>" for item in top_blockers)
        + "</ul>"
        if top_blockers
        else f"<p class='muted'>{_esc(_tr(lang, 'None'))}</p>"
    )
    report_badge = _badge_html(
        (
            _label_text(lang, "利用可能", "Available")
            if report_available
            else _label_text(lang, "未作成", "Unavailable")
        ),
        tone="success" if report_available else "neutral",
    )
    action_html = (
        "<ul class='hero__list'>" + "".join(f"<li>{_esc(item)}</li>" for item in actions) + "</ul>"
        if actions
        else f"<p class='muted'>{_esc(_tr(lang, 'None'))}</p>"
    )
    evidence_html = (
        f"<p>{_esc(_label_text(lang, f'根拠文書 {document_count} 件', f'{document_count} evidence document(s)'))}</p>"
        f"<div class='badge-row'>{report_badge}</div>"
    )
    overview_html = (
        "<div class='meta-grid hero__meta'>"
        + _meta_item_html(
            _tr(lang, "Review stage"),
            _value_badge(review_stage, lang=lang, show_raw=True),
        )
        + _meta_item_html(
            _tr(lang, "Decision"),
            _value_badge(decision_status, lang=lang, show_raw=True),
        )
        + _meta_item_html(
            _tr(lang, "Formal submission readiness"),
            _value_badge(submission.get("status", "not_recommended"), lang=lang, show_raw=True),
        )
        + _meta_item_html(
            _tr(lang, "Production Readiness"),
            _value_badge(readiness_status, lang=lang, show_raw=True),
        )
        + _meta_item_html(_tr(lang, "Unresolved S1"), _esc(delivery.get("unresolved_s1_count", 0)))
        + _meta_item_html(_tr(lang, "Unresolved S2"), _esc(delivery.get("unresolved_s2_count", 0)))
        + "</div>"
    )
    return (
        f"<section class='hero hero--{tone}'>"
        f"<p class='hero__eyebrow'>{_esc(_label_text(lang, '本番移行判断', 'Release Decision'))}</p>"
        f"<div class='badge-row'>{_value_badge(decision_status, lang=lang)}{_value_badge(readiness_status, lang=lang)}</div>"
        f"<h2 class='hero__title'>{_esc(_translate_value(lang, decision_status) or decision_status)}</h2>"
        f"<p class='hero__summary'>{_esc(primary_reason)}</p>"
        "<div class='hero__grid'>"
        + _hero_panel_html(
            _label_text(lang, "主要理由", "Primary Reason"),
            f"<p>{_esc(headline)}</p>",
        )
        + _hero_panel_html(_label_text(lang, "次にやること", "Next Steps"), action_html)
        + _hero_panel_html(
            _label_text(lang, "根拠とレポート", "Evidence and Report"), evidence_html
        )
        + "</div></section>"
    )


def _render_report_preview_card(run: dict[str, Any], *, lang: str) -> str:
    packet = run.get("review_packet")
    sections = packet.get("report_sections") if isinstance(packet, dict) else {}
    submission = (
        packet.get("customer_submission_readiness", {})
        if isinstance(packet, dict)
        and isinstance(packet.get("customer_submission_readiness"), dict)
        else {}
    )
    available = isinstance(sections, dict) and bool(sections)
    description = _label_text(
        lang,
        "顧客向けに共有できる要約レポートの入口です。",
        "This card links to the customer-facing report summary.",
    )
    if available:
        link_text = _label_text(lang, "顧客提出レポートを開く", "Open Report Preview")
        readiness = str(submission.get("status") or "not_recommended")
        readiness_note = (
            "Formal submission is not recommended; treat this as a safe interim draft."
            if readiness == "not_recommended"
            else str(submission.get("recommendation") or "Customer report preview is available.")
        )
        body = (
            f"<p>{_esc(readiness_note)}</p>"
            f"<p><a class='link-button' href='{_run_href(run['run_id'], lang, '/report-preview')}'>{_esc(link_text)}</a></p>"
            f"<p><a class='link-button' href='{_run_href(run['run_id'], lang, '/customer-review.md')}'>Download Customer Review Markdown</a></p>"
        )
        badge_tone = "success" if readiness == "recommended" else "warning"
        badge = _badge_html(readiness, tone=badge_tone)
        return _card_html(
            "Report Preview", body, lang=lang, description=description, badge_html=badge
        )
    body = f"<p>{_esc(_label_text(lang, 'この run では顧客提出レポートを利用できません。', 'No customer-facing report is available for this run.'))}</p>"
    badge = _badge_html(_label_text(lang, "未作成", "Unavailable"), tone="neutral")
    return _card_html("Report Preview", body, lang=lang, description=description, badge_html=badge)


def _render_gate_details_card(run: dict[str, Any], *, lang: str) -> str:
    reliability = run.get("decision") if isinstance(run.get("decision"), dict) else {}
    comparison = run.get("history_summary", {}).get("comparison") or {}
    reasons = reliability.get("reasons", []) if isinstance(reliability.get("reasons"), list) else []
    next_actions = (
        reliability.get("next_actions", [])
        if isinstance(reliability.get("next_actions"), list)
        else []
    )
    reason_list = "".join(
        f"<li>{_esc(_translate_reason_item(item, lang=lang))}</li>" for item in reasons
    ) or _none_list_item(lang)
    action_list = "".join(
        f"<li>{_esc(_translate_issue_label(item.get('failure_category'), item.get('failure_category'), lang=lang, show_raw=True))}: {_esc(_translate_issue_action(item.get('failure_category'), item.get('action'), lang=lang))}</li>"
        for item in next_actions
        if isinstance(item, dict)
    ) or _none_list_item(lang)
    metrics = "".join(
        [
            _meta_item_html(
                _tr(lang, "Status"),
                _badge_html(str(run.get("status", "-")), tone=_badge_tone(run.get("status"))),
            ),
            _meta_item_html(
                _tr(lang, "Policy status"),
                _badge_html(
                    str(run.get("policy_status", "-")), tone=_badge_tone(_run_customer_status(run))
                ),
            ),
            _meta_item_html(
                _tr(lang, "Overall pass rate"),
                _esc("{:.1f}%".format(run.get("overall_pass_rate", 0.0))),
            ),
            _meta_item_html(
                _tr(lang, "S1 pass rate"), _esc("{:.1f}%".format(run.get("s1_pass_rate", 0.0)))
            ),
            _meta_item_html(
                _tr(lang, "S1 fail count"), _esc("{:.0f}".format(run.get("s1_fail_count", 0.0)))
            ),
            _meta_item_html(
                _tr(lang, "Judge reliability"),
                _value_badge(
                    reliability.get("judge_reliability", "unknown"), lang=lang, small=True
                ),
            ),
            _meta_item_html(
                _tr(lang, "Needs human review"),
                _value_badge(reliability.get("needs_human_review", False), lang=lang, small=True),
            ),
            _meta_item_html(
                _tr(lang, "Previous diff"),
                _esc(
                    f"{comparison.get('previous_run_id', '-')} -> {comparison.get('current_run_id', '-')}"
                ),
            ),
        ]
    )
    body = (
        f"<div class='meta-grid'>{metrics}</div>"
        f"<p class='section-label'>{_esc(_tr(lang, 'Reasons'))}</p><ul>{reason_list}</ul>"
        f"<p class='section-label'>{_esc(_tr(lang, 'Next Actions'))}</p><ul>{action_list}</ul>"
    )
    return _card_html("Gate Details", body, lang=lang)


def _split_report_preview_lines(text: str, *, lang: str) -> list[str]:
    raw = str(text or "").strip()
    if not raw or raw == "-":
        return []
    if " / " in raw:
        return [item.strip() for item in raw.split(" / ") if item.strip()]
    if lang == "ja":
        items = [item.strip() for item in re.split(r"。\s*", raw) if item.strip()]
        return [f"{item}。" for item in items]
    items = [item.strip() for item in re.split(r"[.;]\s*", raw) if item.strip()]
    return [f"{item}." for item in items]


def _render_report_preview_section(
    title: str, text: str, *, lang: str, list_first: bool = False
) -> str:
    lines = _split_report_preview_lines(text, lang=lang)
    summary = ""
    points: list[str] = []
    if list_first:
        points = lines or ([text] if text and text != "-" else [])
        if points:
            summary = _label_text(lang, "主なポイント", "Key Points")
    elif lines:
        summary = lines[0]
        points = lines[1:]
    else:
        summary = text
    points_html = (
        "<ul class='report-points'>"
        + "".join(f"<li>{_esc(item)}</li>" for item in points)
        + "</ul>"
        if points
        else ""
    )
    return (
        "<section class='report-section'>"
        f"<h2 class='report-section__title'>{_esc(_tr(lang, title))}</h2>"
        f"<p class='report-section__summary'>{_esc(summary or '-')}</p>"
        f"{points_html}"
        "</section>"
    )


def _href(path: str, lang: str) -> str:
    separator = "&" if "?" in path else "?"
    return f"{path}{separator}lang={lang}"


def _page_title_run(lang: str, run_id: str) -> str:
    if lang == "ja":
        return f"{_tr(lang, 'Run Detail')} {run_id}"
    return f"Run {run_id}"


def _page_title_report_preview(lang: str, run_id: str) -> str:
    if lang == "ja":
        return f"{_tr(lang, 'Report Preview')} {run_id}"
    return f"Report Preview {run_id}"


def _page_title_failure(lang: str, failure_id: str) -> str:
    if lang == "ja":
        return f"{_tr(lang, 'Failure')} {failure_id}"
    return f"Failure {failure_id}"


def create_dashboard_app(
    *,
    workspace_dir: str,
    runs_dir: str | None = None,
) -> FastAPI:
    app = FastAPI(title="Proof Gate Dashboard", version="0.1.0")
    app.state.workspace_dir = Path(workspace_dir)
    app.state.runs_dir = Path(runs_dir) if runs_dir else Path(workspace_dir) / "runs"

    @app.get("/", response_class=HTMLResponse)
    @app.get("/packs", response_class=HTMLResponse)
    def pack_list(request: Request) -> str:
        lang = _dashboard_lang(request)
        packs = _scan_packs(app.state.workspace_dir)
        runs = _scan_runs(app.state.runs_dir)
        latest_by_pack = _latest_runs_by_pack(runs)
        rows = []
        for pack in packs:
            pack_id = _pack_id(pack)
            latest = latest_by_pack.get(pack_id) or latest_by_pack.get(pack["pack_name"])
            rows.append(
                "<tr>"
                f"<td><a href='{_href(f'/packs/{_esc(pack_id)}', lang)}'>{_esc(pack.get('pack_name') or pack_id)}</a></td>"
                f"<td>{_esc(pack.get('use_case', '-'))}</td>"
                f"<td>{_esc(pack.get('vertical', '-'))}</td>"
                f"<td>{_esc(pack.get('risk_profile', '-'))}</td>"
                f"<td>{_esc(latest.get('policy_status', latest['status']) if latest else '-')}</td>"
                f"<td>{_esc(latest['run_id'] if latest else '-')}</td>"
                f"<td>{_esc('{:.0f}'.format(latest['s1_fail_count']) if latest else '-')}</td>"
                f"<td>{_esc(_tr(lang, 'YES') if latest and latest.get('fallback_used') else _tr(lang, 'NO'))}</td>"
                "</tr>"
            )
        return _page(
            _tr(lang, "Packs"),
            "<table><tr>"
            f"<th>{_esc(_tr(lang, 'Pack'))}</th>"
            f"<th>{_esc(_tr(lang, 'Use Case'))}</th>"
            f"<th>{_esc(_tr(lang, 'Vertical'))}</th>"
            f"<th>{_esc(_tr(lang, 'Risk'))}</th>"
            f"<th>{_esc(_tr(lang, 'Latest Gate'))}</th>"
            f"<th>{_esc(_tr(lang, 'Latest Run'))}</th>"
            f"<th>{_esc(_tr(lang, 'S1 Fails'))}</th>"
            f"<th>{_esc(_tr(lang, 'Fallback'))}</th></tr>" + "".join(rows) + "</table>",
            lang=lang,
            current_path=str(request.url.path),
        )

    @app.get("/packs/{pack_name}", response_class=HTMLResponse)
    def pack_detail(pack_name: str, request: Request) -> str:
        lang = _dashboard_lang(request)
        packs = {_pack_id(pack): pack for pack in _scan_packs(app.state.workspace_dir)}
        pack = packs.get(pack_name)
        if pack is None:
            raise HTTPException(status_code=404, detail="Pack not found")
        runs = [run for run in _scan_runs(app.state.runs_dir) if run["pack_id"] == pack_name]
        latest = runs[-1] if runs else None
        metadata_lines = "".join(
            f"<li><strong>{_esc(key)}</strong>: {_esc(value)}</li>"
            for key, value in sorted(pack.items())
            if key not in {"path"}
        )
        if latest:
            latest_run_id = _esc(latest["run_id"])
            latest_status = _esc(latest["status"])
            latest_href = _href(f"/packs/{_esc(pack_name)}/runs/{latest_run_id}", lang)
            latest_html = (
                f"<p>{_esc(_tr(lang, 'Latest gate'))}: "
                f"<a href='{latest_href}'>{latest_status}</a></p>"
            )
        else:
            latest_html = f"<p>{_esc(_tr(lang, 'No runs found.'))}</p>"
        nav = (
            f"<p><a href='{_href(f'/packs/{_esc(pack_name)}/runs', lang)}'>{_esc(_tr(lang, 'Runs'))}</a> | "
            f"<a href='{_href(f'/packs/{_esc(pack_name)}/latest', lang)}'>{_esc(_tr(lang, 'Latest gate'))}</a> | "
            f"<a href='{_href(f'/packs/{_esc(pack_name)}/fail-cases', lang)}'>{_esc(_tr(lang, 'Major Failures'))}</a> | "
            f"<a href='{_href(f'/packs/{_esc(pack_name)}/monthly', lang)}'>{_esc(_tr(lang, 'Monthly summary'))}</a></p>"
        )
        return _page(
            pack_name,
            nav + latest_html + f"<ul>{metadata_lines}</ul>",
            lang=lang,
            current_path=str(request.url.path),
        )

    @app.get("/packs/{pack_name}/runs", response_class=HTMLResponse)
    @app.get("/runs", response_class=HTMLResponse)
    def run_list(request: Request, pack_name: str = "") -> str:
        lang = _dashboard_lang(request)
        all_runs = _scan_runs(app.state.runs_dir)
        runs = (
            all_runs
            if pack_name == ""
            else [
                run
                for run in all_runs
                if run["pack_id"] == pack_name or run["pack_name"] == pack_name
            ]
        )
        if not runs:
            raise HTTPException(status_code=404, detail="No runs found for pack")
        rows = []
        for run in reversed(runs):
            run_id = _esc(run["run_id"])
            run_href = _href(f"/runs/{run_id}", lang)
            rows.append(
                "<tr>"
                f"<td><a href='{run_href}'>{run_id}</a></td>"
                f"<td>{_esc(run['pack_id'])}</td>"
                f"<td>{_esc(run.get('policy_status', run['status']))}</td>"
                f"<td>{_esc('{:.1f}%'.format(run['overall_pass_rate']))}</td>"
                f"<td>{_esc('{:.1f}%'.format(run['s1_pass_rate']))}</td>"
                f"<td>{_esc('{:.0f}'.format(run['s1_fail_count']))}</td>"
                f"<td>{_esc(run['decision'].get('judge_reliability', 'unknown'))}</td>"
                "</tr>"
            )
        return _page(
            (
                (
                    f"{_tr(lang, 'Runs')} {pack_name}"
                    if lang == "ja" and pack_name
                    else f"Runs for {pack_name}"
                )
                if pack_name
                else _tr(lang, "Runs")
            ),
            "<table><tr>"
            f"<th>{_esc(_tr(lang, 'Run'))}</th>"
            f"<th>{_esc(_tr(lang, 'Pack'))}</th>"
            f"<th>{_esc(_tr(lang, 'Status'))}</th>"
            f"<th>{_esc('Overall' if lang == 'en' else '全体')}</th>"
            f"<th>{_esc('S1')}</th>"
            f"<th>{_esc(_tr(lang, 'S1 Fails'))}</th>"
            f"<th>{_esc(_tr(lang, 'Judge reliability'))}</th></tr>" + "".join(rows) + "</table>",
            lang=lang,
            current_path=str(request.url.path),
        )

    @app.get("/packs/{pack_name}/runs/{run_id}", response_class=HTMLResponse)
    @app.get("/runs/{run_id}", response_class=HTMLResponse)
    def run_detail(request: Request, run_id: str, pack_name: str = "") -> str:
        lang = _dashboard_lang(request)
        run = _find_run(_scan_runs(app.state.runs_dir), pack_name=pack_name, run_id=run_id)
        review_packet = run.get("review_packet")
        review_html = (
            _render_review_packet_run_detail(run, lang=lang)
            if isinstance(review_packet, dict) and review_packet
            else (
                _card_html(
                    "Review Packet",
                    f"<p>{_esc(_tr(lang, 'ReviewPacket is not available for this run.'))}</p>",
                    lang=lang,
                    tone="warning",
                    badge_html=_badge_html(
                        _label_text(lang, "未搭載", "Unavailable"), tone="neutral"
                    ),
                )
                + _render_report_preview_card(run, lang=lang)
            )
        )
        return _page(
            _page_title_run(lang, run_id),
            (
                (
                    ""
                    if isinstance(review_packet, dict) and review_packet
                    else f"{_render_summary_hero(run, lang=lang)}"
                )
                + "<div class='stack'>"
                + review_html
                + _render_gate_details_card(run, lang=lang)
                + "</div>"
            ),
            lang=lang,
            current_path=str(request.url.path),
        )

    @app.get("/packs/{pack_name}/runs/{run_id}/failures/{failure_id}", response_class=HTMLResponse)
    @app.get("/runs/{run_id}/failures/{failure_id}", response_class=HTMLResponse)
    def failure_detail(request: Request, run_id: str, failure_id: str, pack_name: str = "") -> str:
        lang = _dashboard_lang(request)
        run = _find_run(_scan_runs(app.state.runs_dir), pack_name=pack_name, run_id=run_id)
        failure = _find_review_failure(run, failure_id)
        if failure is None:
            raise HTTPException(status_code=404, detail="Failure not found")
        return _page(
            _page_title_failure(lang, failure_id),
            _render_failure_detail(run=run, failure=failure, lang=lang),
            lang=lang,
            current_path=str(request.url.path),
        )

    @app.get("/packs/{pack_name}/runs/{run_id}/report-preview", response_class=HTMLResponse)
    @app.get("/runs/{run_id}/report-preview", response_class=HTMLResponse)
    def report_preview(request: Request, run_id: str, pack_name: str = "") -> str:
        lang = _dashboard_lang(request)
        run = _find_run(_scan_runs(app.state.runs_dir), pack_name=pack_name, run_id=run_id)
        review_packet = run.get("review_packet")
        if not isinstance(review_packet, dict) or not review_packet:
            raise HTTPException(status_code=404, detail="ReviewPacket not found")
        return _page(
            _page_title_report_preview(lang, run_id),
            _render_report_preview(run, lang=lang),
            lang=lang,
            current_path=str(request.url.path),
        )

    @app.get(
        "/packs/{pack_name}/runs/{run_id}/customer-review.md", response_class=PlainTextResponse
    )
    @app.get("/runs/{run_id}/customer-review.md", response_class=PlainTextResponse)
    def customer_review_markdown(run_id: str, pack_name: str = "") -> str:
        run = _find_run(_scan_runs(app.state.runs_dir), pack_name=pack_name, run_id=run_id)
        review_packet = run.get("review_packet")
        if not isinstance(review_packet, dict) or not review_packet:
            raise HTTPException(status_code=404, detail="ReviewPacket not found")
        return build_customer_review_markdown(review_packet)

    @app.get("/packs/{pack_name}/latest", response_class=HTMLResponse)
    def latest_gate(pack_name: str, request: Request) -> str:
        runs = [run for run in _scan_runs(app.state.runs_dir) if run["pack_name"] == pack_name]
        if not runs:
            raise HTTPException(status_code=404, detail="No runs found for pack")
        latest = runs[-1]
        return run_detail(request, latest["run_id"], pack_name)

    @app.get("/packs/{pack_name}/fail-cases", response_class=HTMLResponse)
    @app.get("/cases/failures", response_class=HTMLResponse)
    def fail_cases(request: Request, pack_name: str = "") -> str:
        lang = _dashboard_lang(request)
        all_runs = _scan_runs(app.state.runs_dir)
        runs = (
            all_runs
            if pack_name == ""
            else [
                run
                for run in all_runs
                if run["pack_id"] == pack_name or run["pack_name"] == pack_name
            ]
        )
        if not runs:
            raise HTTPException(status_code=404, detail="No runs found for pack")
        fail_case_rows = []
        for run in reversed(runs):
            policy_status = str(run.get("policy_status", run["status"])).lower()
            status = str(run["status"]).lower()
            if status != "fail" and policy_status not in {
                "block",
                "needs_human_review",
            }:
                continue
            for action in run["decision"].get("next_actions", []):
                case_ids = ", ".join(action.get("affected_case_ids", [])) or "-"
                fallback_summary = run["decision"].get("fallback_summary", {})
                origin = "-"
                if isinstance(fallback_summary, dict):
                    origin = str(fallback_summary.get("block_origin") or "-")
                fail_case_rows.append(
                    "<tr>"
                    f"<td>{_esc(run['run_id'])}</td>"
                    f"<td>{_esc(run.get('policy_status', run['status']))}</td>"
                    f"<td>{_esc(origin)}</td>"
                    f"<td>{_esc(_translate_failure_pattern(action.get('failure_category', '-'), lang=lang, show_raw=True))}</td>"
                    f"<td>{_esc(case_ids)}</td>"
                    f"<td>{_esc(_translate_issue_action(action.get('failure_category'), action.get('action', '-'), lang=lang))}</td>"
                    "</tr>"
                )
        if not fail_case_rows:
            fail_case_rows.append(
                f'<tr><td colspan="6">{_esc(_tr(lang, "No failed or review-required cases found."))}</td></tr>'
            )
        return _page(
            (
                (
                    f"{_tr(lang, 'Major Failures')} {pack_name}"
                    if lang == "ja" and pack_name
                    else f"Fail cases for {pack_name}"
                )
                if pack_name
                else _tr(lang, "Major Failures")
            ),
            "<table><tr>"
            f"<th>{_esc(_tr(lang, 'Run'))}</th>"
            f"<th>{_esc(_tr(lang, 'Policy Status'))}</th>"
            f"<th>{_esc(_tr(lang, 'Origin'))}</th>"
            f"<th>{_esc(_tr(lang, 'Failure Category'))}</th>"
            f"<th>{_esc(_tr(lang, 'Affected Cases'))}</th>"
            f"<th>{_esc(_tr(lang, 'Recommended Action'))}</th></tr>"
            + "".join(fail_case_rows)
            + "</table>",
            lang=lang,
            current_path=str(request.url.path),
        )

    @app.get("/packs/{pack_name}/monthly", response_class=HTMLResponse)
    @app.get("/reports/monthly", response_class=HTMLResponse)
    def monthly(request: Request, pack_name: str = "customer_support_pack") -> str:
        lang = _dashboard_lang(request)
        monthly_file = app.state.runs_dir / pack_name / "monthly-summary.json"
        if monthly_file.exists():
            summary = json.loads(monthly_file.read_text(encoding="utf-8"))
        else:
            history_path = app.state.runs_dir / pack_name / "gate-decisions.jsonl"
            summary = build_monthly_summary_payload(load_gate_decision_history(history_path))
        unresolved_items = summary.get("unresolved_issue_reasons", [])
        if not isinstance(unresolved_items, list):
            unresolved_items = []
        unresolved = "".join(
            f"<li>{_esc(_translate_reason_item(item, lang=lang))}</li>" for item in unresolved_items
        )
        return _page(
            (
                f"{_tr(lang, 'Monthly summary')} {pack_name}"
                if lang == "ja"
                else f"Monthly summary for {pack_name}"
            ),
            (
                f"<p>{_esc(_tr(lang, 'Total runs'))}: {_esc(summary.get('total_runs', 0))}</p>"
                f"<p>{_esc(_tr(lang, 'Blocked runs'))}: {_esc(summary.get('blocked_runs', 0))}</p>"
                f"<p>{_esc(_tr(lang, 'S1 incidents detected'))}: {_esc(summary.get('s1_incidents_detected', 0))}</p>"
                f"<p>{_esc(_tr(lang, 'Fallback trend'))}: {_esc(summary.get('fallback_trend', {}))}</p>"
                f"<p>{_esc(_tr(lang, 'Trend summary'))}: {_esc(_translate_message(lang, summary.get('quality_trend_summary', '-')))}</p>"
                f"<h3>{_esc(_tr(lang, 'Unresolved issues'))}</h3><ul>{unresolved or _none_list_item(lang)}</ul>"
            ),
            lang=lang,
            current_path=str(request.url.path),
        )

    return app


def _pack_id(pack: dict[str, Any]) -> str:
    return str(pack.get("pack_id") or pack.get("pack_name") or pack.get("name") or "").strip()


def _scan_packs(workspace_dir: Path) -> list[dict[str, Any]]:
    packs_dir = workspace_dir / "packs"
    items: list[dict[str, Any]] = []
    for quality_pack in sorted(packs_dir.glob("*/quality-pack.yml")):
        payload = yaml.safe_load(quality_pack.read_text(encoding="utf-8")) or {}
        pack = payload.get("pack", {}) if isinstance(payload, dict) else {}
        if not isinstance(pack, dict):
            continue
        item = dict(pack)
        item["pack_name"] = str(item.get("pack_name") or quality_pack.parent.name)
        item["path"] = str(quality_pack.parent)
        items.append(item)
    return items


def _scan_runs(runs_dir: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    report_files = sorted(
        list(runs_dir.glob("**/gate-report.json")) + list(runs_dir.glob("**/gate-report-ci.json"))
    )
    for report_file in report_files:
        payload = _load_json(report_file)
        decision = payload.get("decision", {})
        if not isinstance(decision, dict):
            continue
        pack = decision.get("pack", {})
        if not isinstance(pack, dict):
            pack = {}
        pack_id = (
            str(pack.get("pack_id") or pack.get("pack_name") or "").strip()
            or report_file.parent.name
        )
        pack_name = str(pack.get("pack_name", "")).strip() or pack_id
        metrics = decision.get("metrics", {}) if isinstance(decision.get("metrics"), dict) else {}
        fallback_used = bool(
            decision.get("judge_fallback_used") or decision.get("embedding_fallback_used")
        )
        items.append(
            {
                "pack_id": pack_id,
                "pack_name": pack_name,
                "run_id": str(decision.get("run_id", report_file.parent.name)),
                "status": str(decision.get("status", "unknown")).upper(),
                "policy_status": str(
                    decision.get("policy_status", decision.get("status", "unknown"))
                ).upper(),
                "overall_pass_rate": float(metrics.get("overall_pass_rate", 0.0) or 0.0),
                "s1_pass_rate": float(metrics.get("s1_pass_rate", 0.0) or 0.0),
                "s1_fail_count": float(metrics.get("s1_fail_count", 0.0) or 0.0),
                "fallback_used": fallback_used,
                "decision": decision,
                "history_summary": payload.get("history_summary", {}),
                "review_packet": payload.get("review_packet", {}),
                "report_file": str(report_file),
                "report_file_name": report_file.name,
                "path": str(report_file.parent),
            }
        )
    return sorted(items, key=lambda item: (item["pack_name"], item["run_id"]))


def _latest_runs_by_pack(runs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for run in runs:
        latest[run["pack_id"]] = run
        latest[run["pack_name"]] = run
    return latest


def _find_run(runs: list[dict[str, Any]], *, pack_name: str, run_id: str) -> dict[str, Any]:
    for run in runs:
        pack_matches = not pack_name or run["pack_name"] == pack_name or run["pack_id"] == pack_name
        if pack_matches and run["run_id"] == run_id:
            return run
    raise HTTPException(status_code=404, detail="Run not found")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _page(
    title: str,
    body: str,
    *,
    lang: str = _DEFAULT_DASHBOARD_LANG,
    current_path: str = "/packs",
) -> str:
    styles = """
    :root {
        --bg: #f4f1eb;
        --paper: #fffdf9;
        --paper-strong: #ffffff;
        --ink: #1f2933;
        --muted: #52606d;
        --line: #d7d0c4;
        --shadow: rgba(31, 41, 51, 0.08);
        --accent: #0f766e;
        --accent-soft: #d8f0ec;
        --danger: #b42318;
        --danger-soft: #fde7e4;
        --warning: #b45309;
        --warning-soft: #fff2dc;
        --success: #1d6b3c;
        --success-soft: #e1f3e8;
        --neutral-soft: #eef2f6;
    }
    * { box-sizing: border-box; }
    body {
        margin: 0;
        background: linear-gradient(180deg, #f8f4ed 0%, #f4f1eb 100%);
        color: var(--ink);
        font-family: "Segoe UI", "Yu Gothic UI", "Hiragino Sans", sans-serif;
        line-height: 1.65;
    }
    a { color: var(--accent); text-decoration: none; }
    a:hover { text-decoration: underline; }
    .page-shell {
        max-width: 1120px;
        margin: 0 auto;
        padding: 24px 20px 56px;
    }
    .page-topbar {
        display: flex;
        justify-content: space-between;
        gap: 16px;
        align-items: center;
        margin-bottom: 20px;
        flex-wrap: wrap;
    }
    .page-title {
        margin: 0;
        font-size: 2rem;
        line-height: 1.2;
        letter-spacing: -0.01em;
    }
    .page-nav, .page-links {
        display: flex;
        gap: 10px;
        align-items: center;
        flex-wrap: wrap;
        color: var(--muted);
        font-size: 0.95rem;
    }
    .hero {
        padding: 24px;
        border-radius: 20px;
        background: linear-gradient(135deg, #fff8ef 0%, #fffdf8 56%, #ffffff 100%);
        border: 1px solid var(--line);
        box-shadow: 0 12px 30px var(--shadow);
        margin-bottom: 22px;
    }
    .hero--danger { border-color: #f0b2aa; background: linear-gradient(135deg, #fff0ee 0%, #fff8f6 100%); }
    .hero--warning { border-color: #f3d08b; background: linear-gradient(135deg, #fff7e8 0%, #fffdf8 100%); }
    .hero--success { border-color: #b5dfc3; background: linear-gradient(135deg, #edf9f1 0%, #fffdf8 100%); }
    .hero__eyebrow {
        margin: 0 0 10px;
        color: var(--muted);
        font-size: 0.86rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
    }
    .hero__title {
        margin: 0 0 10px;
        font-size: clamp(1.9rem, 2.5vw, 2.4rem);
        line-height: 1.15;
    }
    .hero__summary {
        margin: 0 0 16px;
        font-size: 1.02rem;
        color: var(--ink);
    }
    .hero__grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 14px;
        margin-top: 16px;
    }
    .hero__meta { margin-top: 18px; }
    .hero__panel {
        padding: 14px 16px;
        background: rgba(255, 255, 255, 0.75);
        border: 1px solid rgba(15, 118, 110, 0.08);
        border-radius: 14px;
    }
    .hero__label {
        display: block;
        margin-bottom: 8px;
        color: var(--muted);
        font-size: 0.85rem;
        font-weight: 700;
    }
    .hero__list {
        margin: 0;
        padding-left: 18px;
    }
    .stack { display: grid; gap: 24px; }
    .card {
        background: var(--paper-strong);
        border: 1px solid var(--line);
        border-radius: 18px;
        box-shadow: 0 6px 20px var(--shadow);
        padding: 22px;
        margin: 0;
    }
    .card--danger { border-color: #efc1ba; }
    .card--warning { border-color: #efd49f; }
    .card--success { border-color: #c8e5d0; }
    .card__header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        gap: 16px;
        padding-bottom: 14px;
        margin-bottom: 16px;
        border-bottom: 1px solid #ebe4d8;
    }
    .card__title {
        margin: 0;
        font-size: 1.3rem;
        line-height: 1.25;
    }
    .card__description {
        margin: 8px 0 0;
        color: var(--muted);
        font-size: 0.95rem;
    }
    .card__body > :first-child { margin-top: 0; }
    .card__body > :last-child { margin-bottom: 0; }
    .meta-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: 14px;
    }
    .meta-item {
        padding: 12px 14px;
        background: var(--paper);
        border-radius: 12px;
        border: 1px solid #efe7da;
    }
    .meta-item__label {
        display: block;
        color: var(--muted);
        font-size: 0.82rem;
        font-weight: 700;
        margin-bottom: 6px;
    }
    .meta-item__value { font-size: 1rem; }
    .badge-row {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
    }
    .badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        border-radius: 999px;
        padding: 6px 11px;
        font-size: 0.84rem;
        font-weight: 700;
        border: 1px solid transparent;
        white-space: nowrap;
    }
    .badge--small { padding: 4px 8px; font-size: 0.76rem; }
    .badge--danger { color: var(--danger); background: var(--danger-soft); border-color: #efc1ba; }
    .badge--warning { color: var(--warning); background: var(--warning-soft); border-color: #efd49f; }
    .badge--success { color: var(--success); background: var(--success-soft); border-color: #bfe1ca; }
    .badge--accent { color: var(--accent); background: var(--accent-soft); border-color: #bfe1db; }
    .badge--neutral { color: #425466; background: var(--neutral-soft); border-color: #d2dae5; }
    table {
        width: 100%;
        border-collapse: collapse;
        margin-top: 8px;
    }
    th, td {
        padding: 14px 16px;
        text-align: left;
        vertical-align: top;
        border-bottom: 1px solid #ece5d9;
    }
    th {
        font-size: 0.86rem;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: var(--muted);
        background: #faf7f1;
    }
    tbody tr:hover, tr:hover td { background: #fffcf7; }
    p { margin: 0 0 12px; }
    ul, ol { margin: 0; padding-left: 20px; }
    li + li { margin-top: 8px; }
    .ordered-list li { padding-left: 4px; }
    .muted { color: var(--muted); }
    .micro { color: var(--muted); font-size: 0.82rem; }
    .report-sections { display: grid; gap: 16px; }
    .report-section {
        padding: 18px;
        border: 1px solid #ebe4d8;
        border-radius: 16px;
        background: var(--paper);
    }
    .report-section__title {
        margin: 0 0 8px;
        font-size: 1.05rem;
    }
    .report-section__summary {
        margin: 0 0 12px;
        color: var(--muted);
    }
    .report-points {
        margin: 0;
        padding-left: 18px;
    }
    .link-button {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        padding: 10px 14px;
        border-radius: 12px;
        font-weight: 700;
        background: #eef7f6;
        border: 1px solid #c5e5e1;
    }
    .section-label {
        display: inline-block;
        margin-bottom: 10px;
        color: var(--muted);
        font-size: 0.86rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
    }
    @media (max-width: 720px) {
        .page-shell { padding: 18px 14px 40px; }
        .card, .hero { padding: 18px; }
        .card__header, .page-topbar { flex-direction: column; align-items: flex-start; }
        th, td { padding: 10px 10px; }
    }
    """
    return (
        "<html><head>"
        f"<title>{_esc(title)}</title>"
        f"<style>{styles}</style>"
        "</head><body>"
        "<main class='page-shell'>"
        "<header class='page-topbar'>"
        f"<div><h1 class='page-title'>{_esc(title)}</h1></div>"
        "<div>"
        f"<div class='page-links'><a href='{_href(current_path, 'ja')}'>日本語</a><span class='muted'>|</span><a href='{_href(current_path, 'en')}'>English</a></div>"
        f"<div class='page-nav'><a href='{_href('/packs', lang)}'>{_esc(_tr(lang, 'Packs'))}</a></div>"
        "</div>"
        "</header>"
        f"{body}"
        "</main></body></html>"
    )


def _esc(value: object) -> str:
    return html.escape(str(value))


def _none_list_item(lang: str) -> str:
    return f"<li>{_esc(_tr(lang, 'None'))}</li>"


def _none_table_row(lang: str, colspan: int) -> str:
    return f'<tr><td colspan="{colspan}">{_esc(_tr(lang, "None"))}</td></tr>'


def _run_href(run_id: object, lang: str, suffix: str = "") -> str:
    return _href(f"/runs/{_esc(run_id)}{suffix}", lang)


def _render_review_overview_card(packet: dict[str, Any], *, lang: str) -> str:
    decision = packet.get("decision", {}) if isinstance(packet.get("decision"), dict) else {}
    delivery = (
        packet.get("delivery_review", {}) if isinstance(packet.get("delivery_review"), dict) else {}
    )
    readiness = (
        packet.get("production_readiness", {})
        if isinstance(packet.get("production_readiness"), dict)
        else {}
    )
    submission = (
        packet.get("customer_submission_readiness", {})
        if isinstance(packet.get("customer_submission_readiness"), dict)
        else {}
    )
    review_stage = packet.get("review_stage", "unknown")
    blocking_items = packet.get("blocking_items", [])
    if not isinstance(blocking_items, list):
        blocking_items = []
    top_blockers = [
        _translate_issue_label(
            item.get("issue") or item.get("category"),
            item.get("issue") or item.get("category") or "-",
            lang=lang,
            show_raw=True,
        )
        for item in blocking_items
        if isinstance(item, dict)
    ][:2]
    next_actions = [
        _translate_message(lang, str(action or ""))
        for action in delivery.get("required_actions", [])
        if str(action or "").strip()
    ][:2]
    blockers_html = "".join(f"<li>{_esc(item)}</li>" for item in top_blockers) or _none_list_item(
        lang
    )
    actions_html = (
        "".join(f"<li>{_esc(item)}</li>" for item in next_actions)
        or f"<li>{_esc(_label_text(lang, '顧客提出レポートを確認してください。', 'Review the customer-facing report.'))}</li>"
    )
    body = (
        f"<p>{_esc(_review_stage_description(review_stage, lang=lang))}</p>"
        "<div class='meta-grid'>"
        + _meta_item_html(
            _tr(lang, "Review stage"), _value_badge(review_stage, lang=lang, show_raw=True)
        )
        + _meta_item_html(
            _tr(lang, "Decision"),
            _value_badge(
                decision.get("customer_status", decision.get("status", "unknown")),
                lang=lang,
                show_raw=True,
            ),
        )
        + _meta_item_html(
            _tr(lang, "Formal submission readiness"),
            _value_badge(submission.get("status", "not_recommended"), lang=lang, show_raw=True),
        )
        + _meta_item_html(
            _tr(lang, "Production Readiness"),
            _value_badge(readiness.get("status", "unknown"), lang=lang, show_raw=True),
        )
        + _meta_item_html(_tr(lang, "Unresolved S1"), _esc(delivery.get("unresolved_s1_count", 0)))
        + _meta_item_html(_tr(lang, "Unresolved S2"), _esc(delivery.get("unresolved_s2_count", 0)))
        + "</div>"
        f"<p class='section-label'>{_esc(_tr(lang, 'Top blockers'))}</p>"
        f"<ul>{blockers_html}</ul>"
        f"<p class='section-label'>{_esc(_tr(lang, 'Next priority actions'))}</p>"
        f"<ul>{actions_html}</ul>"
    )
    return _card_html(
        "Review Overview",
        body,
        lang=lang,
        badge_html=_value_badge(
            decision.get("customer_status", decision.get("status", "unknown")),
            lang=lang,
            show_raw=True,
        ),
        tone=_badge_tone(decision.get("customer_status", decision.get("status", "unknown"))),
    )


def _action_guidance_rows(packet: dict[str, Any], *, lang: str) -> list[str]:
    delivery = (
        packet.get("delivery_review", {}) if isinstance(packet.get("delivery_review"), dict) else {}
    )
    actions = delivery.get("required_actions", [])
    if not isinstance(actions, list):
        actions = []
    blockers = packet.get("blocking_items", [])
    if not isinstance(blockers, list):
        blockers = []
    rows: list[str] = []
    for index, action in enumerate(actions[:8]):
        action_text = str(action or "").strip()
        if not action_text:
            continue
        blocker = (
            blockers[index] if index < len(blockers) and isinstance(blockers[index], dict) else None
        )
        category = _action_category(action_text, blocker)
        translated_action = _translate_message(lang, action_text)
        rows.append(
            "<tr>"
            f"<td>{_badge_html(_action_priority(index, action_text), tone='danger' if index == 0 else 'warning', small=True)}</td>"
            f"<td><strong>{_esc(translated_action)}</strong><div class='micro'>code: {_esc(category)}</div></td>"
            f"<td>{_esc(_action_reason(action_text, blocker, lang=lang))}</td>"
            f"<td>{_esc(category)}</td>"
            f"<td>{_esc(_action_owner(category, action_text, lang=lang))}</td>"
            f"<td>{_esc(_action_next_state(category, action_text, lang=lang))}</td>"
            "</tr>"
        )
    return rows


def _render_action_guidance_card(packet: dict[str, Any], *, lang: str) -> str:
    rows = _action_guidance_rows(packet, lang=lang)
    empty_row = f"<tr><td colspan='6'>{_esc(_label_text(lang, '現時点で追加対応は検出されていません。', 'No additional action is detected at this point.'))}</td></tr>"
    body = (
        f"<table><tr><th>{_esc(_tr(lang, 'Priority'))}</th><th>{_esc(_tr(lang, 'Action'))}</th>"
        f"<th>{_esc(_tr(lang, 'Reason'))}</th><th>{_esc(_tr(lang, 'Category'))}</th>"
        f"<th>{_esc(_tr(lang, 'Owner'))}</th><th>{_esc(_tr(lang, 'Next State'))}</th></tr>"
        f"{''.join(rows) or empty_row}</table>"
    )
    return _card_html(
        "Prioritized Improvement Actions",
        body,
        lang=lang,
        description=_label_text(
            lang,
            "必要な対応を、改善優先度・理由・担当・次の状態で整理します。",
            "Required actions are grouped by priority, reason, owner, and next state.",
        ),
        badge_html=_badge_html(str(len(rows)), tone="danger" if rows else "neutral", small=True),
        tone="danger" if rows else "default",
    )


def _render_improvement_order_card(packet: dict[str, Any], *, lang: str) -> str:
    steps = _stage_improvement_steps(packet.get("review_stage", "unknown"), lang=lang)
    body = (
        "<ol class='ordered-list'>" + "".join(f"<li>{_esc(step)}</li>" for step in steps) + "</ol>"
    )
    return _card_html(
        "Improvement Order",
        body,
        lang=lang,
        description=_label_text(
            lang,
            "PM・営業・QAが次に進める順序を固定手順として表示します。",
            "A fixed sequence for PM, sales, and QA to move the review forward.",
        ),
    )


def _render_internal_review_notes_card(*, lang: str) -> str:
    body = (
        f"<p>{_esc(_label_text(lang, 'これはベンダー社内で改善・納品判断に使う情報です。', 'This information is for internal vendor review and delivery decisions.'))}</p>"
        "<div class='badge-row'>"
        + _badge_html(_tr(lang, "Delivery Review Summary"), tone="accent", small=True)
        + _badge_html(_tr(lang, "S1/S2 Blocking List"), tone="danger", small=True)
        + _badge_html(_tr(lang, "Major Failures"), tone="warning", small=True)
        + _badge_html(_tr(lang, "Improvement Actions"), tone="accent", small=True)
        + _badge_html(_tr(lang, "Gate Details"), tone="neutral", small=True)
        + "</div>"
    )
    return _card_html("Internal Review Notes", body, lang=lang)


def _render_customer_submission_card(run: dict[str, Any], *, lang: str) -> str:
    packet = run.get("review_packet")
    if not isinstance(packet, dict):
        return ""
    delivery = (
        packet.get("delivery_review", {}) if isinstance(packet.get("delivery_review"), dict) else {}
    )
    shareability = (
        packet.get("customer_shareability", {})
        if isinstance(packet.get("customer_shareability"), dict)
        else {}
    )
    submission = (
        packet.get("customer_submission_readiness", {})
        if isinstance(packet.get("customer_submission_readiness"), dict)
        else {}
    )
    reasons = _submission_status_reason(packet, lang=lang)
    status = str(submission.get("status") or "not_recommended")
    if _normalize_code(status) == "not_recommended":
        next_text = _label_text(
            lang,
            "社内で修正・再検査してください。GoまたはConditionalになったら正式レポートを生成してください。",
            "Fix internally, rerun, and generate the formal report after Go or Conditional.",
        )
    elif _normalize_code(status) == "conditional":
        next_text = _label_text(
            lang,
            "条件付き提出として、残留リスクと承認条件を明記してください。",
            "Use as conditional submission and document residual risks.",
        )
    else:
        next_text = _label_text(
            lang, "正式提出レポートとして利用できます。", "Ready for formal customer submission."
        )
    body = (
        f"<p>{_esc(_label_text(lang, 'これはsafe情報のみで構成される顧客共有向けの成果物です。', 'This customer-facing artifact is built from safe information only.'))}</p>"
        "<div class='meta-grid'>"
        + _meta_item_html(
            _tr(lang, "Report title"),
            _esc(_customer_report_title_for_stage(packet.get("review_stage"), lang=lang)),
        )
        + _meta_item_html(
            _tr(lang, "Customer shareability"),
            _value_badge(
                shareability.get(
                    "status", delivery.get("customer_submission_status", "needs_review")
                ),
                lang=lang,
                show_raw=True,
            ),
        )
        + _meta_item_html(
            _tr(lang, "Formal submission readiness"),
            _value_badge(status, lang=lang, show_raw=True),
        )
        + "</div>"
        f"<p class='section-label'>{_esc(_tr(lang, 'Why this status'))}</p>"
        f"<ul>{''.join(f'<li>{_esc(reason)}</li>' for reason in reasons)}</ul>"
        f"<p class='section-label'>{_esc(_tr(lang, 'Next Action'))}</p>"
        f"<p>{_esc(next_text)}</p>"
        f"<p><a class='link-button' href='{_run_href(run['run_id'], lang, '/report-preview')}'>{_esc(_label_text(lang, '顧客提出レポートを確認', 'Open Customer Report'))}</a></p>"
    )
    share_status = shareability.get(
        "status",
        delivery.get("customer_submission_status", "needs_review"),
    )
    share_reason = _label_text(
        lang,
        "顧客向け表示はsafe情報のみで構成されています。",
        "The customer-facing view uses safe information only.",
    )
    body = (
        f"<p>{_esc(_label_text(lang, '顧客に共有できる情報か、正式提出として推奨できる状態かを分けて確認します。', 'This separates information shareability from formal submission readiness.'))}</p>"
        f"<p><strong>{_esc(_tr(lang, 'Report title'))}:</strong> {_esc(_customer_report_title_for_stage(packet.get('review_stage'), lang=lang))}</p>"
        "<table>"
        f"<tr><th>{_esc(_tr(lang, 'Item'))}</th><th>{_esc(_tr(lang, 'Status'))}</th><th>{_esc(_tr(lang, 'Reason'))}</th><th>{_esc(_tr(lang, 'Next Action'))}</th></tr>"
        "<tr>"
        f"<td>{_esc(_tr(lang, 'Customer shareability'))}</td>"
        f"<td>{_value_badge(share_status, lang=lang, show_raw=True)}</td>"
        f"<td>{_esc(share_reason)}</td>"
        f"<td>{_esc(_label_text(lang, '正式提出可否は別途確認してください。', 'Check formal submission readiness separately.'))}</td>"
        "</tr>"
        "<tr>"
        f"<td>{_esc(_tr(lang, 'Formal submission readiness'))}</td>"
        f"<td>{_value_badge(status, lang=lang, show_raw=True)}</td>"
        f"<td><ul>{''.join(f'<li>{_esc(reason)}</li>' for reason in reasons)}</ul></td>"
        f"<td>{_esc(next_text)}</td>"
        "</tr>"
        "</table>"
        f"<p><a class='link-button' href='{_run_href(run['run_id'], lang, '/report-preview')}'>{_esc(_label_text(lang, '顧客提出レポートを確認', 'Open Customer Report'))}</a></p>"
    )
    return _card_html(
        "Customer Submission Status",
        body,
        lang=lang,
        badge_html=_value_badge(status, lang=lang, show_raw=True),
        tone=_badge_tone(status),
    )


def _render_review_packet_run_detail(run: dict[str, Any], *, lang: str) -> str:
    packet = run.get("review_packet")
    if not isinstance(packet, dict):
        return ""
    return (
        "<div class='stack'>"
        + _render_review_overview_card(packet, lang=lang)
        + _render_action_guidance_card(packet, lang=lang)
        + _render_customer_submission_card(run, lang=lang)
        + _render_blocking_items(packet, lang=lang)
        + _render_major_failures(run, lang=lang)
        + _render_production_readiness_card(packet, lang=lang)
        + _render_document_corpus_card(packet, lang=lang)
        + _render_change_event_card(packet, lang=lang)
        + _render_report_preview_card(run, lang=lang)
        + _render_summary_card(packet, lang=lang)
        + _render_scope_card(packet, lang=lang)
        + _render_count_card("Severity Summary", packet.get("severity_summary", {}), lang=lang)
        + _render_count_card("Risk Breakdown", packet.get("risk_breakdown", {}), lang=lang)
        + "</div>"
    )


def _render_delivery_review_card(packet: dict[str, Any], *, lang: str) -> str:
    display_lang = "ja"
    review = (
        packet.get("delivery_review", {}) if isinstance(packet.get("delivery_review"), dict) else {}
    )
    shareability = (
        packet.get("customer_shareability", {})
        if isinstance(packet.get("customer_shareability"), dict)
        else {}
    )
    submission = (
        packet.get("customer_submission_readiness", {})
        if isinstance(packet.get("customer_submission_readiness"), dict)
        else {}
    )
    actions = review.get("required_actions", [])
    if not isinstance(actions, list):
        actions = []
    body = (
        f"<p>{_esc(_translate_message(display_lang, review.get('summary', '-') or '-'))}</p>"
        "<div class='meta-grid'>"
        + _meta_item_html(
            _tr(display_lang, "Review stage"),
            _value_badge(packet.get("review_stage", "unknown"), lang=display_lang, small=True),
        )
        + _meta_item_html(
            _tr(display_lang, "Unresolved S1"),
            _esc(review.get("unresolved_s1_count", 0)),
        )
        + _meta_item_html(
            _tr(display_lang, "Unresolved S2"),
            _esc(review.get("unresolved_s2_count", 0)),
        )
        + _meta_item_html(
            _tr(display_lang, "Customer shareability"),
            _value_badge(
                review.get("customer_submission_status", "needs_review"),
                lang=display_lang,
                small=True,
            ),
        )
        + _meta_item_html(
            _tr(display_lang, "Formal submission readiness"),
            _value_badge(
                submission.get("status", "not_recommended"),
                lang=display_lang,
                small=True,
            ),
        )
        + _meta_item_html(
            _tr(display_lang, "Shareability"),
            _value_badge(
                shareability.get("status", "needs_review"),
                lang=display_lang,
                small=True,
            ),
        )
        + "</div>"
        f"<p>{_esc(_translate_message(display_lang, submission.get('recommendation', '') or ''))}</p>"
        f"<p class='section-label'>{_esc(_tr(display_lang, 'Required actions'))}</p>"
        f"<ul>{''.join(f'<li>{_esc(_translate_message(display_lang, item))}</li>' for item in actions) or _none_list_item(display_lang)}</ul>"
        f"<p class='muted'>{_esc(_translate_message(display_lang, review.get('reviewer_notes_placeholder', '') or ''))}</p>"
    )
    return _card_html(
        "Delivery Review Summary",
        body,
        lang=display_lang,
        badge_html=_value_badge(review.get("status", "unknown"), lang=display_lang, small=True),
        tone=_delivery_tone(review.get("status", "unknown")),
    )


def _delivery_tone(value: object) -> str:
    status = str(value or "").strip().lower()
    if status in {"not_deliverable", "needs_fix"}:
        return "danger"
    if status in {"needs_approval", "unknown"}:
        return "warning"
    return "default"


def _render_blocking_items(packet: dict[str, Any], *, lang: str) -> str:
    display_lang = "ja"
    items = packet.get("blocking_items", [])
    if not isinstance(items, list):
        items = []
    rows = []
    for item in items:
        if not isinstance(item, dict):
            continue
        rows.append(
            "<tr>"
            f"<td>{_esc(_translate_value(display_lang, item.get('severity', '-') or '-', show_raw=True))}</td>"
            f"<td>{_esc(_translate_issue_label(item.get('issue'), item.get('issue', '-'), lang=display_lang, show_raw=True))}</td>"
            f"<td>{_esc(_translate_issue_reason(item.get('issue'), item.get('issue', '-'), lang=display_lang))}</td>"
            f"<td>{_esc(_translate_message(display_lang, item.get('required_action', '-') or '-'))}</td>"
            f"<td>{_esc(_action_owner(str(item.get('category') or item.get('issue') or ''), str(item.get('required_action') or ''), lang=display_lang))}</td>"
            f"<td>{_esc(_translate_value(display_lang, item.get('status', '-') or '-'))}</td>"
            "</tr>"
        )
    body = (
        f"<table><tr><th>{_esc(_tr(display_lang, 'Severity'))}</th><th>{_esc(_tr(display_lang, 'Issue'))}</th><th>{_esc(_tr(display_lang, 'Why it matters'))}</th>"
        f"<th>{_esc(_tr(display_lang, 'Required actions'))}</th><th>{_esc(_tr(display_lang, 'Owner'))}</th><th>{_esc(_tr(display_lang, 'Detail'))}</th></tr>"
        f"{''.join(rows) or _none_table_row(display_lang, 6)}</table>"
    )
    return _card_html(
        "S1/S2 Blocking List",
        body,
        lang=display_lang,
        badge_html=_badge_html(str(len(rows)), tone="danger" if rows else "neutral", small=True),
        tone="danger" if rows else "default",
    )


def _render_decision_card(packet: dict[str, Any], *, lang: str) -> str:
    decision = packet.get("decision", {}) if isinstance(packet.get("decision"), dict) else {}
    explanation = (
        packet.get("decision_explanation", {})
        if isinstance(packet.get("decision_explanation"), dict)
        else {}
    )
    blocking_reasons = explanation.get("blocking_reasons", [])
    if not isinstance(blocking_reasons, list):
        blocking_reasons = []
    required_actions = explanation.get("required_actions", [])
    if not isinstance(required_actions, list):
        required_actions = []
    headline = _translate_decision_headline(decision, explanation, blocking_reasons, lang=lang)
    plain_reason = _translate_decision_reason_text(
        decision,
        explanation,
        blocking_reasons,
        lang=lang,
    )
    reason_rows_list: list[str] = []
    for item in blocking_reasons:
        if not isinstance(item, dict):
            continue
        affected_count = item.get("affected_count")
        affected_html = (
            f"<div class='micro'>{_esc(_tr(lang, 'Affected'))}: {_esc(affected_count)}</div>"
            if affected_count not in {None, "", 0}
            else ""
        )
        reason_rows_list.append(
            "<tr>"
            f"<td>{_value_badge(item.get('severity', '-'), lang=lang, small=True)}</td>"
            f"<td><strong>{_esc(_translate_issue_label(item.get('reason_code'), item.get('label', item.get('reason_code', '-')), lang=lang, show_raw=True))}</strong>{affected_html}</td>"
            f"<td>{_esc(_translate_issue_reason(item.get('reason_code'), item.get('why_it_blocks', '-'), lang=lang))}</td>"
            f"<td>{_esc(_translate_issue_action(item.get('reason_code'), item.get('required_action', '-'), lang=lang))}</td>"
            "</tr>"
        )
    reason_rows = "".join(reason_rows_list)
    actions = "".join(
        f"<li>{_esc(item)}</li>"
        for item in _decision_action_items(explanation, blocking_reasons, lang=lang)
    )
    body = (
        f"<p>{_esc(headline)}</p>"
        f"<p>{_esc(plain_reason)}</p>"
        f"<table><tr><th>{_esc(_tr(lang, 'Severity'))}</th><th>{_esc(_tr(lang, 'Reason'))}</th><th>{_esc(_tr(lang, 'Why it matters'))}</th><th>{_esc(_tr(lang, 'Action'))}</th></tr>"
        f"{reason_rows or _none_table_row(lang, 4)}"
        "</table>"
        f"<p class='section-label'>{_esc(_tr(lang, 'Required actions'))}</p><ul>{actions or _none_list_item(lang)}</ul>"
    )
    return _card_html(
        "Decision Card",
        body,
        lang=lang,
        badge_html=_value_badge(
            decision.get("customer_status", decision.get("status", "-")),
            lang=lang,
            show_raw=True,
        ),
        tone=_badge_tone(decision.get("customer_status", decision.get("status", "-"))),
    )


def _render_summary_card(packet: dict[str, Any], *, lang: str) -> str:
    summary = packet.get("run_summary", {}) if isinstance(packet.get("run_summary"), dict) else {}
    pass_rate = summary.get("pass_rate", 0.0)
    try:
        pass_rate_text = f"{float(pass_rate):.1f}%"
    except (TypeError, ValueError):
        pass_rate_text = str(pass_rate)
    body = (
        "<div class='meta-grid'>"
        + _meta_item_html(_tr(lang, "Total"), _esc(summary.get("total_cases", 0)))
        + _meta_item_html(_tr(lang, "Passed"), _esc(summary.get("passed_cases", 0)))
        + _meta_item_html(_tr(lang, "Failed"), _esc(summary.get("failed_cases", 0)))
        + _meta_item_html(_tr(lang, "Pass Rate"), _esc(pass_rate_text))
        + _meta_item_html(
            _tr(lang, "Report Mode"),
            _badge_html(str(summary.get("report_mode", "-")), tone="neutral", small=True),
        )
        + "</div>"
    )
    return _card_html("Summary Card", body, lang=lang)


def _render_scope_card(packet: dict[str, Any], *, lang: str) -> str:
    scope = packet.get("scope", {}) if isinstance(packet.get("scope"), dict) else {}
    mode = str(packet.get("packet_mode", "") or "")
    safe_note = _tr(lang, "Not available in safe mode") if mode == "safe" else "-"

    def available(value: object) -> str:
        if value in (None, "", [], {}):
            return safe_note
        if isinstance(value, list):
            return ", ".join(_esc(item) for item in value) or safe_note
        if isinstance(value, dict):
            return _esc(json.dumps(value, ensure_ascii=False))
        return _esc(value)

    body = (
        "<div class='meta-grid'>"
        + _meta_item_html(_tr(lang, "Target"), available(scope.get("target_name")))
        + _meta_item_html(_tr(lang, "Type"), available(scope.get("target_type")))
        + _meta_item_html(_tr(lang, "Documents"), available(scope.get("target_documents")))
        + _meta_item_html(_tr(lang, "Versions"), available(scope.get("document_versions")))
        + _meta_item_html(_tr(lang, "Change Event"), available(scope.get("change_event")))
        + "</div>"
    )
    return _card_html("Scope Card", body, lang=lang)


def _render_document_corpus_card(packet: dict[str, Any], *, lang: str) -> str:
    corpus = (
        packet.get("document_corpus", {}) if isinstance(packet.get("document_corpus"), dict) else {}
    )
    mode = str(packet.get("packet_mode", "") or "")
    safe_note = _tr(lang, "Not available in safe mode") if mode == "safe" else "-"

    def available(value: object) -> str:
        if value in (None, "", [], {}):
            return safe_note
        if isinstance(value, list):
            return ", ".join(_esc(item) for item in value) or safe_note
        return _esc(value)

    summary = (
        "<div class='meta-grid'>"
        + _meta_item_html(_tr(lang, "Document Count"), _esc(corpus.get("document_count", 0)))
        + _meta_item_html(
            _tr(lang, "Source of Truth Type"),
            _badge_html(
                _translate_value(
                    lang, corpus.get("source_of_truth_type", "unknown"), show_raw=True
                ),
                tone="accent",
                small=True,
            ),
        )
        + _meta_item_html(
            _tr(lang, "Has Versions"),
            _value_badge(corpus.get("has_document_versions", False), lang=lang, small=True),
        )
        + _meta_item_html(_tr(lang, "Stale Doc Policy"), available(corpus.get("stale_doc_policy")))
        + _meta_item_html(_tr(lang, "Version Hashes"), available(corpus.get("version_hashes")))
        + "</div>"
    )
    documents = corpus.get("target_documents", [])
    if mode == "full" and isinstance(documents, list) and documents:
        rows = "".join(
            "<tr>"
            f"<td>{_esc(item.get('title', '-') if isinstance(item, dict) else '-')}</td>"
            f"<td>{_esc(item.get('version', '-') if isinstance(item, dict) else '-')}</td>"
            f"<td>{_esc(item.get('last_updated_at', '-') if isinstance(item, dict) else '-')}</td>"
            f"<td>{_esc(item.get('owner', '-') if isinstance(item, dict) else '-')}</td>"
            f"<td>{_esc(item.get('snapshot_id', '-') if isinstance(item, dict) else '-')}</td>"
            f"<td>{_esc(item.get('source_path', '-') if isinstance(item, dict) else '-')}</td>"
            "</tr>"
            for item in documents
        )
        summary += (
            f"<p class='section-label'>{_esc(_tr(lang, 'Full document metadata'))}</p>"
            f"<table><tr><th>{_esc(_tr(lang, 'Title'))}</th><th>{_esc(_tr(lang, 'Version'))}</th><th>{_esc(_tr(lang, 'Last Updated'))}</th>"
            f"<th>{_esc(_tr(lang, 'Owner'))}</th><th>{_esc(_tr(lang, 'Snapshot ID'))}</th><th>{_esc(_tr(lang, 'Source Path'))}</th></tr>"
            f"{rows}</table>"
        )
    elif mode == "safe":
        summary += f"<p>{_esc(_tr(lang, 'Document titles, owners, and source paths are not expanded in safe mode.'))}</p>"
    return _card_html(
        "Document Corpus Card",
        summary,
        lang=lang,
        badge_html=_badge_html(
            _label_text(
                lang,
                f"{int(corpus.get('document_count', 0) or 0)} 件",
                f"{int(corpus.get('document_count', 0) or 0)} docs",
            ),
            tone="neutral",
            small=True,
        ),
    )


def _render_change_event_card(packet: dict[str, Any], *, lang: str) -> str:
    change = (
        packet.get("change_summary", {}) if isinstance(packet.get("change_summary"), dict) else {}
    )
    mode = str(packet.get("packet_mode", "") or "")
    safe_note = _tr(lang, "Not available in safe mode") if mode == "safe" else "-"

    def available(value: object, *, translate_text: bool = False) -> str:
        if value in (None, "", [], {}):
            return safe_note
        if isinstance(value, list):
            return ", ".join(_esc(item) for item in value) or safe_note
        if translate_text and isinstance(value, str):
            return _esc(_translate_message(lang, value))
        return _esc(value)

    summary = (
        "<div class='meta-grid'>"
        + _meta_item_html(
            _tr(lang, "Change Type"),
            _badge_html(
                _translate_value(lang, change.get("change_type", "unknown"), show_raw=True),
                tone="accent",
                small=True,
            ),
        )
        + _meta_item_html(_tr(lang, "Changed Assets"), _esc(change.get("changed_assets_count", 0)))
        + _meta_item_html(
            _tr(lang, "Affected Documents"), _esc(change.get("affected_documents_count", 0))
        )
        + _meta_item_html(
            _tr(lang, "Affected Categories"), available(change.get("affected_business_categories"))
        )
        + _meta_item_html(_tr(lang, "Target Release"), available(change.get("target_release")))
        + "</div>"
        f"<p><strong>{_esc(_tr(lang, 'Summary'))}:</strong> {available(change.get('change_summary'), translate_text=True)}</p>"
        f"<p><strong>{_esc(_tr(lang, 'Retest reason:'))}</strong> {available(change.get('retest_reason'), translate_text=True)}</p>"
    )
    if mode == "full" and change.get("changed_assets"):
        summary += (
            f"<h4>{_esc(_tr(lang, 'Full change assets'))}</h4>"
            f"<p>{available(change.get('changed_assets'))}</p>"
        )
    elif mode == "safe":
        summary += f"<p>{_esc(_tr(lang, 'Changed asset names and affected document names are not expanded in safe mode.'))}</p>"
    return _card_html("Change Event Card", summary, lang=lang)


def _render_production_readiness_card(packet: dict[str, Any], *, lang: str) -> str:
    readiness = (
        packet.get("production_readiness", {})
        if isinstance(packet.get("production_readiness"), dict)
        else {}
    )
    blockers = readiness.get("blockers", [])
    warnings = readiness.get("warnings", [])
    actions = readiness.get("required_actions", [])
    if not isinstance(blockers, list):
        blockers = []
    if not isinstance(warnings, list):
        warnings = []
    if not isinstance(actions, list):
        actions = []
    translated_actions = _readiness_action_items(readiness, lang=lang)
    body = (
        f"<p>{_esc(_translate_readiness_summary(readiness, lang=lang))}</p>"
        + f"<p class='section-label'>{_esc(_tr(lang, 'Blockers'))}</p>"
        + _render_readiness_issue_table(blockers, issue_type="blocker", lang=lang)
        + f"<p class='section-label'>{_esc(_tr(lang, 'Warnings'))}</p>"
        + _render_readiness_issue_table(warnings, issue_type="warning", lang=lang)
        + f"<p class='section-label'>{_esc(_tr(lang, 'Required actions'))}</p>"
        + f"<ul>{''.join(f'<li>{_esc(item)}</li>' for item in translated_actions) or _none_list_item(lang)}</ul>"
    )
    return _card_html(
        "Production Readiness Card",
        body,
        lang=lang,
        badge_html=_value_badge(readiness.get("status", "unknown"), lang=lang, show_raw=True),
        tone=_badge_tone(readiness.get("status", "unknown")),
    )


def _render_readiness_issue_table(items: list[object], *, issue_type: str, lang: str) -> str:
    action_key = "required_action" if issue_type == "blocker" else "recommended_action"
    rows = "".join(
        "<tr>"
        f"<td>{_esc(item.get('code', '-') if isinstance(item, dict) else '-')}</td>"
        f"<td>{_esc(_translate_issue_label(item.get('code', '-'), item.get('label', '-'), lang=lang)) if isinstance(item, dict) else '-'}</td>"
        f"<td>{_esc(_translate_issue_reason(item.get('code', '-'), item.get('reason', '-'), lang=lang)) if isinstance(item, dict) else '-'}</td>"
        f"<td>{_esc(_translate_issue_action(item.get('code', '-'), item.get(action_key, '-'), lang=lang)) if isinstance(item, dict) else '-'}</td>"
        "</tr>"
        for item in items
    )
    return (
        f"<table><tr><th>{_esc(_tr(lang, 'Code'))}</th><th>{_esc(_tr(lang, 'Label'))}</th><th>{_esc(_tr(lang, 'Reason'))}</th><th>{_esc(_tr(lang, 'Action'))}</th></tr>"
        f"{rows or _none_table_row(lang, 4)}</table>"
    )


def _render_count_card(title: str, counts: object, *, lang: str) -> str:
    if not isinstance(counts, dict):
        counts = {}
    rows: list[str] = []
    for key, value in counts.items():
        if title == "Severity Summary":
            label_html = _value_badge(key, lang=lang, small=True)
        elif title == "Risk Breakdown":
            label_html = _esc(_translate_issue_label(key, key, lang=lang, show_raw=True))
        else:
            label_html = _esc(_translate_value(lang, key))
        rows.append(f"<tr><td>{label_html}</td><td>{_esc(value)}</td></tr>")
    body = f"<table><tr><th>{_esc(_tr(lang, 'Item'))}</th><th>{_esc(_tr(lang, 'Count'))}</th></tr>{''.join(rows) or _none_table_row(lang, 2)}</table>"
    return _card_html(title, body, lang=lang)


def _render_major_failures(run: dict[str, Any], *, lang: str) -> str:
    packet = run.get("review_packet")
    failures = packet.get("major_failures", []) if isinstance(packet, dict) else []
    if not isinstance(failures, list):
        failures = []
    sorted_failures = sorted(failures, key=_failure_sort_key)
    rows = []
    for failure in sorted_failures:
        if not isinstance(failure, dict):
            continue
        failure_id = str(failure.get("failure_id") or failure.get("case_id_hash") or "")
        detail = "-"
        if failure.get("full_detail_ref") and failure_id:
            failure_suffix = f"/failures/{_esc(failure_id)}"
            detail_href = _run_href(run["run_id"], lang, failure_suffix)
            detail = (
                f"<a class='link-button' href='{detail_href}'>" f"{_esc(_tr(lang, 'Detail'))}</a>"
            )
        failure_code = (
            failure.get("safe_reason_code")
            or failure.get("failure_category")
            or failure.get("failure_pattern")
        )
        summary_label = _translate_failure_pattern(
            failure.get("failure_category") or failure.get("failure_pattern") or "-",
            lang=lang,
            show_raw=True,
        )
        summary_meta = []
        if failure.get("failure_pattern") and failure.get("failure_pattern") != failure.get(
            "failure_category"
        ):
            summary_meta.append(
                _translate_failure_pattern(failure.get("failure_pattern"), lang=lang, show_raw=True)
            )
        if failure.get("evidence_status"):
            summary_meta.append(
                f"{_tr(lang, 'Evidence Status')}: {_translate_value(lang, failure.get('evidence_status'))}"
            )
        summary_html = f"<div><strong>{_esc(summary_label)}</strong></div>"
        if summary_meta:
            summary_html += f"<div class='micro'>{_esc(' / '.join(summary_meta))}</div>"
        impact_html = _value_badge(failure.get("go_no_go_impact", "-"), lang=lang, small=True)
        if failure.get("safe_reason_code"):
            impact_html += f"<div class='micro'>{_esc(failure.get('safe_reason_code'))}</div>"
        rows.append(
            "<tr>"
            f"<td>{_value_badge(failure.get('customer_severity', '-'), lang=lang, small=True)}</td>"
            f"<td>{summary_html}</td>"
            f"<td>{impact_html}</td>"
            f"<td>{_esc(_translate_issue_action(failure_code, failure.get('next_action', '-') or '-', lang=lang))}</td>"
            f"<td>{detail}</td>"
            "</tr>"
        )
    body = (
        f"<table><tr><th>{_esc(_tr(lang, 'Severity'))}</th><th>{_esc(_label_text(lang, '失敗内容', 'Failure'))}</th>"
        f"<th>{_esc(_label_text(lang, '影響', 'Impact'))}</th><th>{_esc(_tr(lang, 'Next Action'))}</th><th>{_esc(_tr(lang, 'Detail'))}</th></tr>"
        f"{''.join(rows) or _none_table_row(lang, 5)}"
        "</table>"
    )
    return _card_html(
        "Major Failures",
        body,
        lang=lang,
        badge_html=_badge_html(str(len(rows)), tone="danger" if rows else "neutral", small=True),
        tone="danger" if rows else "default",
    )


def _failure_sort_key(failure: object) -> tuple[int, int, str]:
    if not isinstance(failure, dict):
        return (99, 99, "")
    severity_order = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
    impact_order = {
        "blocks_release": 0,
        "requires_human_review": 1,
        "needs_fix_or_review": 2,
        "informational": 3,
    }
    impact = _normalize_code(failure.get("go_no_go_impact", ""))
    impact_rank = impact_order.get(impact, 9)
    return (
        impact_rank,
        severity_order.get(str(failure.get("customer_severity", "")), 9),
        str(failure.get("failure_id") or failure.get("case_id_hash") or ""),
    )


def _find_review_failure(run: dict[str, Any], failure_id: str) -> dict[str, Any] | None:
    packet = run.get("review_packet")
    failures = packet.get("major_failures", []) if isinstance(packet, dict) else []
    if not isinstance(failures, list):
        return None
    for failure in failures:
        if not isinstance(failure, dict):
            continue
        if failure_id in {
            str(failure.get("failure_id") or ""),
            str(failure.get("case_id_hash") or ""),
        }:
            return failure
    return None


def _render_failure_detail(*, run: dict[str, Any], failure: dict[str, Any], lang: str) -> str:
    packet = run.get("review_packet")
    mode = packet.get("packet_mode", "safe") if isinstance(packet, dict) else "safe"
    safe_note = (
        f"<p>{_esc(_tr(lang, 'Safe packet: raw question, answer, and evidence text are not expanded here.'))}</p>"
        if mode == "safe"
        else ""
    )
    failure_code = (
        failure.get("safe_reason_code")
        or failure.get("failure_category")
        or failure.get("failure_pattern")
    )
    fields = [
        ("Customer Severity", _translate_value(lang, failure.get("customer_severity", "-") or "-")),
        ("Internal Severity", str(failure.get("internal_severity", "-") or "-")),
        (
            "Failure Pattern",
            _translate_failure_pattern(
                failure.get("failure_pattern", "-") or "-", lang=lang, show_raw=True
            ),
        ),
        (
            "Failure Category",
            _translate_failure_pattern(
                failure.get("failure_category", "-") or "-", lang=lang, show_raw=True
            ),
        ),
        ("Evidence Status", _translate_value(lang, failure.get("evidence_status", "-") or "-")),
        ("Safe Reason Code", str(failure.get("safe_reason_code", "-") or "-")),
        ("Go/No-Go Impact", _translate_value(lang, failure.get("go_no_go_impact", "-") or "-")),
        (
            "Next Action",
            _translate_issue_action(
                failure_code, failure.get("next_action", "-") or "-", lang=lang
            ),
        ),
        ("Full Detail Ref", str(failure.get("full_detail_ref", "-") or "-")),
    ]
    rows = "".join(
        f"<tr><th>{_esc(_tr(lang, label))}</th><td>{_esc(value)}</td></tr>"
        for label, value in fields
    )
    full_only = ""
    if mode == "full":
        full_only = (
            f"<h3>{_esc(_tr(lang, 'Full Detail Summaries'))}</h3>"
            "<table>"
            f"<tr><th>{_esc(_tr(lang, 'Question'))}</th><td>{_esc(failure.get('question_summary', '-') or '-')}</td></tr>"
            f"<tr><th>{_esc(_tr(lang, 'Expected'))}</th><td>{_esc(failure.get('expected_summary', '-') or '-')}</td></tr>"
            f"<tr><th>{_esc(_tr(lang, 'Actual'))}</th><td>{_esc(failure.get('actual_summary', '-') or '-')}</td></tr>"
            "</table>"
        )
    body = f"{safe_note}<table>{rows}</table>{full_only}"
    return (
        f"<p><a href='{_run_href(run['run_id'], lang)}'>{_esc(_tr(lang, 'Back to Run Detail'))}</a></p>"
        + _card_html(
            "Failure",
            body,
            lang=lang,
            badge_html=_value_badge(failure.get("customer_severity", "-"), lang=lang, small=True),
            tone=_badge_tone(failure.get("customer_severity", "-")),
        )
    )


def _render_report_preview(run: dict[str, Any], *, lang: str) -> str:
    packet = run.get("review_packet")
    sections = packet.get("report_sections", {}) if isinstance(packet, dict) else {}
    if not isinstance(sections, dict):
        sections = {}
    report_title = sections.get("report_title") or _tr(lang, "Report Preview")
    order = [
        ("Executive Summary", "executive_summary"),
        ("Decision", "decision"),
        ("Change Summary", "change_summary"),
        ("Scope", "scope"),
        ("Production Readiness", "production_readiness"),
        ("Delivery Review", "delivery_review"),
        ("Customer Submission", "customer_submission"),
        ("Major Risks", "major_risks"),
        ("Blocking Issues", "blocking_issues"),
        ("Required Actions", "required_actions"),
        ("Residual Risks", "residual_risks"),
        ("Disclaimer", "disclaimer"),
    ]
    body = (
        f"<p><a href='{_run_href(run['run_id'], lang)}'>{_esc(_tr(lang, 'Back to Run Detail'))}</a></p>"
        f"<h2>{_esc(report_title)}</h2><div class='report-sections'>"
    )
    for title, key in order:
        body += _render_report_preview_section(
            title,
            _report_preview_section_text(run, key, sections.get(key, "-") or "-", lang=lang),
            lang=lang,
            list_first=key
            in {"required_actions", "major_risks", "blocking_issues", "residual_risks"},
        )
    return body + "</div>"
