#!/usr/bin/env python3
"""
v1 to v2 Manifest Migration
============================

Converts a v1 (single-platform) manifest from the original
medium-image-generator skill into a v2 (cross-platform) manifest.

v1 schema:
    {
      "schema_version": 1,
      "blog_owner": "...",
      "entries": [
        {
          "id": "...",
          "post_slug": "...",
          "post_title": "...",
          "post_date": "YYYY-MM-DD",
          "post_url": "...",
          "style": "...",
          "palette_id": "...",
          "compositions": {hero: ..., inline_1: ..., ...},
          "subject_themes": [...],
          "prompts": {hero: ..., inline_1: ..., ...},
          "generated_image_paths": {...},
          "notes": "..."
        }
      ]
    }

v2 schema (cross-platform):
    {
      "schema_version": 2,
      "blog_owner": "...",
      "content_pieces": [
        {
          "content_id": "...",
          "canonical_title": "...",
          "canonical_slug": "...",
          "first_seen_date": "YYYY-MM-DD",
          "subject_themes": [...],
          "shared_identity": {"style": "...", "palette_id": "..."},
          "platform_outputs": {
            "medium": { format, generated_at, compositions, prompts,
                        image_paths, notes },
            "linkedin": null, "twitter": null, "instagram": null, "meta": null
          }
        }
      ]
    }

Each v1 entry becomes a v2 content_piece with the medium platform output
populated from the entry data.

Usage:
    python migrate_v1_to_v2.py /path/to/v1/manifest.json [--output /path/to/v2/manifest.json] [--keep-backup]

By default:
    - Reads from <manifest_path>
    - Writes to <manifest_path> (in place)
    - Backs up the original to <manifest_path>.v1.backup
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def migrate_entry(v1_entry: dict[str, Any]) -> dict[str, Any]:
    """Convert a single v1 entry into a v2 content_piece."""
    style = v1_entry.get("style") or "editorial"
    palette = v1_entry.get("palette_id") or "bone-and-rust"

    # Build the medium platform output from v1 data.
    compositions = v1_entry.get("compositions") or {}
    prompts = v1_entry.get("prompts") or {}
    image_paths = v1_entry.get("generated_image_paths") or {}
    post_date = v1_entry.get("post_date") or datetime.now(timezone.utc).strftime("%Y-%m-%d")

    medium_output: dict[str, Any] = {
        "format": "hero",  # v1 entries imply hero + inline_*
        "generated_at": post_date,
        "compositions": dict(compositions),
        "prompts": dict(prompts),
        "image_paths": dict(image_paths),
        "notes": v1_entry.get("notes") or "",
    }

    return {
        "content_id": v1_entry.get("id") or str(uuid.uuid4()),
        "canonical_title": v1_entry.get("post_title") or "Untitled",
        "canonical_slug": v1_entry.get("post_slug") or f"untitled-{uuid.uuid4().hex[:8]}",
        "first_seen_date": post_date,
        "subject_themes": list(v1_entry.get("subject_themes") or []),
        "shared_identity": {"style": style, "palette_id": palette},
        "platform_outputs": {
            "medium": medium_output,
            "linkedin": None,
            "twitter": None,
            "instagram": None,
            "meta": None,
        },
        # Carry the post_url forward as a top-level field on the piece.
        "post_url": v1_entry.get("post_url") or "",
    }


def migrate_manifest(v1: dict[str, Any]) -> dict[str, Any]:
    """Migrate a full v1 manifest to v2."""
    if v1.get("schema_version") == 2:
        # Already v2; return as-is.
        return v1

    if v1.get("schema_version") not in (None, 1):
        raise ValueError(
            f"Unknown schema_version {v1.get('schema_version')!r}. "
            "Migration only supports v1 → v2."
        )

    pieces: list[dict[str, Any]] = []
    for entry in v1.get("entries", []):
        if not isinstance(entry, dict):
            continue
        pieces.append(migrate_entry(entry))

    pieces.sort(key=lambda p: str(p.get("first_seen_date") or ""), reverse=True)

    now = datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": 2,
        "blog_owner": v1.get("blog_owner") or "",
        "created_at": v1.get("created_at") or now,
        "updated_at": now,
        "content_pieces": pieces,
        "_migrated_from_v1": True,
        "_migration_date": now,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate v1 manifest to v2 cross-platform schema.")
    parser.add_argument("manifest", type=Path, help="Path to v1 manifest.json (will be migrated in place by default)")
    parser.add_argument("--output", type=Path, default=None,
                        help="Optional output path (defaults to overwriting input)")
    parser.add_argument("--no-backup", action="store_true",
                        help="Skip the backup file (default: keep .v1.backup)")
    args = parser.parse_args()

    if not args.manifest.exists():
        print(f"ERROR: file not found: {args.manifest}", file=sys.stderr)
        return 1

    try:
        with args.manifest.open("r", encoding="utf-8") as f:
            v1 = json.load(f)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"ERROR: cannot parse manifest: {exc}", file=sys.stderr)
        return 2

    try:
        v2 = migrate_manifest(v1)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 3

    output_path = args.output or args.manifest

    # Backup the original.
    if not args.no_backup and output_path == args.manifest:
        backup_path = args.manifest.with_suffix(args.manifest.suffix + ".v1.backup")
        shutil.copy2(args.manifest, backup_path)
        print(f"Backed up v1 manifest to: {backup_path}", file=sys.stderr)

    # Write v2.
    with output_path.open("w", encoding="utf-8") as f:
        json.dump(v2, f, indent=2, ensure_ascii=False)

    print(json.dumps({
        "status": "ok",
        "input": str(args.manifest),
        "output": str(output_path),
        "v1_entries": len(v1.get("entries", [])),
        "v2_content_pieces": len(v2["content_pieces"]),
        "backup_kept": not args.no_backup,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
