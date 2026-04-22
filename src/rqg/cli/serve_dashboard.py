"""rqg serve-dashboard sub-command."""

from __future__ import annotations

import argparse
import sys


def cmd_serve_dashboard(args: argparse.Namespace) -> int:
    try:
        import uvicorn
    except ImportError:
        print(
            "[ERROR] uvicorn is required for serve-dashboard. "
            "Install it with: pip install rag-quality-gate[serve]",
            file=sys.stderr,
        )
        return 1

    from ..serving.dashboard import create_dashboard_app

    app = create_dashboard_app(workspace_dir=args.workspace_dir, runs_dir=args.runs_dir)
    base_url = f"http://{args.host}:{args.port}"
    print(f"Serving dashboard at {base_url}/")
    uvicorn.run(app, host=args.host, port=args.port, log_level="info")
    return 0
