"""rqg init-pack sub-command."""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

import yaml

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
    _hydrate_pack_metadata(target_dir=target_dir, selected_profile=selected_profile)
    if requested_profile == selected_profile:
        print(f"Initialized {selected_profile} pack at {target_dir}")
    else:
        print(
            f"Initialized {selected_profile} pack at {target_dir} "
            f"(requested alias: {requested_profile})"
        )
    return 0


def _hydrate_pack_metadata(*, target_dir: Path, selected_profile: str) -> None:
    quality_pack_path = target_dir / "quality-pack.yml"
    if not quality_pack_path.exists():
        return

    payload = yaml.safe_load(quality_pack_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        return
    pack_metadata = payload.get("pack", {})
    if not isinstance(pack_metadata, dict):
        pack_metadata = {}

    existing_version = (
        str(pack_metadata.get("pack_version") or pack_metadata.get("version") or "1.0").strip()
        or "1.0"
    )
    review_steward = str(pack_metadata.get("review_steward", "")).strip()
    pack_metadata.setdefault("pack_name", target_dir.name)
    pack_metadata.setdefault("tenant_name", target_dir.name)
    pack_metadata.setdefault(
        "use_case", str(pack_metadata.get("profile", "")).strip() or selected_profile
    )
    pack_metadata.setdefault(
        "vertical", str(pack_metadata.get("domain", "")).strip() or "internal-docs"
    )
    pack_metadata.setdefault("risk_profile", "high-risk-rag")
    pack_metadata.setdefault("owner", review_steward or "ops-team")
    pack_metadata.setdefault("environment", "poc")
    pack_metadata.setdefault("pack_version", existing_version)
    pack_metadata.setdefault("source_pack", selected_profile)
    pack_metadata.setdefault("created_from_template", True)
    payload["pack"] = pack_metadata
    quality_pack_path.write_text(
        yaml.safe_dump(payload, sort_keys=True, allow_unicode=True),
        encoding="utf-8",
    )
