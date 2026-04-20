"""RAG Quality Runner — serving layer を呼び出してテストケースを評価する。

これが llmops-lab と rag_app の融合点。
RAGStore で検索 → LLM で回答 → 各 evaluator で品質判定。
"""

from __future__ import annotations

import logging
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from openai import APIError

from ..serving.llm_client import generate_answer
from ..serving.rag import RAGStore
from .case_schema import normalize_eval_mode
from .evaluators.keyword import keyword_match_rate
from .evaluators.llm_judge import (
    _normalize_text,
    _overlap_f1,
    _overlap_precision,
    _overlap_tokens,
    _split_text_units,
)
from .evaluators.llm_judge import judge as llm_judge
from .evaluators.reference import extract_references, reference_accuracy
from .evaluators.retrieval import retrieval_hit, retrieval_precision_at_k
from .failure_reason import classify_failure_category
from .models import EvalResult, EvalRun, QARunRecord, QATestCase

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Evaluation thresholds (ケースの severity で分岐)
# ------------------------------------------------------------------

S1_KEYWORD_THRESHOLD = 0.8  # S1: 80% 以上のキーワード一致必須
S2_KEYWORD_THRESHOLD = 0.5  # S2: 50% で OK
GROUNDED_JUDGE_THRESHOLD = 0.5  # rollout threshold; citation and evidence recall remain mandatory
_EXACT_WHITESPACE_RE = re.compile(r"\s+")
_CONTACT_ANSWER_RE = re.compile(r"(人事部|情報セキュリティ担当|[\w一-龠ぁ-んァ-ヶー々]+担当)")
_NUMERIC_ANSWER_RE = re.compile(r"\d|毎月|翌営業日|営業日|前営業日|週\s*\d+\s*回|最長\s*\d+\s*歳")
_PROCEDURE_ANSWER_RE = re.compile(r"申請|承認|提出|添付|システム|打刻|報告")
_POLICY_ANSWER_RE = re.compile(r"禁止|必要|可能|対象|条件|事由|違反|原則")
_QUESTION_SPLIT_RE = re.compile(r"[はをにでがと、。？！?\s]+")
_QUESTION_SUFFIXES = (
    "はどの手順で申請しますか",
    "はどの手順ですか",
    "はどうやって申請しますか",
    "はどうやって行いますか",
    "は何ですか",
    "はいつまでですか",
    "はいつですか",
    "はどこですか",
    "はいくらですか",
)
_QUESTION_GENERIC_PHRASES = {
    "何ですか",
    "何",
    "いつですか",
    "いつ",
    "どこですか",
    "どこ",
    "いくらですか",
    "いくら",
    "ですか",
    "ますか",
    "する場合",
    "場合",
    "主な",
    "必要",
}


def _mode_threshold(severity: str) -> float:
    return S1_KEYWORD_THRESHOLD if severity == "S1" else S2_KEYWORD_THRESHOLD


def _normalize_exact_text(text: str) -> str:
    return _EXACT_WHITESPACE_RE.sub("", text).strip().lower()


def _expected_answer_matches(answer: str, expected_answer: str) -> bool:
    normalized_answer = _normalize_exact_text(answer)
    normalized_expected = _normalize_exact_text(expected_answer)
    if not normalized_expected:
        return False
    return normalized_expected in normalized_answer


