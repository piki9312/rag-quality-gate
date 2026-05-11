"""Before/after comparison helpers for gate bundles."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def load_gate_bundle(path: str | Path | None) -> dict[str, Any]:
    if path is None:
        return {}
    bundle_path = Path(path)
    if not bundle_path.exists() or not bundle_path.is_file():
        return {}
    try:
        payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    except ValueError:
        return {}
    return payload if isinstance(payload, dict) else {}


def build_before_after_summary(
    *,
    before_bundle: dict[str, Any],
    after_bundle: dict[str, Any],
) -> dict[str, Any]:
    if not before_bundle or not after_bundle:
        return {}

    before_decision = before_bundle.get("decision", {}) if isinstance(before_bundle, dict) else {}
    after_decision = after_bundle.get("decision", {}) if isinstance(after_bundle, dict) else {}
    before_provenance = before_bundle.get("provenance", {}) or before_decision.get("provenance", {})
    after_provenance = after_bundle.get("provenance", {}) or after_decision.get("provenance", {})
    before_cases = before_bundle.get("cases", [])
    after_cases = after_bundle.get("cases", [])
    before_fail_ids = {
        str(item.get("case_id"))
        for item in before_cases
        if isinstance(item, dict) and str(item.get("pass_fail")) == "fail"
    }
    after_fail_ids = {
        str(item.get("case_id"))
        for item in after_cases
        if isinstance(item, dict) and str(item.get("pass_fail")) == "fail"
    }
    before_s1_fail_ids = {
        str(item.get("case_id"))
        for item in before_cases
        if isinstance(item, dict)
        and str(item.get("pass_fail")) == "fail"
        and str(item.get("severity")).upper() == "S1"
    }
    after_s1_fail_ids = {
        str(item.get("case_id"))
        for item in after_cases
        if isinstance(item, dict)
        and str(item.get("pass_fail")) == "fail"
        and str(item.get("severity")).upper() == "S1"
    }
    compared_fields = [
        "model",
        "prompt_hash",
        "prompt_version",
        "retrieval_config_hash",
        "adapter_config_hash",
        "doc_snapshot_ids",
        "index_version",
        "quality_pack_version",
        "case_set_version",
        "execution_mode",
        "generated_at",
        "change_event_id",
    ]
    provenance_diffs: dict[str, dict[str, object]] = {}
    for field in compared_fields:
        before_value = before_provenance.get(field, before_bundle.get(field))
        after_value = after_provenance.get(field, after_bundle.get(field))
        if before_value == after_value:
            continue
        provenance_diffs[field] = {"before": before_value, "after": after_value}

    return {
        "before_run_id": before_decision.get("run_id"),
        "after_run_id": after_decision.get("run_id"),
        "before_overall_decision": before_bundle.get("overall_decision"),
        "after_overall_decision": after_bundle.get("overall_decision"),
        "before_policy_status": before_decision.get("policy_status"),
        "after_policy_status": after_decision.get("policy_status"),
        "provenance_diffs": provenance_diffs,
        "newly_failing_cases": sorted(after_fail_ids - before_fail_ids),
        "recovered_cases": sorted(before_fail_ids - after_fail_ids),
        "unchanged_failures": sorted(before_fail_ids & after_fail_ids),
        "newly_failing_s1_cases": sorted(after_s1_fail_ids - before_s1_fail_ids),
        "recovered_s1_cases": sorted(before_s1_fail_ids - after_s1_fail_ids),
        "unchanged_s1_failures": sorted(before_s1_fail_ids & after_s1_fail_ids),
        "decision_recommendation": (
            "block"
            if after_decision.get("policy_status") == "block"
            else (
                "needs_human_review"
                if after_decision.get("policy_status") in {"needs_human_review", "warn"}
                else "pass_with_scope_limit"
            )
        ),
    }


def render_before_after_summary_markdown(summary: dict[str, Any]) -> str:
    if not summary:
        return "# Before / After Summary\n\n- Comparison unavailable.\n"
    lines = ["# Before / After Summary", ""]
    lines.append(f"- before_run_id: {summary.get('before_run_id') or '-'}")
    lines.append(f"- after_run_id: {summary.get('after_run_id') or '-'}")
    lines.append(f"- before_policy_status: {summary.get('before_policy_status') or '-'}")
    lines.append(f"- after_policy_status: {summary.get('after_policy_status') or '-'}")
    lines.append("")
    lines.append("## Provenance Diffs")
    provenance_diffs = summary.get("provenance_diffs", {})
    if provenance_diffs:
        for field, values in provenance_diffs.items():
            lines.append(f"- {field}: {values.get('before')!r} -> {values.get('after')!r}")
    else:
        lines.append("- No tracked provenance diffs detected.")
    lines.append("")
    lines.append(
        f"- newly_failing_cases: {', '.join(summary.get('newly_failing_cases', [])) or '-'}"
    )
    lines.append(f"- recovered_cases: {', '.join(summary.get('recovered_cases', [])) or '-'}")
    lines.append(f"- unchanged_failures: {', '.join(summary.get('unchanged_failures', [])) or '-'}")
    lines.append(
        f"- newly_failing_s1_cases: {', '.join(summary.get('newly_failing_s1_cases', [])) or '-'}"
    )
    lines.append(f"- recovered_s1_cases: {', '.join(summary.get('recovered_s1_cases', [])) or '-'}")
    lines.append(
        f"- unchanged_s1_failures: {', '.join(summary.get('unchanged_s1_failures', [])) or '-'}"
    )
    lines.append(f"- decision_recommendation: {summary.get('decision_recommendation') or '-'}")
    return "\n".join(lines) + "\n"
