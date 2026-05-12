#!/usr/bin/env python3
"""
visual_engine CLI
=================

Single CLI that platform skills shell out to for all major operations.
This avoids each platform skill needing to import Python directly.

Subcommands:
    rotate              Run rotation engine for a platform
    shared-identity     Compute a shared style+palette across platforms
    build-prompt        Build a Gemini prompt
    generate            Generate an image via fal.ai
    manifest get        Read content_pieces from manifest
    manifest find       Find a content piece by slug/title (fuzzy)
    manifest upsert     Insert or update a content piece
    manifest add-output Add a platform output to a content piece
    manifest validate   Validate a manifest

Each subcommand outputs JSON to stdout. Errors go to stderr with non-zero exit.

Usage examples:
    python engine.py rotate --manifest path.json --platform medium
    python engine.py shared-identity --manifest path.json --platforms medium,linkedin,twitter
    python engine.py build-prompt --platform medium --format hero --style editorial \\
        --palette bone-and-rust --composition centered-subject \\
        --subject "A woman at a wooden desk reviewing invoices"
    python engine.py generate --prompt "..." --aspect 16:9 --output /path/to/image.png
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# Add this directory to path so sibling modules import.
SCRIPTS_DIR = Path(__file__).parent
sys.path.insert(0, str(SCRIPTS_DIR))

ENGINE_DIR = SCRIPTS_DIR.parent  # visual-engine/

from constants import ALL_COMPOSITIONS, ALL_PALETTES, ALL_STYLES  # noqa: E402
from fal_client_wrapper import GenerationError, generate_image  # noqa: E402
from manifest_io import (  # noqa: E402
    fuzzy_match_piece,
    is_suspicious_location,
    load_manifest,
    save_manifest,
    slugify,
    upsert_content_piece,
    upsert_platform_output,
    validate_manifest,
)
from platforms import all_platforms, get_format, get_platform  # noqa: E402
from prompt_builder import build_prompt  # noqa: E402
from rotation import compute_rotation, compute_shared_identity  # noqa: E402


def emit(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, ensure_ascii=False, default=str))


def emit_error(message: str, error_type: str = "error", exit_code: int = 1) -> int:
    emit({"status": "error", "error_type": error_type, "message": message})
    return exit_code


# ---------------------------------------------------------------------------
# Subcommand: rotate
# ---------------------------------------------------------------------------


def cmd_rotate(args: argparse.Namespace) -> int:
    try:
        manifest, was_corrupt = load_manifest(Path(args.manifest))
    except ValueError as exc:
        return emit_error(str(exc), "schema_mismatch", 2)

    try:
        result = compute_rotation(
            manifest,
            args.platform,
            post_type=args.post_type,
            locked_style=args.locked_style,
            locked_palette=args.locked_palette,
        )
    except KeyError as exc:
        return emit_error(str(exc), "unknown_platform", 1)

    result["was_corrupt_recovered"] = was_corrupt
    emit(result)
    return 0


# ---------------------------------------------------------------------------
# Subcommand: shared-identity
# ---------------------------------------------------------------------------


def cmd_shared_identity(args: argparse.Namespace) -> int:
    try:
        manifest, was_corrupt = load_manifest(Path(args.manifest))
    except ValueError as exc:
        return emit_error(str(exc), "schema_mismatch", 2)

    platforms = [p.strip() for p in args.platforms.split(",") if p.strip()]
    if not platforms:
        return emit_error("--platforms cannot be empty", "bad_args", 1)

    try:
        result = compute_shared_identity(manifest, platforms, post_type=args.post_type)
    except (KeyError, ValueError) as exc:
        return emit_error(str(exc), "bad_args", 1)

    result["was_corrupt_recovered"] = was_corrupt
    emit(result)
    return 0


# ---------------------------------------------------------------------------
# Subcommand: build-prompt
# ---------------------------------------------------------------------------


def cmd_build_prompt(args: argparse.Namespace) -> int:
    try:
        prompt, fmt, metadata = build_prompt(
            platform_id=args.platform,
            format_name=args.format,
            style=args.style,
            palette_id=args.palette,
            composition=args.composition,
            subject=args.subject,
            engine_dir=ENGINE_DIR,
            extra_lighting=args.lighting or "",
            custom_negatives=args.negatives or "",
            protagonist_mode=args.protagonist_mode,
            text_mode=args.text_mode,
        )
    except (FileNotFoundError, KeyError, ValueError) as exc:
        return emit_error(str(exc), "bad_args", 1)

    emit({
        "status": "ok",
        "prompt": prompt,
        "aspect_ratio": fmt.aspect_ratio,
        "width": fmt.width,
        "height": fmt.height,
        "format_name": fmt.name,
        "label_risk_detected": metadata["label_risk_detected"],
        "label_risk_reason": metadata["label_risk_reason"],
        "protagonist_mode_resolved": metadata["protagonist_mode_resolved"],
        "text_mode": args.text_mode,
    })
    return 0


# ---------------------------------------------------------------------------
# Subcommand: generate
# ---------------------------------------------------------------------------


def cmd_generate(args: argparse.Namespace) -> int:
    output_path = Path(args.output)

    # File-exists check (Q4 decision): unless --overwrite is passed, refuse to
    # regenerate over an existing image. The skill catches this status and
    # asks the user whether to reuse the existing file or regenerate.
    if not args.overwrite and output_path.exists():
        try:
            size = output_path.stat().st_size
            mtime = output_path.stat().st_mtime
        except OSError:
            size = 0
            mtime = 0.0

        # Only treat as "existing" if it's a real image (>1KB). Smaller files
        # are likely stubs/errors from a previous failure and should be regenerated.
        if size >= 1024:
            from datetime import datetime, timezone
            iso_mtime = datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
            emit({
                "status": "file_exists",
                "local_path": str(output_path),
                "size_bytes": size,
                "modified_at": iso_mtime,
                "message": (
                    f"Image already exists at {output_path}. "
                    f"Pass --overwrite to regenerate."
                ),
            })
            # Exit code 4 = file_exists (distinct from 0=ok, 1=bad_args, 2=generation_error)
            return 4

    # Quality-gate retry loop. When --quality-gate is cheap or strict and the
    # gate flags the image, we regenerate up to --quality-max-retries times
    # before giving up and returning the last image with the gate's verdict.
    quality_attempts: list[dict[str, Any]] = []
    quality_tier = getattr(args, "quality_gate", "off")
    max_retries = max(0, int(getattr(args, "quality_max_retries", 0)))

    attempt_count = 0
    while True:
        attempt_count += 1
        try:
            if args.provider == "openai-gpt-image":
                from openai_provider import OpenAIGenerationError, generate_image as openai_generate
                try:
                    result = openai_generate(
                        prompt=args.prompt,
                        aspect_ratio=args.aspect,
                        output_path=output_path,
                        model=args.openai_model,
                        quality=args.quality,
                        output_format=args.output_format,
                        output_compression=args.output_compression,
                        width_hint=args.width or 0,
                        height_hint=args.height or 0,
                        timeout=args.timeout,
                        retry_once=not args.no_retry,
                    )
                except OpenAIGenerationError as exc:
                    return emit_error(exc.message, exc.error_type, 2)
            else:
                # Default provider: fal-gemini (Gemini 3 Pro Image via fal.ai)
                result = generate_image(
                    prompt=args.prompt,
                    aspect_ratio=args.aspect,
                    output_path=output_path,
                    timeout=args.timeout,
                    retry_once=not args.no_retry,
                )
                result["provider"] = "fal-gemini"
        except GenerationError as exc:
            return emit_error(exc.message, exc.error_type, 2)

        # Post-generation OCR check (safety net for text leakage).
        if not args.skip_ocr:
            from text_detection import detect_text_in_image
            ocr_result = detect_text_in_image(Path(args.output))
            if args.text_mode == "allow":
                ocr_result["passed"] = True
                ocr_result["text_mode"] = "allow"
            else:
                ocr_result["text_mode"] = "block"
            result["text_detection"] = ocr_result
        else:
            result["text_detection"] = {"status": "skipped", "passed": True, "text_mode": args.text_mode}

        # Quality gate (vision-model scorecard). Off by default.
        if quality_tier in ("cheap", "strict"):
            from quality_gate import evaluate_image
            qr = evaluate_image(
                Path(args.output),
                tier=quality_tier,
                prompt_context=args.prompt,
                palette_hint=getattr(args, "quality_palette_hint", "") or "",
                style_hint=getattr(args, "quality_style_hint", "") or "",
                axis_floor=int(getattr(args, "quality_axis_floor", 6)),
                provider=getattr(args, "quality_provider", "auto"),
                model=getattr(args, "quality_model", "") or None,
            )
            attempt_record = qr.to_dict()
            attempt_record["attempt"] = attempt_count
            quality_attempts.append(attempt_record)
            result["quality_gate"] = attempt_record
            result["quality_attempts"] = quality_attempts

            should_retry = (
                qr.status == "ok"
                and not qr.passed
                and attempt_count <= max_retries
            )
            if should_retry:
                # Loop: regenerate. Existing file gets overwritten.
                continue
        else:
            result["quality_gate"] = {"status": "off", "passed": True, "tier": "off"}

        break

    emit(result)
    return 0


# ---------------------------------------------------------------------------
# Subcommand: manifest
# ---------------------------------------------------------------------------


def cmd_manifest_get(args: argparse.Namespace) -> int:
    try:
        manifest, was_corrupt = load_manifest(Path(args.manifest))
    except ValueError as exc:
        return emit_error(str(exc), "schema_mismatch", 2)

    if args.summary:
        pieces = manifest.get("content_pieces", [])
        platform_counts: dict[str, int] = {}
        for piece in pieces:
            for pid, output in (piece.get("platform_outputs") or {}).items():
                if output:
                    platform_counts[pid] = platform_counts.get(pid, 0) + 1
        emit({
            "schema_version": manifest.get("schema_version"),
            "blog_owner": manifest.get("blog_owner"),
            "total_pieces": len(pieces),
            "platform_counts": platform_counts,
            "latest_date": pieces[0].get("first_seen_date") if pieces else None,
            "was_corrupt_recovered": was_corrupt,
        })
        return 0

    emit(manifest)
    return 0


def cmd_manifest_find(args: argparse.Namespace) -> int:
    try:
        manifest, was_corrupt = load_manifest(Path(args.manifest))
    except ValueError as exc:
        return emit_error(str(exc), "schema_mismatch", 2)

    piece, score = fuzzy_match_piece(
        manifest,
        title=args.title,
        slug=args.slug,
        threshold=args.threshold,
    )
    emit({
        "status": "ok",
        "match": piece,
        "confidence": score,
        "matched": piece is not None,
        "was_corrupt_recovered": was_corrupt,
    })
    return 0


def cmd_manifest_upsert(args: argparse.Namespace) -> int:
    from manifest_lock import for_read_modify_write
    manifest_path = Path(args.manifest)

    with for_read_modify_write(manifest_path):
        try:
            manifest, was_corrupt = load_manifest(manifest_path)
        except ValueError as exc:
            return emit_error(str(exc), "schema_mismatch", 2)

        themes = [t.strip() for t in (args.themes or "").split(",") if t.strip()]
        shared_identity = {"style": args.style, "palette_id": args.palette}

        try:
            piece, action = upsert_content_piece(
                manifest,
                canonical_title=args.title,
                canonical_slug=args.slug or slugify(args.title),
                subject_themes=themes,
                shared_identity=shared_identity,
                first_seen_date=args.date,
                content_id=args.content_id,
            )
        except ValueError as exc:
            return emit_error(str(exc), "bad_args", 1)

        save_manifest(manifest_path, manifest)

    emit({
        "status": "ok",
        "action": action,
        "content_id": piece["content_id"],
        "canonical_slug": piece["canonical_slug"],
        "was_corrupt_recovered": was_corrupt,
    })
    return 0


def cmd_manifest_add_output(args: argparse.Namespace) -> int:
    from manifest_lock import for_read_modify_write
    manifest_path = Path(args.manifest)

    with for_read_modify_write(manifest_path):
        try:
            manifest, was_corrupt = load_manifest(manifest_path)
        except ValueError as exc:
            return emit_error(str(exc), "schema_mismatch", 2)

        # Find the piece by content_id or slug.
        target = None
        if args.content_id:
            for piece in manifest.get("content_pieces", []):
                if piece.get("content_id") == args.content_id:
                    target = piece
                    break
        elif args.slug:
            for piece in manifest.get("content_pieces", []):
                if piece.get("canonical_slug") == args.slug:
                    target = piece
                    break
        else:
            return emit_error("Must provide --content-id or --slug", "bad_args", 1)

        if not target:
            return emit_error("Content piece not found", "not_found", 1)

        # Parse compositions and prompts. Use ||| separator.
        SEP = "|||"

        def parse_pairs(s: str) -> dict[str, str]:
            if not s:
                return {}
            out: dict[str, str] = {}
            for pair in s.split(SEP):
                if "=" not in pair:
                    continue
                k, v = pair.split("=", 1)
                out[k.strip()] = v.strip()
            return out

        compositions = parse_pairs(args.compositions)
        prompts = parse_pairs(args.prompts)
        image_paths = parse_pairs(args.image_paths) if args.image_paths else {}

        try:
            action = upsert_platform_output(
                target,
                platform_id=args.platform,
                format_name=args.format,
                compositions=compositions,
                prompts=prompts,
                image_paths=image_paths,
                notes=args.notes or "",
                generated_at=args.date,
            )
        except ValueError as exc:
            return emit_error(str(exc), "bad_args", 1)

        save_manifest(manifest_path, manifest)

    emit({
        "status": "ok",
        "action": action,
        "platform": args.platform,
        "content_id": target["content_id"],
        "was_corrupt_recovered": was_corrupt,
    })
    return 0


def cmd_manifest_validate(args: argparse.Namespace) -> int:
    try:
        manifest, was_corrupt = load_manifest(Path(args.manifest), auto_create=False)
    except FileNotFoundError as exc:
        return emit_error(str(exc), "not_found", 1)
    except ValueError as exc:
        return emit_error(str(exc), "schema_mismatch", 2)

    errors = validate_manifest(manifest)
    emit({
        "status": "ok" if not errors else "invalid",
        "valid": not errors,
        "errors": errors,
        "was_corrupt_recovered": was_corrupt,
    })
    return 0 if not errors else 3


# ---------------------------------------------------------------------------
# Subcommand: platforms
# ---------------------------------------------------------------------------


def cmd_platforms(args: argparse.Namespace) -> int:
    """List registered platforms and their formats."""
    out = []
    for cfg in all_platforms():
        out.append({
            "platform_id": cfg.platform_id,
            "display_name": cfg.display_name,
            "rotation_philosophy": cfg.rotation_philosophy,
            "supports_multi_slide": cfg.supports_multi_slide,
            "max_slides": cfg.max_slides,
            "formats": [
                {
                    "name": f.name,
                    "aspect_ratio": f.aspect_ratio,
                    "width": f.width,
                    "height": f.height,
                    "is_primary": f.is_primary,
                }
                for f in cfg.output_formats
            ],
        })
    emit({"platforms": out})
    return 0


# ---------------------------------------------------------------------------
# Subcommand: path-check
# ---------------------------------------------------------------------------


def cmd_path_check(args: argparse.Namespace) -> int:
    """Check if the proposed manifest path looks like a sensible place to
    keep image history. Returns a structured response the skill can act on.
    """
    path = Path(args.manifest).resolve()
    suspicious, reason = is_suspicious_location(path)
    emit({
        "status": "ok",
        "manifest_path": str(path),
        "suspicious": suspicious,
        "reason": reason,
        "exists": path.exists(),
    })
    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="engine.py",
        description="Content Image Suite - Visual Engine CLI",
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_rotate = sub.add_parser("rotate", help="Run rotation engine for a platform")
    p_rotate.add_argument("--manifest", required=True)
    p_rotate.add_argument("--platform", required=True)
    p_rotate.add_argument("--post-type", default=None)
    p_rotate.add_argument("--locked-style", default=None)
    p_rotate.add_argument("--locked-palette", default=None)
    p_rotate.set_defaults(func=cmd_rotate)

    p_shared = sub.add_parser("shared-identity",
                              help="Compute shared style+palette across platforms")
    p_shared.add_argument("--manifest", required=True)
    p_shared.add_argument("--platforms", required=True,
                          help="Comma-separated platform IDs (e.g. medium,linkedin,twitter)")
    p_shared.add_argument("--post-type", default=None)
    p_shared.set_defaults(func=cmd_shared_identity)

    p_build = sub.add_parser("build-prompt", help="Build a Gemini prompt")
    p_build.add_argument("--platform", required=True)
    p_build.add_argument("--format", required=True,
                         help="Output format name (e.g. hero, carousel_slide)")
    p_build.add_argument("--style", required=True, choices=ALL_STYLES)
    p_build.add_argument("--palette", required=True, choices=ALL_PALETTES)
    p_build.add_argument("--composition", required=True, choices=ALL_COMPOSITIONS)
    p_build.add_argument("--subject", required=True)
    p_build.add_argument("--lighting", default=None)
    p_build.add_argument("--negatives", default=None)
    p_build.add_argument(
        "--protagonist-mode", default="auto",
        choices=["auto", "named", "generic", "none"],
        help="Face treatment mode. 'named' = clear face for first-person/profiled "
             "posts. 'generic' = face can be obscured. 'none' = no human figure. "
             "'auto' (default) = heuristic detection from the subject string.",
    )
    p_build.add_argument(
        "--text-mode", default="block",
        choices=["block", "allow"],
        help="Whether rendered text is expected. 'block' (default) activates "
             "label-risk detection and anti-text negatives. 'allow' is used by "
             "the infographic skill — text in the subject becomes the rendered "
             "content. Pair with --provider openai-gpt-image on generate.",
    )
    p_build.set_defaults(func=cmd_build_prompt)

    p_gen = sub.add_parser("generate", help="Generate an image via fal.ai or OpenAI")
    p_gen.add_argument("--prompt", required=True)
    p_gen.add_argument("--aspect", required=True)
    p_gen.add_argument("--output", required=True)
    p_gen.add_argument("--timeout", type=int, default=180)
    p_gen.add_argument("--no-retry", action="store_true")
    p_gen.add_argument(
        "--provider", default="fal-gemini",
        choices=["fal-gemini", "openai-gpt-image"],
        help="Which image-generation backend to use. 'fal-gemini' (default) "
             "for illustrated content via Gemini 3 Pro Image. 'openai-gpt-image' "
             "for text-rendering quality via gpt-image-2 (infographics).",
    )
    p_gen.add_argument(
        "--openai-model", default="gpt-image-2",
        help="OpenAI model id when provider is openai-gpt-image. Default "
             "gpt-image-2 (released April 21, 2026). Other options: "
             "gpt-image-1.5, gpt-image-1, gpt-image-1-mini. Pinned snapshot: "
             "gpt-image-2-2026-04-21.",
    )
    p_gen.add_argument(
        "--quality", default="medium",
        choices=["low", "medium", "high", "auto"],
        help="Quality tier (OpenAI provider only). Higher = slower + more "
             "expensive but better fidelity. Auto lets the model pick.",
    )
    p_gen.add_argument(
        "--output-format", default="png",
        choices=["png", "jpeg", "webp"],
        help="Output image file format (OpenAI provider only). PNG for "
             "lossless (default), JPEG/WebP for smaller files.",
    )
    p_gen.add_argument(
        "--output-compression", type=int, default=0,
        help="Compression level 0-100 for JPEG/WebP outputs. 0 disables. "
             "Ignored for PNG.",
    )
    p_gen.add_argument(
        "--width", type=int, default=0,
        help="Optional width hint in pixels. OpenAI: validated against "
             "gpt-image-2 constraints (multiple of 16, max edge 3840). "
             "Use with --height to override aspect-based sizing.",
    )
    p_gen.add_argument(
        "--height", type=int, default=0,
        help="Optional height hint in pixels (see --width).",
    )
    p_gen.add_argument(
        "--text-mode", default="block",
        choices=["block", "allow"],
        help="Whether rendered text is expected. 'block' (default) flags any "
             "detected text as a failure. 'allow' (infographic skill) treats "
             "text as expected and reports it informationally.",
    )
    p_gen.add_argument(
        "--overwrite", action="store_true",
        help="Regenerate even if the output file already exists. "
             "Without this flag, an existing image causes exit code 4.",
    )
    p_gen.add_argument(
        "--skip-ocr", action="store_true",
        help="Skip post-generation OCR text detection (useful when tesseract "
             "is slow or unwanted).",
    )
    p_gen.add_argument(
        "--quality-gate", default="off",
        choices=["off", "cheap", "strict"],
        help="Post-generation vision-model quality check. 'cheap' (one vision "
             "call) catches face/composition/palette/thumbnail defects. "
             "'strict' adds a prompt-vs-image fidelity comparison. Requires "
             "either ANTHROPIC_API_KEY (Haiku) or OPENAI_API_KEY (gpt-4o-mini). "
             "Off by default.",
    )
    p_gen.add_argument(
        "--quality-provider", default="auto",
        choices=["auto", "anthropic", "openai"],
        help="Which vision API powers the quality gate. 'auto' (default) "
             "prefers Anthropic if its key is set, otherwise OpenAI.",
    )
    p_gen.add_argument(
        "--quality-model", default="",
        help="Override the vision model id. Defaults: Anthropic "
             "claude-haiku-4-5-20251001, OpenAI gpt-4o-mini. Can also be set "
             "via ANTHROPIC_QUALITY_MODEL or OPENAI_QUALITY_MODEL.",
    )
    p_gen.add_argument(
        "--quality-max-retries", type=int, default=2,
        help="If the quality gate flags the image, regenerate up to this many "
             "times before giving up. Default 2. Set to 0 to disable retries.",
    )
    p_gen.add_argument(
        "--quality-axis-floor", type=int, default=6,
        help="Minimum per-axis score (0-10) for the gate to consider an image "
             "passable. Default 6.",
    )
    p_gen.add_argument(
        "--quality-palette-hint", default="",
        help="Optional free-text palette description passed to the gate so it "
             "can verify palette adherence ('bone white, rust orange, ...').",
    )
    p_gen.add_argument(
        "--quality-style-hint", default="",
        help="Optional style label passed to the gate as a prior for what "
             "'good composition' looks like in this image.",
    )
    p_gen.set_defaults(func=cmd_generate)

    p_plat = sub.add_parser("platforms", help="List registered platforms")
    p_plat.set_defaults(func=cmd_platforms)

    p_pc = sub.add_parser("path-check",
                          help="Check if a manifest path looks like a sensible location")
    p_pc.add_argument("--manifest", required=True)
    p_pc.set_defaults(func=cmd_path_check)

    # ----- manifest subcommands -----
    p_man = sub.add_parser("manifest", help="Manifest operations")
    p_man_sub = p_man.add_subparsers(dest="manifest_cmd", required=True)

    p_get = p_man_sub.add_parser("get", help="Read manifest contents")
    p_get.add_argument("--manifest", required=True)
    p_get.add_argument("--summary", action="store_true")
    p_get.set_defaults(func=cmd_manifest_get)

    p_find = p_man_sub.add_parser("find", help="Find a content piece by slug/title")
    p_find.add_argument("--manifest", required=True)
    p_find.add_argument("--title", default=None)
    p_find.add_argument("--slug", default=None)
    p_find.add_argument("--threshold", type=float, default=0.80)
    p_find.set_defaults(func=cmd_manifest_find)

    p_up = p_man_sub.add_parser("upsert", help="Insert or update a content piece")
    p_up.add_argument("--manifest", required=True)
    p_up.add_argument("--title", required=True)
    p_up.add_argument("--slug", default=None)
    p_up.add_argument("--style", required=True)
    p_up.add_argument("--palette", required=True)
    p_up.add_argument("--themes", default="")
    p_up.add_argument("--date", default=None)
    p_up.add_argument("--content-id", default=None)
    p_up.set_defaults(func=cmd_manifest_upsert)

    p_addo = p_man_sub.add_parser("add-output", help="Add a platform output to a content piece")
    p_addo.add_argument("--manifest", required=True)
    p_addo.add_argument("--content-id", default=None)
    p_addo.add_argument("--slug", default=None)
    p_addo.add_argument("--platform", required=True)
    p_addo.add_argument("--format", required=True)
    p_addo.add_argument("--compositions", required=True,
                        help="key=value pairs separated by ||| (e.g. hero=centered-subject|||inline_1=split-frame)")
    p_addo.add_argument("--prompts", required=True,
                        help="key=value pairs separated by |||")
    p_addo.add_argument("--image-paths", default="")
    p_addo.add_argument("--notes", default="")
    p_addo.add_argument("--date", default=None)
    p_addo.set_defaults(func=cmd_manifest_add_output)

    p_val = p_man_sub.add_parser("validate", help="Validate a manifest")
    p_val.add_argument("--manifest", required=True)
    p_val.set_defaults(func=cmd_manifest_validate)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
