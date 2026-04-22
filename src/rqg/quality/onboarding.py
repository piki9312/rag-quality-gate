"""Helpers for validating pack onboarding configuration before first gate run."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

import yaml

from ..serving.connection_validation import validate_http_rag_connection
from .case_merge import load_csv_rows
from .case_schema import infer_source_doc, validate_case_rows
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
    pack_metadata: dict[str, object] = field(default_factory=dict)
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
                "pack_metadata": self.pack_metadata,
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
    pack_metadata: dict[str, object] = {}

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
            pack_metadata={},
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
                raw_pack_metadata = quality_pack_data.get("pack", {})
                if isinstance(raw_pack_metadata, dict):
                    pack_metadata = dict(raw_pack_metadata)
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
            active_case_count = sum(
                1 for row in rows if (row.get("status") or "active").strip() == "active"
            )
            require_active_owner = bool(gate_config and gate_config.staleness_policy_enabled)
            for issue in validate_case_rows(rows, require_active_owner=require_active_owner):
                findings.append(
                    OnboardingFinding(
                        issue.level,
                        "cases",
                        f"{issue.case_id} / {issue.field}: {issue.message}",
                        str(cases_target),
                    )
                )

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
        pack_metadata=pack_metadata,
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
    pack_metadata: dict[str, object] | None = None,
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
        pack_metadata=pack_metadata or {},
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
        for field_name in (
            "pack_name",
            "tenant_name",
            "use_case",
            "vertical",
            "risk_profile",
            "owner",
            "environment",
            "pack_version",
            "source_pack",
        ):
            if not str(pack_meta.get(field_name, "")).strip():
                findings.append(
                    OnboardingFinding(
                        "warn",
                        "quality_pack",
                        f"pack.{field_name} is missing; productized pack metadata is incomplete",
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
