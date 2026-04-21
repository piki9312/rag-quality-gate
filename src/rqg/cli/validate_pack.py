"""rqg validate-pack sub-command."""

from __future__ import annotations

import argparse
from pathlib import Path

from .helpers import write_json_data_output, write_text_output


def cmd_validate_pack(args: argparse.Namespace) -> int:
    """Validate pack onboarding inputs before the first gate run."""
    from ..quality.onboarding import render_pack_onboarding_summary, validate_pack_onboarding

    result = validate_pack_onboarding(
        pack_dir=args.pack_dir,
        cases_path=args.cases,
        gate_config_path=args.gate_config,
        quality_pack_path=args.quality_pack,
        docs_dir=args.docs_dir,
        endpoint=args.endpoint,
        api_key_env=args.api_key_env,
        required_env=args.required_env,
        connection_query=args.connection_query,
        connection_top_k=args.connection_top_k,
        connection_timeout_sec=args.connection_timeout_sec,
    )

    summary = render_pack_onboarding_summary(result)
    print(summary, end="")

    if args.output:
        output_path = Path(args.output)
        if output_path.suffix.lower() == ".json":
            saved_path = write_json_data_output(output_path, result.to_payload())
        else:
            saved_path = write_text_output(output_path, summary)
        print(f"Saved onboarding validation report to {saved_path}")

    return 0 if result.ok else 1