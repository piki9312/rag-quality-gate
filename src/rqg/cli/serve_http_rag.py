"""rqg serve-http-rag sub-command."""

from __future__ import annotations

import argparse
import os
import sys


def cmd_serve_http_rag(args: argparse.Namespace) -> int:
    """Expose the built-in FAISS store via the external HTTP /search contract."""
    try:
        import uvicorn
    except ImportError:
        print(
            "[ERROR] uvicorn is required for serve-http-rag. "
            "Install it with: pip install rag-quality-gate[serve]",
            file=sys.stderr,
        )
        return 1

    if args.api_key_env and not os.environ.get(args.api_key_env, "").strip():
        print(
            f"[ERROR] Environment variable not set: {args.api_key_env}",
            file=sys.stderr,
        )
        return 1

    try:
        from ..serving.local_http_rag import create_local_http_rag_app

        app = create_local_http_rag_app(
            index_dir=args.index_dir,
            docs_dir=args.docs_dir,
            api_key_env=args.api_key_env,
        )
    except (ImportError, ValueError) as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    base_url = f"http://{args.host}:{args.port}"
    print(f"Serving local HTTP RAG at {base_url}/search")
    print(f"Health endpoint     : {base_url}/health")
    print(f"Notify capture sink : {base_url}/notify")
    print(f"Notify event log    : {base_url}/notify/events")
    if args.docs_dir:
        print(f"Docs directory      : {args.docs_dir}")
    print(f"Index directory     : {args.index_dir}")
    if args.api_key_env:
        print(f"Bearer auth env     : {args.api_key_env}")

    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0