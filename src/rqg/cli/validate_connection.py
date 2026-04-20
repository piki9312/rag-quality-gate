"""rqg validate-connection sub-command."""

from __future__ import annotations

import argparse
from pathlib import Path

from .helpers import write_json_output


def cmd_validate_connection(args: argparse.Namespace) -> int:
    """Validate an external RAG endpoint before running the gate."""
    from ..serving.connection_validation import validate_http_rag_connection

    result = validate_http_rag_connection(
        endpoint=args.endpoint,
        query=args.query,
        top_k=args.top_k,
        api_key_env=args.api_key_env,
        timeout_sec=args.timeout_sec,
    )

    print(f"Connection: {'OK' if result.ok else 'NG'}")
    print(f"Endpoint  : {result.endpoint}")
    print(f"Latency   : {result.latency_ms:.1f} ms")
    print(f"Chunks    : {result.chunk_count}")
    if result.sample_sources:
        print(f"Sources   : {', '.join(result.sample_sources)}")
    if result.issues:
        print(f"Issues    : {'; '.join(result.issues)}")

    if args.output:
        output_path = Path(args.output)
        if output_path.suffix.lower() == ".json":
            saved_path = write_json_output(output_path, result)
            print(f"Saved validation JSON to {saved_path}")
        else:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(_render_markdown(result), encoding="utf-8")
            print(f"Saved validation report to {output_path}")

    return 0 if result.ok else 1


def _render_markdown(result) -> str:
    status = "OK" if result.ok else "NG"
    lines = [f"## External RAG Connection Validation: {status}", ""]
    lines.append(f"- Endpoint: {result.endpoint}")
    lines.append(f"- Query: {result.query}")
    lines.append(f"- Top K: {result.top_k}")
    lines.append(f"- Latency: {result.latency_ms:.1f} ms")
    lines.append(f"- Chunk Count: {result.chunk_count}")
    if result.sample_sources:
        lines.append(f"- Sample Sources: {', '.join(result.sample_sources)}")
    if result.issues:
        lines.append(f"- Issues: {'; '.join(result.issues)}")
    return "\n".join(lines) + "\n"
