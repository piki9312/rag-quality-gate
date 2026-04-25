"""Helpers for validating pack onboarding configuration before first gate run."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..serving.connection_validation import validate_http_rag_connection
from .case_merge import load_csv_rows
from .case_schema import (
    LEGACY_FIELD_MAP,
    ValidationError,
    infer_source_doc,
    normalize_legacy_row,
    validate_case_rows,
)
from .check import GateConfig


@dataclass(frozen=True, slots=True)
class OnboardingFinding:
    level: str
    area: str
    message: str
    path: str = ""


@dataclass(slots=True)
class PackOnboardingValidationResult:
    ok: bool
    mode: str
    pack_dir: str
    cases_path: str
    gate_config_path: str
    quality_pack_path: str
    docs_dir: str
    case_count: int = 0
    active_case_count: int = 0
    docs_file_count: int = 0
    failure_pattern_count: int = 0
    error_count: int = 0
    warning_count: int = 0
    env_checks: list[dict[str, object]] = field(default_factory=list)
    connection: dict[str, object] | None = None
    findings: list[OnboardingFinding] = field(default_factory=list)

    def to_payload(self) -> dict[str, object]:
        return {
            "ok": self.ok,
            "mode": self.mode,
            "pack_dir": self.pack_dir,
            "cases": {
                "path": self.cases_path,
                "case_count": self.case_count,
                "active_case_count": self.active_case_count,
            },
            "gate_config": {
                "path": self.gate_config_path,
            },
            "quality_pack": {
                "path": self.quality_pack_path,
                "failure_pattern_count": self.failure_pattern_count,
            },
            "docs": {
                "path": self.docs_dir,
                "file_count": self.docs_file_count,
            },
            "env_checks": self.env_checks,
            "connection": self.connection,
            "finding_counts": {
                "error": self.error_count,
                "warn": self.warning_count,
            },
            "findings": [asdict(item) for item in self.findings],
        }


def validate_pack_onboarding(
    *,
    pack_dir: str | Path,
    cases_path: str | Path | None = None,
    gate_config_path: str | Path | None = None,
    quality_pack_path: str | Path | None = None,
    docs_dir: str | Path | None = None,
    endpoint: str | None = None,
    api_key_env: str | None = None,
    required_env: list[str] | None = None,
    connection_query: str = "healthcheck",
    connection_top_k: int = 3,
    connection_timeout_sec: float = 10.0,
) -> PackOnboardingValidationResult:
    root_dir = Path(pack_dir)
    findings: list[OnboardingFinding] = []
    env_checks: list[dict[str, object]] = []
    connection_payload: dict[str, object] | None = None
    case_count = 0
    active_case_count = 0
    docs_file_count = 0
    failure_pattern_count = 0

    if not root_dir.exists() or not root_dir.is_dir():
        findings.append(
            OnboardingFinding(
                "error",
                "pack",
                "pack directory not found or is not a directory",
                str(root_dir),
            )
        )
        return _build_result(
            root_dir=root_dir,
            findings=findings,
            mode="unconfigured",
            cases_path=Path(cases_path) if cases_path else root_dir / "cases.csv",
            gate_config_path=(
                Path(gate_config_path) if gate_config_path else root_dir / "gate.yml"
            ),
            quality_pack_path=(
                Path(quality_pack_path) if quality_pack_path else root_dir / "quality-pack.yml"
            ),
            docs_dir=Path(docs_dir) if docs_dir else root_dir / "documents",
        )

    quality_pack_target = _resolve_pack_path(root_dir, quality_pack_path, "quality-pack.yml")
    quality_pack_data: dict[str, Any] = {}
    gate_config: GateConfig | None = None
    if quality_pack_target.exists():
        try:
            loaded_quality_pack = yaml.safe_load(quality_pack_target.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            findings.append(
                OnboardingFinding(
                    "error",
                    "quality_pack",
                    f"failed to parse quality-pack.yml: {exc}",
                    str(quality_pack_target),
                )
            )
        else:
            if isinstance(loaded_quality_pack, dict):
                quality_pack_data = loaded_quality_pack
                failure_pattern_count = _validate_quality_pack(
                    findings, quality_pack_target, quality_pack_data
                )
            else:
                findings.append(
                    OnboardingFinding(
                        "error",
                        "quality_pack",
                        "quality-pack.yml must be a YAML mapping",
                        str(quality_pack_target),
                    )
                )
    else:
        findings.append(
            OnboardingFinding(
                "warn",
                "quality_pack",
                "quality-pack.yml is missing; next-action hints and pack metadata will be unavailable",
                str(quality_pack_target),
            )
        )

    cases_target = _resolve_pack_path(
        root_dir,
        cases_path,
        _pack_metadata_path(quality_pack_data, "cases_file", "cases.csv"),
    )
    gate_target = _resolve_pack_path(
        root_dir,
        gate_config_path,
        _pack_metadata_path(quality_pack_data, "gate_file", "gate.yml"),
    )
    docs_target = _resolve_pack_path(
        root_dir,
        docs_dir,
        _pack_metadata_path(quality_pack_data, "documents_dir", "documents"),
    )

    if not gate_target.exists():
        findings.append(
            OnboardingFinding("error", "gate", "gate config not found", str(gate_target))
        )
    else:
        try:
            gate_config = GateConfig.from_yaml(str(gate_target))
        except (OSError, ValueError, yaml.YAMLError) as exc:
            findings.append(
                OnboardingFinding(
                    "error",
                    "gate",
                    f"failed to parse gate config: {exc}",
                    str(gate_target),
                )
            )

    rows: list[dict[str, str]] = []
    if not cases_target.exists():
        findings.append(
            OnboardingFinding("error", "cases", "cases.csv not found", str(cases_target))
        )
    else:
        try:
            rows = load_csv_rows(cases_target)
        except (FileNotFoundError, ValueError) as exc:
            findings.append(
                OnboardingFinding(
                    "error", "cases", f"failed to load cases.csv: {exc}", str(cases_target)
                )
            )
        else:
            case_count = len(rows)
            normalized_rows = [normalize_legacy_row(row) for row in rows]
            active_case_count = sum(
                1
                for row in normalized_rows
                if (row.get("status") or "active").strip() == "active"
            )
            require_active_owner = bool(gate_config and gate_config.staleness_policy_enabled)
            for issue in validate_case_rows(
                normalized_rows, require_active_owner=require_active_owner
            ):
                findings.append(
                    OnboardingFinding(
                        issue.level,
                        "cases",
                        _format_case_finding(issue),
                        str(cases_target),
                    )
                )
            _append_case_onboarding_warnings(findings, cases_target, rows, normalized_rows)
            rows = normalized_rows

    docs_available = docs_target.exists() and docs_target.is_dir()
    if docs_available:
        docs_file_count = sum(1 for path in docs_target.rglob("*") if path.is_file())
        if docs_file_count == 0:
            findings.append(
                OnboardingFinding(
                    "error",
                    "docs",
                    "documents directory is empty",
                    str(docs_target),
                )
            )
        elif rows:
            _validate_docs_against_cases(findings, root_dir, docs_target, rows)

    endpoint = (endpoint or "").strip() or None
    required_env_names = _normalized_env_list(required_env)
    if endpoint and api_key_env:
        required_env_names = _normalized_env_list([*required_env_names, api_key_env])

    for env_name in required_env_names:
        present = bool(os.environ.get(env_name, "").strip())
        env_checks.append({"name": env_name, "present": present})
        if not present:
            findings.append(
                OnboardingFinding(
                    "error",
                    "env",
                    f"required environment variable is not set: {env_name}",
                )
            )

    if endpoint:
        if not any(item.level == "error" and item.area == "env" for item in findings):
            connection_result = validate_http_rag_connection(
                endpoint=endpoint,
                query=connection_query,
                top_k=connection_top_k,
                api_key_env=api_key_env,
                timeout_sec=connection_timeout_sec,
            )
            connection_payload = connection_result.model_dump(mode="json")
            if not connection_result.ok:
                issue_text = "; ".join(connection_result.issues) or connection_result.error_type
                findings.append(
                    OnboardingFinding(
                        "error",
                        "external",
                        f"external connection validation failed: {issue_text}",
                        endpoint,
                    )
                )
    elif not docs_available:
        findings.append(
            OnboardingFinding(
                "error",
                "pack",
                "provide a documents directory or --endpoint for external mode",
                str(docs_target),
            )
        )

    mode = "hybrid" if docs_available and endpoint else "external" if endpoint else "local_docs"
    return _build_result(
        root_dir=root_dir,
        findings=findings,
        mode=mode,
        cases_path=cases_target,
        gate_config_path=gate_target,
        quality_pack_path=quality_pack_target,
        docs_dir=docs_target,
        case_count=case_count,
        active_case_count=active_case_count,
        docs_file_count=docs_file_count,
        failure_pattern_count=failure_pattern_count,
        env_checks=env_checks,
        connection_payload=connection_payload,
    )


def render_pack_onboarding_summary(result: PackOnboardingValidationResult) -> str:
    status = "OK" if result.ok else "NG"
    lines = [f"Pack onboarding validation: {status}", ""]
    lines.append(f"- Mode: {result.mode}")
    lines.append(f"- Pack dir: {result.pack_dir}")
    lines.append(
        f"- Cases: {result.case_count} total / {result.active_case_count} active ({result.cases_path})"
    )
    lines.append(f"- Gate config: {result.gate_config_path}")
    lines.append(
        f"- Quality pack: {result.quality_pack_path} ({result.failure_pattern_count} failure patterns)"
    )
    lines.append(f"- Docs: {result.docs_dir} ({result.docs_file_count} files)")
    if result.connection is not None:
        lines.append(
            "- External connection: "
            f"{'OK' if result.connection.get('ok') else 'NG'} ({result.connection.get('endpoint')})"
        )
    if result.env_checks:
        present_count = sum(1 for item in result.env_checks if item.get("present"))
        lines.append(f"- Required env: {present_count}/{len(result.env_checks)} present")
    lines.append(f"- Findings: {result.error_count} error(s), {result.warning_count} warning(s)")
    if result.findings:
        lines.append("")
        lines.append("Findings:")
        for finding in result.findings:
            path_suffix = f" ({finding.path})" if finding.path else ""
            lines.append(
                f"- [{finding.level.upper()}] {finding.area}: {finding.message}{path_suffix}"
            )
    return "\n".join(lines) + "\n"


def _case_message(problem: str, why: str, fix: str, example: str = "") -> str:
    parts = [f"Problem: {problem}", f"Why it matters: {why}", f"Fix: {fix}"]
    if example:
        parts.append(f"Example: {example}")
    return " | ".join(parts)


def _format_case_finding(issue: ValidationError) -> str:
    prefix = f"{issue.case_id} / {issue.field}: "
    if "Problem:" in issue.message:
        return prefix + issue.message

    if issue.field == "expected_answer":
        return prefix + _case_message(
            "expected_answer is missing.",
            "RAG vendors need a reviewer-approved target answer so the gate can explain why a response passed or failed.",
            "Add the concise answer the customer expects, or keep the row as status=needs_review until the answer is reviewed.",
            "expected_answer=Paid leave requests must be submitted 5 business days in advance.",
        )
    if issue.field == "expected_keywords":
        return prefix + _case_message(
            "expected_keywords is missing.",
            "Keywords catch answer drift in FAQ/RAG responses before delivery to the customer.",
            "Add 2-5 semicolon-separated terms that must appear in a correct answer.",
            "expected_keywords=5 business days;paid leave;advance request",
        )
    if issue.field == "expected_evidence":
        return prefix + _case_message(
            "expected_evidence is missing or not usable.",
            "The gate cannot verify groundedness without a source document section or chunk reference.",
            "Point expected_evidence to the document section that supports the answer.",
            "expected_evidence=leave_policy.md#sec-1",
        )
    if issue.field == "severity":
        return prefix + _case_message(
            issue.message,
            "Severity controls gate strictness; S1 is the production-blocking class for high-risk customer answers.",
            "Use severity=S1 for must-not-fail cases and severity=S2 for standard regression checks.",
            "severity=S1",
        )
    if issue.field == "owner":
        return prefix + _case_message(
            issue.message,
            "Stale active cases need a named owner so monthly quality operation does not become anonymous cleanup.",
            "Fill owner for each active row when staleness policy is enabled.",
            "owner=hr-ops",
        )
    if issue.field == "notes" and "auto-generated expected_answer draft" in issue.message:
        return prefix + _case_message(
            issue.message,
            "Auto-generated answers are useful drafts, but S1/S2 active gates must be based on human-reviewed customer expectations.",
            "Review the answer, remove auto_expected_answer_status:draft, then promote the case to active.",
        )
    return prefix + issue.message


def _append_case_onboarding_warnings(
    findings: list[OnboardingFinding],
    cases_path: Path,
    raw_rows: list[dict[str, str]],
    normalized_rows: list[dict[str, str]],
) -> None:
    for raw_row in raw_rows:
        cid = (raw_row.get("case_id") or "(empty)").strip() or "(empty)"
        _append_legacy_alias_warnings(findings, cases_path, cid, raw_row)

    active_rows = [
        row for row in normalized_rows if (row.get("status") or "active").strip() != "deprecated"
    ]
    _append_severity_design_warnings(findings, cases_path, active_rows)
    _append_category_design_warnings(findings, cases_path, active_rows)

    for row in active_rows:
        cid = (row.get("case_id") or "(empty)").strip() or "(empty)"
        severity = (row.get("severity") or "").strip().upper()
        expected_answer = (row.get("expected_answer") or "").strip()
        evidence = (row.get("expected_evidence") or "").strip()
        keywords = _split_semicolon(row.get("expected_keywords", ""))
        if severity == "S1" and not expected_answer:
            findings.append(
                OnboardingFinding(
                    "warn",
                    "cases",
                    f"{cid} / expected_answer: "
                    + _case_message(
                        "S1 case has no expected_answer.",
                        "S1 is the blocking class; a target answer gives reviewers and customers a clear reason for pass/fail decisions.",
                        "Add a short customer-approved answer, even when eval_mode primarily uses evidence/keywords.",
                        "expected_answer=Paid leave requests must be submitted 5 business days in advance.",
                    ),
                    str(cases_path),
                )
            )
        if severity == "S1" and not evidence:
            findings.append(
                OnboardingFinding(
                    "warn",
                    "cases",
                    f"{cid} / expected_evidence: "
                    + _case_message(
                        "S1 case has no expected_evidence.",
                        "S1 rows are production-blocking checks; without evidence, the vendor cannot explain the pass/fail decision to the customer.",
                        "Add a source section/chunk reference before relying on this row as an S1 gate.",
                        "expected_evidence=hr_rules.md#sec-3",
                    ),
                    str(cases_path),
                )
            )
        if severity == "S1" and not keywords:
            findings.append(
                OnboardingFinding(
                    "warn",
                    "cases",
                    f"{cid} / expected_keywords: "
                    + _case_message(
                        "S1 case has no expected_keywords.",
                        "S1 cases should catch obvious answer drift before the delivery gate is approved.",
                        "Add 2-5 must-include terms for the answer.",
                        "expected_keywords=deadline;5 business days;advance request",
                    ),
                    str(cases_path),
                )
            )
        if 0 < len(keywords) < 2:
            findings.append(
                OnboardingFinding(
                    "warn",
                    "cases",
                    f"{cid} / expected_keywords: "
                    + _case_message(
                        "expected_keywords has fewer than 2 terms.",
                        "A single keyword is often too weak to catch answer drift in customer FAQ/RAG regression checks.",
                        "Add 2-5 business-critical terms separated by semicolons.",
                        "expected_keywords=deadline;5 business days;advance request",
                    ),
                    str(cases_path),
                )
            )


def _append_severity_design_warnings(
    findings: list[OnboardingFinding],
    cases_path: Path,
    active_rows: list[dict[str, str]],
) -> None:
    if not active_rows:
        return
    s1_count = sum(1 for row in active_rows if (row.get("severity") or "").strip().upper() == "S1")
    s2_count = sum(1 for row in active_rows if (row.get("severity") or "").strip().upper() == "S2")
    total = len(active_rows)

    if s1_count == 0:
        findings.append(
            OnboardingFinding(
                "warn",
                "cases",
                _case_message(
                    "Quality Pack has 0 active S1 cases.",
                    "Without S1, validate-pack cannot help you confirm that the customer has at least one production-blocking quality gate.",
                    "Promote the highest-risk FAQ/regulation cases to severity=S1.",
                    "severity=S1 for HR policy, labor rule, or high-risk customer-facing answers.",
                ),
                str(cases_path),
            )
        )
    elif total >= 5 and s1_count == 1:
        findings.append(
            OnboardingFinding(
                "warn",
                "cases",
                _case_message(
                    f"Quality Pack has only 1 S1 case across {total} active cases.",
                    "A single S1 rarely covers enough customer risk for production readiness.",
                    "Add S1 cases for the top failure modes: wrong deadline, wrong eligibility, wrong escalation, and unsupported answer.",
                ),
                str(cases_path),
            )
        )

    if total >= 2 and s1_count == total:
        findings.append(
            OnboardingFinding(
                "warn",
                "cases",
                _case_message(
                    "All active cases are S1.",
                    "If every case blocks release, monthly operation becomes too heavy and teams may stop trusting the gate.",
                    "Keep true must-not-fail cases as S1 and move ordinary regression checks to S2.",
                    "severity=S2 for normal wording, coverage, or low-risk FAQ checks.",
                ),
                str(cases_path),
            )
        )
    if total >= 2 and s2_count == total:
        findings.append(
            OnboardingFinding(
                "warn",
                "cases",
                _case_message(
                    "All active cases are S2.",
                    "A pack with only S2 has a weak blocking gate and may miss high-risk customer-facing failures.",
                    "Choose at least one must-not-fail case and mark it severity=S1.",
                ),
                str(cases_path),
            )
        )


def _append_category_design_warnings(
    findings: list[OnboardingFinding],
    cases_path: Path,
    active_rows: list[dict[str, str]],
) -> None:
    if len(active_rows) < 4:
        return
    counts: dict[str, int] = {}
    for row in active_rows:
        category = (row.get("category") or "general").strip() or "general"
        counts[category] = counts.get(category, 0) + 1
    top_category, top_count = max(counts.items(), key=lambda item: item[1])
    if top_count / len(active_rows) >= 0.8:
        findings.append(
            OnboardingFinding(
                "warn",
                "cases",
                _case_message(
                    f"Category coverage is concentrated in '{top_category}' ({top_count}/{len(active_rows)} active cases).",
                    "A pack concentrated in one category may pass while important customer workflows remain untested.",
                    "Add cases for other high-risk categories such as eligibility, deadline, procedure, exception, and escalation.",
                    "category=deadline / category=eligibility / category=escalation",
                ),
                str(cases_path),
            )
        )


def _append_legacy_alias_warnings(
    findings: list[OnboardingFinding],
    cases_path: Path,
    case_id: str,
    row: dict[str, str],
) -> None:
    for legacy_name, formal_name in LEGACY_FIELD_MAP.items():
        if legacy_name not in row or not str(row.get(legacy_name) or "").strip():
            continue
        findings.append(
            OnboardingFinding(
                "warn",
                "cases",
                f"{case_id} / {legacy_name}: "
                + _case_message(
                    f"legacy alias '{legacy_name}' is still used.",
                    "Legacy aliases remain readable for backward compatibility, but customer-facing Quality Packs are easier to maintain when all rows use the formal 16-column contract.",
                    f"Rename '{legacy_name}' to '{formal_name}' in cases.csv.",
                    f"{formal_name}=...",
                ),
                str(cases_path),
            )
        )


def _split_semicolon(value: object) -> list[str]:
    return [item.strip() for item in str(value or "").split(";") if item.strip()]


def _build_result(
    *,
    root_dir: Path,
    findings: list[OnboardingFinding],
    mode: str,
    cases_path: Path,
    gate_config_path: Path,
    quality_pack_path: Path,
    docs_dir: Path,
    case_count: int = 0,
    active_case_count: int = 0,
    docs_file_count: int = 0,
    failure_pattern_count: int = 0,
    env_checks: list[dict[str, object]] | None = None,
    connection_payload: dict[str, object] | None = None,
) -> PackOnboardingValidationResult:
    error_count = sum(1 for item in findings if item.level == "error")
    warning_count = sum(1 for item in findings if item.level == "warn")
    return PackOnboardingValidationResult(
        ok=error_count == 0,
        mode=mode,
        pack_dir=str(root_dir),
        cases_path=str(cases_path),
        gate_config_path=str(gate_config_path),
        quality_pack_path=str(quality_pack_path),
        docs_dir=str(docs_dir),
        case_count=case_count,
        active_case_count=active_case_count,
        docs_file_count=docs_file_count,
        failure_pattern_count=failure_pattern_count,
        error_count=error_count,
        warning_count=warning_count,
        env_checks=env_checks or [],
        connection=connection_payload,
        findings=findings,
    )


def _validate_quality_pack(
    findings: list[OnboardingFinding],
    quality_pack_path: Path,
    payload: dict[str, Any],
) -> int:
    if not isinstance(payload.get("pack", {}), dict):
        findings.append(
            OnboardingFinding(
                "warn",
                "quality_pack",
                "pack metadata block is missing",
                str(quality_pack_path),
            )
        )
    else:
        pack_meta = payload.get("pack", {})
        review_steward = str(pack_meta.get("review_steward", "")).strip()
        if not review_steward:
            findings.append(
                OnboardingFinding(
                    "warn",
                    "quality_pack",
                    "pack.review_steward is missing; weekly review owner will stay manual",
                    str(quality_pack_path),
                )
            )

    patterns = payload.get("common_failure_patterns", [])
    if patterns is None:
        patterns = []
    if not isinstance(patterns, list):
        findings.append(
            OnboardingFinding(
                "error",
                "quality_pack",
                "common_failure_patterns must be a list",
                str(quality_pack_path),
            )
        )
        return 0

    valid_patterns = 0
    for index, item in enumerate(patterns, start=1):
        if not isinstance(item, dict):
            findings.append(
                OnboardingFinding(
                    "warn",
                    "quality_pack",
                    f"failure pattern #{index} is not a mapping",
                    str(quality_pack_path),
                )
            )
            continue
        name = str(item.get("name", "")).strip()
        action = str(item.get("first_action") or item.get("action") or "").strip()
        if not name:
            findings.append(
                OnboardingFinding(
                    "warn",
                    "quality_pack",
                    f"failure pattern #{index} is missing name",
                    str(quality_pack_path),
                )
            )
            continue
        if not action:
            findings.append(
                OnboardingFinding(
                    "warn",
                    "quality_pack",
                    f"failure pattern '{name}' is missing first_action/action",
                    str(quality_pack_path),
                )
            )
            continue
        valid_patterns += 1

    if valid_patterns == 0:
        findings.append(
            OnboardingFinding(
                "warn",
                "quality_pack",
                "no valid common_failure_patterns were found",
                str(quality_pack_path),
            )
        )
    return valid_patterns


def _validate_docs_against_cases(
    findings: list[OnboardingFinding],
    root_dir: Path,
    docs_dir: Path,
    rows: list[dict[str, str]],
) -> None:
    seen_tokens: set[str] = set()
    for row in rows:
        if (row.get("status") or "active").strip() == "deprecated":
            continue
        source_doc = infer_source_doc(
            expected_evidence=row.get("expected_evidence", ""),
            source_doc=row.get("source_doc", ""),
        )
        normalized = _normalize_source_doc_token(source_doc)
        if not normalized or normalized in seen_tokens:
            continue
        seen_tokens.add(normalized)
        matches = _resolve_source_doc_matches(root_dir, docs_dir, normalized)
        if not matches:
            findings.append(
                OnboardingFinding(
                    "warn",
                    "docs",
                    f"source_doc does not match a file under documents/: {normalized}",
                    str(docs_dir),
                )
            )
        elif len(matches) > 1:
            findings.append(
                OnboardingFinding(
                    "warn",
                    "docs",
                    f"source_doc is ambiguous under documents/: {normalized}",
                    str(docs_dir),
                )
            )


def _resolve_source_doc_matches(root_dir: Path, docs_dir: Path, source_doc: str) -> list[Path]:
    token_path = Path(source_doc.replace("\\", "/"))
    candidates = [root_dir / token_path, docs_dir / token_path]
    matches = [path for path in candidates if path.exists() and path.is_file()]
    if matches:
        return matches
    return [path for path in docs_dir.rglob(token_path.name) if path.is_file()]


def _normalize_source_doc_token(source_doc: str) -> str:
    text = str(source_doc or "").strip().replace("\\", "/")
    if not text:
        return ""
    text = text.split("#", 1)[0]
    if "@" in Path(text).name:
        head, _, tail = Path(text).name.partition("@")
        if head and tail:
            text = str(Path(text).with_name(head))
    if text.startswith("documents/"):
        text = text[len("documents/") :]
    return text.strip("/")


def _resolve_pack_path(root_dir: Path, override: str | Path | None, default_value: str) -> Path:
    value = override if override is not None else default_value
    candidate = Path(str(value))
    return candidate if candidate.is_absolute() else root_dir / candidate


def _pack_metadata_path(payload: dict[str, Any], key: str, default_value: str) -> str:
    value = payload.get(key)
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default_value


def _normalized_env_list(values: list[str] | None) -> list[str]:
    if not values:
        return []
    normalized: list[str] = []
    for value in values:
        env_name = str(value or "").strip()
        if env_name and env_name not in normalized:
            normalized.append(env_name)
    return normalized
