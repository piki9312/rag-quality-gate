"""RAG Quality Runner — serving layer を呼び出してテストケースを評価する。

これが llmops-lab と rag_app の融合点。
RAGStore で検索 → LLM で回答 → 各 evaluator で品質判定。
"""

from __future__ import annotations

import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..serving.llm_client import generate_answer
from ..serving.rag import RAGStore
from .evaluators.keyword import keyword_match_rate
from .evaluators.reference import reference_accuracy
from .evaluators.retrieval import retrieval_hit, retrieval_precision_at_k
from .models import EvalResult, EvalRun, QARunRecord, QATestCase

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------
# Evaluation thresholds (ケースの severity で分岐)
# ------------------------------------------------------------------

S1_KEYWORD_THRESHOLD = 0.8  # S1: 80% 以上のキーワード一致必須
S2_KEYWORD_THRESHOLD = 0.5  # S2: 50% で OK


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
        failure_type = None
        failure_reason = ""
        answer = ""
        retrieved_ids: list[str] = []
        ret_hit: bool | None = None
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

            # 3) 回答生成
            if not retrieved:
                answer = "検索結果がありません。文書を投入してください。"
            elif self.mock_llm:
                # Mock: retrieved chunk のテキストを結合して返す
                answer = " ".join(r["text"][:100] for r in retrieved)
            else:
                answer, meta = generate_answer(
                    case.question, retrieved, self.max_new_tokens
                )
                usage = meta.get("usage", {})
                cost_usd = usage.get("estimated_cost_usd", 0.0) or 0.0
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)

        except Exception as e:
            failure_type = "error"
            failure_reason = str(e)
            logger.error("Case %s failed: %s", case.case_id, e)

        latency_ms = (time.perf_counter() - t0) * 1000

        # 4) 品質評価
        passed = True
        score = 0.0

        if failure_type:
            passed = False
            score = 0.0
        else:
            scores: list[float] = []

            # Keyword match
            if case.expected_keywords:
                threshold = (
                    S1_KEYWORD_THRESHOLD if case.severity == "S1" else S2_KEYWORD_THRESHOLD
                )
                kw_rate = keyword_match_rate(answer, case.expected_keywords)
                scores.append(kw_rate)
                if kw_rate < threshold:
                    passed = False
                    failure_type = "keyword_miss"
                    failure_reason = (
                        f"Keyword match {kw_rate:.0%} < {threshold:.0%}"
                    )

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
                failure_reason = failure_reason or (
                    f"Reference accuracy {ref_acc:.0%}"
                )

            score = sum(scores) / len(scores) if scores else 1.0

        return EvalResult(
            case_id=case.case_id,
            severity=case.severity,
            passed=passed,
            score=score,
            answer=answer,
            retrieved_ids=retrieved_ids,
            failure_type=failure_type,
            failure_reason=failure_reason,
            latency_ms=latency_ms,
            cost_usd=cost_usd,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            retrieval_hit=ret_hit,
        )

    def run_all(
        self, cases: list[QATestCase], run_id: str | None = None
    ) -> EvalRun:
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
    def save_jsonl(
        run: EvalRun, cases: list[QATestCase], log_dir: str
    ) -> Path:
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
