"""Read-only dashboard for packs, runs, and monthly summaries."""

from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

import yaml
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from ..quality.history import load_gate_decision_history
from ..quality.monthly_summary import build_monthly_summary_payload


def create_dashboard_app(
    *,
    workspace_dir: str,
    runs_dir: str | None = None,
) -> FastAPI:
    app = FastAPI(title="Proof Gate Dashboard", version="0.1.0")
    app.state.workspace_dir = Path(workspace_dir)
    app.state.runs_dir = Path(runs_dir) if runs_dir else Path(workspace_dir) / "runs"

    @app.get("/", response_class=HTMLResponse)
    def pack_list() -> str:
        packs = _scan_packs(app.state.workspace_dir)
        runs = _scan_runs(app.state.runs_dir)
        latest_by_pack = _latest_runs_by_pack(runs)
        rows = []
        for pack in packs:
            latest = latest_by_pack.get(pack["pack_name"])
            rows.append(
                "<tr>"
                f"<td><a href='/packs/{_esc(pack['pack_name'])}'>{_esc(pack['pack_name'])}</a></td>"
                f"<td>{_esc(pack.get('tenant_name', '-'))}</td>"
                f"<td>{_esc(latest['status'] if latest else '-')}</td>"
                f"<td>{_esc(latest['run_id'] if latest else '-')}</td>"
                "</tr>"
            )
        return _page(
            "Packs",
            "<table><tr><th>Pack</th><th>Tenant</th><th>Latest Gate</th><th>Latest Run</th></tr>"
            + "".join(rows)
            + "</table>",
        )

    @app.get("/packs/{pack_name}", response_class=HTMLResponse)
    def pack_detail(pack_name: str) -> str:
        packs = {pack["pack_name"]: pack for pack in _scan_packs(app.state.workspace_dir)}
        pack = packs.get(pack_name)
        if pack is None:
            raise HTTPException(status_code=404, detail="Pack not found")
        runs = [run for run in _scan_runs(app.state.runs_dir) if run["pack_name"] == pack_name]
        latest = runs[-1] if runs else None
        metadata_lines = "".join(
            f"<li><strong>{_esc(key)}</strong>: {_esc(value)}</li>"
            for key, value in sorted(pack.items())
            if key not in {"path"}
        )
        latest_html = (
            f"<p>Latest gate: <a href='/packs/{_esc(pack_name)}/runs/{_esc(latest['run_id'])}'>{_esc(latest['status'])}</a></p>"
            if latest
            else "<p>No runs found.</p>"
        )
        nav = (
            f"<p><a href='/packs/{_esc(pack_name)}/runs'>Runs</a> | "
            f"<a href='/packs/{_esc(pack_name)}/latest'>Latest gate</a> | "
            f"<a href='/packs/{_esc(pack_name)}/fail-cases'>Fail cases</a> | "
            f"<a href='/packs/{_esc(pack_name)}/monthly'>Monthly summary</a></p>"
        )
        return _page(pack_name, nav + latest_html + f"<ul>{metadata_lines}</ul>")

    @app.get("/packs/{pack_name}/runs", response_class=HTMLResponse)
    def run_list(pack_name: str) -> str:
        runs = [run for run in _scan_runs(app.state.runs_dir) if run["pack_name"] == pack_name]
        if not runs:
            raise HTTPException(status_code=404, detail="No runs found for pack")
        rows = []
        for run in reversed(runs):
            rows.append(
                "<tr>"
                f"<td><a href='/packs/{_esc(pack_name)}/runs/{_esc(run['run_id'])}'>{_esc(run['run_id'])}</a></td>"
                f"<td>{_esc(run['status'])}</td>"
                f"<td>{_esc('{:.1f}%'.format(run['overall_pass_rate']))}</td>"
                f"<td>{_esc('{:.1f}%'.format(run['s1_pass_rate']))}</td>"
                "</tr>"
            )
        return _page(
            f"Runs for {pack_name}",
            "<table><tr><th>Run</th><th>Status</th><th>Overall</th><th>S1</th></tr>"
            + "".join(rows)
            + "</table>",
        )

    @app.get("/packs/{pack_name}/runs/{run_id}", response_class=HTMLResponse)
    def run_detail(pack_name: str, run_id: str) -> str:
        run = _find_run(_scan_runs(app.state.runs_dir), pack_name=pack_name, run_id=run_id)
        reliability = run["decision"]
        next_actions = "".join(
            f"<li>{_esc(item['failure_category'])}: {_esc(item['action'])}</li>"
            for item in reliability.get("next_actions", [])
        )
        reasons = "".join(f"<li>{_esc(item)}</li>" for item in reliability.get("reasons", []))
        comparison = run.get("history_summary", {}).get("comparison") or {}
        return _page(
            f"Run {run_id}",
            (
                f"<p>Status: {_esc(run['status'])}</p>"
                f"<p>Overall pass rate: {_esc('{:.1f}%'.format(run['overall_pass_rate']))}</p>"
                f"<p>S1 pass rate: {_esc('{:.1f}%'.format(run['s1_pass_rate']))}</p>"
                f"<p>S1 fail count: {_esc('{:.0f}'.format(run['s1_fail_count']))}</p>"
                f"<p>Judge reliability: {_esc(reliability.get('judge_reliability', 'unknown'))}</p>"
                f"<p>Needs human review: {_esc(reliability.get('needs_human_review'))}</p>"
                f"<p>Previous diff: {_esc(comparison.get('previous_run_id', '-'))} -> {_esc(comparison.get('current_run_id', '-'))}</p>"
                f"<h3>Reasons</h3><ul>{reasons or '<li>None</li>'}</ul>"
                f"<h3>Next Actions</h3><ul>{next_actions or '<li>None</li>'}</ul>"
            ),
        )

    @app.get("/packs/{pack_name}/latest", response_class=HTMLResponse)
    def latest_gate(pack_name: str) -> str:
        runs = [run for run in _scan_runs(app.state.runs_dir) if run["pack_name"] == pack_name]
        if not runs:
            raise HTTPException(status_code=404, detail="No runs found for pack")
        latest = runs[-1]
        return run_detail(pack_name, latest["run_id"])

    @app.get("/packs/{pack_name}/fail-cases", response_class=HTMLResponse)
    def fail_cases(pack_name: str) -> str:
        runs = [run for run in _scan_runs(app.state.runs_dir) if run["pack_name"] == pack_name]
        if not runs:
            raise HTTPException(status_code=404, detail="No runs found for pack")
        latest = runs[-1]
        fail_case_rows = []
        for action in latest["decision"].get("next_actions", []):
            case_ids = ", ".join(action.get("affected_case_ids", [])) or "-"
            fail_case_rows.append(
                f"<tr><td>{_esc(action.get('failure_category', '-'))}</td><td>{_esc(case_ids)}</td></tr>"
            )
        return _page(
            f"Fail cases for {pack_name}",
            "<table><tr><th>Failure Category</th><th>Affected Cases</th></tr>"
            + "".join(fail_case_rows)
            + "</table>",
        )

    @app.get("/packs/{pack_name}/monthly", response_class=HTMLResponse)
    def monthly(pack_name: str) -> str:
        monthly_file = app.state.runs_dir / pack_name / "monthly-summary.json"
        if monthly_file.exists():
            summary = json.loads(monthly_file.read_text(encoding="utf-8"))
        else:
            history_path = app.state.runs_dir / pack_name / "gate-decisions.jsonl"
            summary = build_monthly_summary_payload(load_gate_decision_history(history_path))
        unresolved = "".join(
            f"<li>{_esc(item)}</li>" for item in summary.get("unresolved_issues", [])
        )
        return _page(
            f"Monthly summary for {pack_name}",
            (
                f"<p>Total runs: {_esc(summary.get('total_runs', 0))}</p>"
                f"<p>Blocked runs: {_esc(summary.get('blocked_runs', 0))}</p>"
                f"<p>S1 incidents detected: {_esc(summary.get('s1_incidents_detected', 0))}</p>"
                f"<p>Trend summary: {_esc(summary.get('quality_trend_summary', '-'))}</p>"
                f"<h3>Unresolved issues</h3><ul>{unresolved or '<li>None</li>'}</ul>"
            ),
        )

    return app


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
    for report_file in sorted(runs_dir.glob("**/gate-report.json")):
        payload = _load_json(report_file)
        decision = payload.get("decision", {})
        if not isinstance(decision, dict):
            continue
        pack = decision.get("pack", {})
        if not isinstance(pack, dict):
            pack = {}
        pack_name = str(pack.get("pack_name", "")).strip() or report_file.parent.name
        metrics = decision.get("metrics", {}) if isinstance(decision.get("metrics"), dict) else {}
        items.append(
            {
                "pack_name": pack_name,
                "run_id": str(decision.get("run_id", report_file.parent.name)),
                "status": str(decision.get("status", "unknown")).upper(),
                "overall_pass_rate": float(metrics.get("overall_pass_rate", 0.0) or 0.0),
                "s1_pass_rate": float(metrics.get("s1_pass_rate", 0.0) or 0.0),
                "s1_fail_count": float(metrics.get("s1_fail_count", 0.0) or 0.0),
                "decision": decision,
                "history_summary": payload.get("history_summary", {}),
                "path": str(report_file.parent),
            }
        )
    return sorted(items, key=lambda item: (item["pack_name"], item["run_id"]))


def _latest_runs_by_pack(runs: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    latest: dict[str, dict[str, Any]] = {}
    for run in runs:
        latest[run["pack_name"]] = run
    return latest


def _find_run(runs: list[dict[str, Any]], *, pack_name: str, run_id: str) -> dict[str, Any]:
    for run in runs:
        if run["pack_name"] == pack_name and run["run_id"] == run_id:
            return run
    raise HTTPException(status_code=404, detail="Run not found")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _page(title: str, body: str) -> str:
    return (
        "<html><body>"
        f"<h1>{_esc(title)}</h1>"
        "<p><a href='/'>Packs</a></p>"
        f"{body}"
        "</body></html>"
    )


def _esc(value: object) -> str:
    return html.escape(str(value))
