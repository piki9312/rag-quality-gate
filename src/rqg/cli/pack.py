"""rqg init-pack sub-command."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

from .helpers import (
    PACK_PROFILE_ALIASES,
    normalize_pack_profile,
    pack_profile_templates,
    resolve_pack_template_dir,
)


def cmd_init_pack(args: argparse.Namespace) -> int:
    """Scaffold a new pack directory from the selected profile template."""
    if args.list_profiles:
        print("Available init-pack profiles:")
        for profile_name, (template_dir, description) in pack_profile_templates().items():
            status = "ok" if template_dir.exists() else "missing"
            print(f"  - {profile_name}: {description} ({status}) -> {template_dir}")
        if PACK_PROFILE_ALIASES:
            print("Aliases:")
            for alias_name, profile_name in sorted(PACK_PROFILE_ALIASES.items()):
                print(f"  - {alias_name} -> {profile_name}")
        return 0

    if not args.output_dir:
        print(
            "[ERROR] output_dir is required unless --list-profiles is used",
            file=sys.stderr,
        )
        return 1

    requested_profile = args.profile
    selected_profile = normalize_pack_profile(requested_profile)

    try:
        template_dir = resolve_pack_template_dir(requested_profile)
    except FileNotFoundError as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1

    target_dir = Path(args.output_dir)

    if target_dir.exists() and not target_dir.is_dir():
        print(f"[ERROR] Output path is not a directory: {target_dir}", file=sys.stderr)
        return 1

    if target_dir.exists() and any(target_dir.iterdir()) and not args.force:
        print(
            f"[ERROR] Target directory is not empty: {target_dir}. Use --force to overwrite.",
            file=sys.stderr,
        )
        return 1

    if target_dir.exists() and args.force:
        shutil.rmtree(target_dir)

    target_dir.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(template_dir, target_dir)
    if requested_profile == selected_profile:
        print(f"Initialized {selected_profile} pack at {target_dir}")
    else:
        print(
            f"Initialized {selected_profile} pack at {target_dir} "
            f"(requested alias: {requested_profile})"
        )
    return 0