def _markdown_excerpt_blocks(text: str) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return []

    lines = [line.rstrip() for line in stripped.splitlines()]
    doc_title = ""
    current: list[str] = []
    blocks: list[str] = []

    def flush_current() -> None:
        nonlocal current
        candidate = "\n".join(line for line in current if line.strip()).strip()
        if not candidate:
            current = []
            return

        content_lines = [
            line
            for line in candidate.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        if content_lines:
            blocks.append(candidate)
        current = []

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            if level == 1:
                doc_title = line
                continue

            if current:
                flush_current()
            current = [part for part in (doc_title, line) if part]
            continue

        if not current and doc_title:
            current.append(doc_title)
        current.append(line)

    if current:
        flush_current()

    if blocks:
        return blocks

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", stripped) if part.strip()]
    return paragraphs or [stripped]


def _question_intent_boost(question: str, excerpt: str) -> float:
    normalized_question = _normalize_text(question)
    normalized_excerpt = _normalize_text(excerpt)
    boost = 0.0

    if any(
        term in normalized_question
        for term in ("問い合わせ先", "どこ", "窓口", "連絡先", "エスカレーション")
    ):
        if _CONTACT_ANSWER_RE.search(normalized_excerpt) or "人事部" in normalized_excerpt:
            boost += 0.18

    if any(
        term in normalized_question
        for term in ("いつ", "期限", "締め日", "何日", "いつまで", "上限")
    ):
        if _NUMERIC_ANSWER_RE.search(normalized_excerpt):
            boost += 0.12

    if any(term in normalized_question for term in ("いくら", "金額", "何円", "月額")):
        if _NUMERIC_ANSWER_RE.search(normalized_excerpt):
            boost += 0.15

    if any(term in normalized_question for term in ("手順", "方法", "申請", "どうやって")):
        if _PROCEDURE_ANSWER_RE.search(normalized_excerpt):
            boost += 0.12

    if any(term in normalized_question for term in ("条件", "ルール", "事由", "主な", "何ですか")):
        if _POLICY_ANSWER_RE.search(normalized_excerpt):
            boost += 0.08

    return boost


def _question_focus_label(question: str) -> str:
    normalized = _normalize_text(question).rstrip("？?")
    for suffix in _QUESTION_SUFFIXES:
        if normalized.endswith(suffix):
            return normalized[: -len(suffix)].strip()

    if normalized.endswith("ですか"):
        trimmed = normalized[: -len("ですか")].strip()
        return trimmed.rstrip("は").strip()

    return normalized


def _question_focus_phrases(question: str) -> list[str]:
    normalized = _question_focus_label(question)
    phrases: list[str] = []
    seen: set[str] = set()
    candidates = [normalized, *_QUESTION_SPLIT_RE.split(normalized)]
    for candidate in candidates:
        if not candidate:
            continue
        for part in re.split(r"[の・/]|な", candidate):
            phrase = part.strip()
            if len(phrase) < 2 or phrase in _QUESTION_GENERIC_PHRASES or phrase in seen:
                continue
            seen.add(phrase)
            phrases.append(phrase)
    return phrases


def _phrase_aliases(phrase: str) -> tuple[str, ...]:
    aliases: list[str] = []
    if "証憑" in phrase:
        aliases.extend(["レシート", "領収書", "添付", "原本"])
    if "問い合わせ" in phrase or "窓口" in phrase or "連絡先" in phrase:
        aliases.extend(["人事部", "担当", "窓口"])
    if "期限" in phrase or "締め日" in phrase:
        aliases.extend(["営業日", "前営業日", "翌営業日", "毎月25日"])
    if "残業" in phrase:
        aliases.append("残業")
    if "持ち出し" in phrase:
        aliases.extend(["社外への持ち出し", "社外持ち出し", "原則禁止"])
    if "承認" in phrase or "手順" in phrase:
        aliases.extend(["承認", "申請", "上司", "上長"])
    if "懲戒" in phrase or "事由" in phrase:
        aliases.extend(["背信行為", "無断欠勤", "有罪判決", "機密情報"])
    if "在宅勤務" in phrase:
        aliases.extend(["在宅勤務", "週2回", "在宅"])
    if "育児休業" in phrase or "延長" in phrase:
        aliases.extend(["育児休業", "最長2歳", "保育所"])
    return tuple(dict.fromkeys(aliases))


def _question_phrase_boost(question: str, excerpt: str) -> float:
    normalized_excerpt = _normalize_text(excerpt)
    boost = 0.0
    for phrase in _question_focus_phrases(question):
        if phrase in normalized_excerpt:
            boost += 0.06 + min(0.08, 0.02 * max(len(phrase) - 2, 0))
            continue
        alias_hits = [alias for alias in _phrase_aliases(phrase) if alias in normalized_excerpt]
        if alias_hits:
            boost += min(0.18, 0.05 * len(alias_hits))
    return min(boost, 0.45)


def _score_mock_excerpt(question: str, excerpt: str) -> float:
    question_tokens = _overlap_tokens(question)
    excerpt_tokens = _overlap_tokens(excerpt)
    if not excerpt_tokens:
        return 0.0

    lexical_score = 0.0
    if question_tokens:
        lexical_score = (0.7 * _overlap_f1(question_tokens, excerpt_tokens)) + (
            0.3 * _overlap_precision(question_tokens, excerpt_tokens)
        )

    return (
        lexical_score
        + _question_intent_boost(question, excerpt)
        + _question_phrase_boost(question, excerpt)
    )


def _best_mock_excerpt(question: str, text: str) -> str:
    blocks = _markdown_excerpt_blocks(text)
    if not blocks:
        return text

    best_block = blocks[0]
    best_score = float("-inf")
    for block in blocks:
        score = _score_mock_excerpt(question, block)
        if score > best_score:
            best_block = block
            best_score = score
    return best_block


def _best_grounded_mock_excerpt(question: str, text: str) -> str:
    block = _best_mock_excerpt(question, text)
    units = _split_text_units(block)
    if not units:
        return block

    best_unit = block
    best_score = float("-inf")
    for unit in units:
        score = _score_mock_excerpt(question, unit)
        if score > best_score:
            best_unit = unit
            best_score = score
    return best_unit


def _format_mock_excerpt(question: str, excerpt: str) -> str:
    normalized_question = _normalize_text(question)
    content_lines = [
        line.strip()
        for line in excerpt.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    if not content_lines:
        return excerpt

    contact_match = _CONTACT_ANSWER_RE.search(excerpt)
    if contact_match and any(
        term in normalized_question
        for term in ("問い合わせ先", "どこ", "窓口", "連絡先", "エスカレーション")
    ):
        return f"問い合わせ先は{contact_match.group(1)}です。\n" + "\n".join(content_lines)

    best_line = max(content_lines, key=lambda line: _score_mock_excerpt(question, line))
    remaining_lines = [line for line in content_lines if line != best_line]
    focus_label = _question_focus_label(question)
    if focus_label and focus_label not in best_line:
        first_line = f"{focus_label}については、{best_line}"
    else:
        first_line = best_line

    return "\n".join([first_line, *remaining_lines])


def _render_grounded_mock_answer(question: str, retrieved: list[dict[str, Any]]) -> str:
    question_tokens = _overlap_tokens(question)
    best_part = ""
    best_score = float("-inf")
    for row in retrieved:
        raw_text = str(row.get("text", "")).strip()
        if not raw_text:
            continue
        excerpt = _best_grounded_mock_excerpt(question, raw_text)
        chunk_id = str(row.get("chunk_id", "")).strip()
        score = _score_mock_excerpt(question, excerpt)
        if question_tokens:
            score += _overlap_f1(question_tokens, _overlap_tokens(excerpt))
        candidate = f"{excerpt} [{chunk_id}]" if chunk_id else excerpt
        if score > best_score:
            best_part = candidate
            best_score = score
    return best_part


def _render_focus_mock_answer(question: str, retrieved: list[dict[str, Any]]) -> str:
    best_excerpt = ""
    best_score = float("-inf")
    for row in retrieved:
        raw_text = str(row.get("text", "")).strip()
        if not raw_text:
            continue
        excerpt = _best_mock_excerpt(question, raw_text)
        score = _score_mock_excerpt(question, excerpt)
        if score > best_score:
            best_excerpt = excerpt
            best_score = score

    if not best_excerpt:
        return ""

    return _format_mock_excerpt(question, best_excerpt)


def _render_mock_answer(
    question: str,
    retrieved: list[dict[str, Any]],
    *,
    grounded: bool = False,
) -> str:
    if grounded:
        return _render_grounded_mock_answer(question, retrieved)

    return _render_focus_mock_answer(question, retrieved)


class RAGQualityRunner:
    """RAG パイプラインを端から端まで実行して品質を評価する。"""

    def __init__(
        self,
        store: RAGStore,
        retrieval_k: int = 20,
        context_k: int = 3,
        use_multi: bool = False,
        max_new_tokens: int = 256,
        mock_llm: bool = False,
    ):
        self.store = store
        self.retrieval_k = retrieval_k
        self.context_k = context_k
        self.use_multi = use_multi
        self.max_new_tokens = max_new_tokens
        self.mock_llm = mock_llm

    def run_case(self, case: QATestCase) -> EvalResult:
        """1件のテストケースを実行して評価する。"""
        t0 = time.perf_counter()
        eval_mode = normalize_eval_mode(case.eval_mode)
        failure_type = None
        failure_reason = ""
        answer = ""
        retrieved_ids: list[str] = []
        answer_match: bool | None = None
        evidence_match: bool | None = None
        ret_hit: bool | None = None
        evidence_recall: float | None = None
        faithfulness: float | None = None
        judge_relevance: float | None = None
        judge_fallback_used = False
        judge_fallback_reason: str | None = None
        cost_usd = 0.0
        input_tokens = 0
        output_tokens = 0
        total_tokens = 0

        try:
            # 1) 検索
            if self.use_multi:
                raw = self.store.search_multi(case.question, top_k=self.retrieval_k)
            else:
                raw = self.store.search(case.question, top_k=self.retrieval_k)

            # 重複排除 & context_k 件に絞り込み
            seen: set[str] = set()
            retrieved: list[dict[str, Any]] = []
            for r in raw:
                cid = r.get("chunk_id", "")
                if cid and cid not in seen:
                    seen.add(cid)
                    retrieved.append(r)
            retrieved = retrieved[: self.context_k]
            retrieved_ids = [r["chunk_id"] for r in retrieved]

            # 2) Retrieval 評価
            if case.expected_chunks:
                ret_hit = retrieval_hit(retrieved_ids, case.expected_chunks)
                evidence_recall = retrieval_precision_at_k(retrieved_ids, case.expected_chunks)
                evidence_match = ret_hit

            # 3) 回答生成
            if not retrieved:
                answer = "検索結果がありません。文書を投入してください。"
            elif self.mock_llm:
                # Mock: grounded_judge では質問に近い文だけを引用付きで返す。
                answer = _render_mock_answer(
                    case.question,
                    retrieved,
                    grounded=eval_mode == "grounded_judge",
                )
            else:
                answer, meta = generate_answer(case.question, retrieved, self.max_new_tokens)
                usage = meta.get("usage", {})
                cost_usd = usage.get("estimated_cost_usd", 0.0) or 0.0
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)

            # 4) LLM-as-Judge — faithfulness / relevance
            if answer and retrieved:
                context_text = " ".join(
                    str(r.get("text", "")) for r in retrieved if str(r.get("text", "")).strip()
                )
                judge_result = llm_judge(
                    question=case.question,
                    answer=answer,
                    context=context_text,
                    mock=self.mock_llm,
                )
                faithfulness = judge_result.faithfulness
                judge_relevance = judge_result.relevance
                judge_fallback_used = judge_result.fallback_used
                judge_fallback_reason = judge_result.fallback_reason
                if judge_result.usage and not self.mock_llm:
                    judge_cost = judge_result.usage.get("estimated_cost_usd", 0.0) or 0.0
                    cost_usd += judge_cost
                    input_tokens += judge_result.usage.get("input_tokens", 0)
                    output_tokens += judge_result.usage.get("output_tokens", 0)
                    total_tokens += judge_result.usage.get("total_tokens", 0)

        except (RuntimeError, ValueError, OSError, KeyError, APIError) as e:
            failure_type = "error"
            failure_reason = str(e)
            logger.error("Case %s failed: %s", case.case_id, e)

        latency_ms = (time.perf_counter() - t0) * 1000

        # 4) 品質評価
        passed = True
        score = 0.0
        failure_category: str | None = None

        if failure_type:
            passed = False
            score = 0.0
        else:
            threshold = _mode_threshold(case.severity)

            if eval_mode == "exact":
                answer_match = _expected_answer_matches(answer, case.expected_answer)
                passed = answer_match
                score = 1.0 if answer_match else 0.0
                if not passed:
                    failure_type = "keyword_miss"
                    failure_reason = "Expected answer did not match"

            elif eval_mode == "evidence_keyword":
                kw_rate = keyword_match_rate(answer, case.expected_keywords)
                evidence_score = evidence_recall if evidence_recall is not None else 0.0
                answer_match = kw_rate >= threshold
                evidence_match = evidence_score >= threshold
                score = (kw_rate + evidence_score) / 2
                passed = answer_match and evidence_match
                if not evidence_match:
                    failure_type = "retrieval_miss"
                    failure_reason = f"Evidence recall {evidence_score:.0%} < {threshold:.0%}"
                elif not answer_match:
                    failure_type = "keyword_miss"
                    failure_reason = f"Keyword match {kw_rate:.0%} < {threshold:.0%}"

            elif eval_mode == "grounded_judge":
                grounded_threshold = GROUNDED_JUDGE_THRESHOLD
                evidence_score = evidence_recall if evidence_recall is not None else 0.0
                evidence_match = evidence_score >= grounded_threshold
                answer_match = judge_relevance is not None and judge_relevance >= grounded_threshold
                faithfulness_match = faithfulness is not None and faithfulness >= grounded_threshold
                refs = extract_references(answer)
                ref_acc = reference_accuracy(answer, retrieved_ids)
                citation_match = bool(refs) and ref_acc >= 1.0
                score = (
                    evidence_score
                    + (ref_acc if refs else 0.0)
                    + (judge_relevance or 0.0)
                    + (faithfulness or 0.0)
                ) / 4
                passed = evidence_match and citation_match and answer_match and faithfulness_match
                if not evidence_match:
                    failure_type = "retrieval_miss"
                    failure_reason = (
                        f"Evidence recall {evidence_score:.0%} < {grounded_threshold:.0%}"
                    )
                elif not citation_match:
                    failure_type = "bad_reference"
                    failure_reason = "Citation required for grounded_judge"
                elif not faithfulness_match:
                    failure_type = "keyword_miss"
                    failure_reason = (
                        f"Faithfulness {faithfulness or 0.0:.0%} < {grounded_threshold:.0%}"
                    )
                elif not answer_match:
                    failure_type = "keyword_miss"
                    failure_reason = (
                        f"Judge relevance {judge_relevance or 0.0:.0%} < {grounded_threshold:.0%}"
                    )

            else:
                scores: list[float] = []

                # Keyword match
                if case.expected_keywords:
                    kw_rate = keyword_match_rate(answer, case.expected_keywords)
                    answer_match = kw_rate >= threshold
                    scores.append(kw_rate)
                    if kw_rate < threshold:
                        passed = False
                        failure_type = "keyword_miss"
                        failure_reason = f"Keyword match {kw_rate:.0%} < {threshold:.0%}"

                # Retrieval hit (S1 のみ必須)
                if case.expected_chunks and case.severity == "S1" and not ret_hit:
                    passed = False
                    failure_type = failure_type or "retrieval_miss"
                    failure_reason = failure_reason or (
                        f"Expected chunk(s) not in top-{self.context_k}"
                    )

                # Reference accuracy
                ref_acc = reference_accuracy(answer, retrieved_ids)
                scores.append(ref_acc)
                if ref_acc < 0.5 and not self.mock_llm:
                    passed = False
                    failure_type = failure_type or "bad_reference"
                    failure_reason = failure_reason or (f"Reference accuracy {ref_acc:.0%}")

                # Faithfulness (LLM judge)
                if faithfulness is not None:
                    scores.append(faithfulness)

                score = sum(scores) / len(scores) if scores else 1.0

        if not passed:
            failure_category = classify_failure_category(
                failure_type=failure_type,
                failure_reason=failure_reason,
                retrieval_hit=ret_hit,
                retrieved_ids=retrieved_ids,
            )

        return EvalResult(
            case_id=case.case_id,
            severity=case.severity,
            passed=passed,
            score=score,
            answer=answer,
            retrieved_ids=retrieved_ids,
            failure_type=failure_type,
            failure_category=failure_category,
            failure_reason=failure_reason,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            answer_match=answer_match,
            evidence_match=evidence_match,
            retrieval_hit=ret_hit,
            evidence_recall=evidence_recall,
            faithfulness_score=faithfulness,
            judge_relevance=judge_relevance,
            judge_fallback_used=judge_fallback_used,
            judge_fallback_reason=judge_fallback_reason,
        )

    def run_all(self, cases: list[QATestCase], run_id: str | None = None) -> EvalRun:
        """全ケースを実行して EvalRun を返す。"""
        rid = run_id or str(uuid.uuid4())[:12]
        results: list[EvalResult] = []
        for case in cases:
            result = self.run_case(case)
            results.append(result)
            status = "✅" if result.passed else "❌"
            logger.info(
                "[%s] %s (%s) ... %s  (%.0fms)",
                case.case_id,
                case.name,
                case.severity,
                status,
                result.latency_ms,
            )
        return EvalRun(
            run_id=rid,
            timestamp=datetime.now(timezone.utc),
            results=results,
        )

    @staticmethod
    def save_jsonl(run: EvalRun, cases: list[QATestCase], log_dir: str) -> Path:
        """EvalRun を JSONL ファイルに永続化する。"""
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        today = run.timestamp.strftime("%Y%m%d")
        jsonl_file = log_path / f"{today}.jsonl"

        case_map = {c.case_id: c for c in cases}
        with open(jsonl_file, "a", encoding="utf-8") as f:
            for result in run.results:
                case = case_map.get(result.case_id, cases[0])
                record = QARunRecord.from_eval_result(result, run.run_id, case)
                f.write(record.model_dump_json() + "\n")

        return jsonl_file
