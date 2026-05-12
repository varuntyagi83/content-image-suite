"""
visual_engine.manifest_io
=========================

Read/write the v2 cross-platform manifest. Schema is structured around
'content_pieces' (one entry per piece of source content, regardless of
how many platforms it's been imaged for).

Key features:
- Atomic writes with backup on corruption
- Cross-session content linking via fuzzy slug/title match
- Per-platform output records nested under each content piece
- Migration path from v1 manifests (delegated to a separate script)
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
import uuid
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any

from constants import SCHEMA_VERSION


# ----------------------------------------------------------------------------
# Schema validation
# ----------------------------------------------------------------------------


REQUIRED_PIECE_FIELDS = {
    "content_id",
    "canonical_title",
    "canonical_slug",
    "first_seen_date",
    "subject_themes",
    "shared_identity",
    "platform_outputs",
}

DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")


# ----------------------------------------------------------------------------
# Empty manifest factory
# ----------------------------------------------------------------------------


def empty_manifest(blog_owner: str = "") -> dict[str, Any]:
    """Construct an empty v2 manifest."""
    now = datetime.now(timezone.utc).isoformat()
    return {
        "schema_version": SCHEMA_VERSION,
        "blog_owner": blog_owner,
        "created_at": now,
        "updated_at": now,
        "content_pieces": [],
    }


# ----------------------------------------------------------------------------
# IO
# ----------------------------------------------------------------------------


def _is_sqlite_backend(path: Path) -> bool:
    return path.suffix.lower() in (".db", ".sqlite", ".sqlite3")


def load_manifest(path: Path, auto_create: bool = True) -> tuple[dict[str, Any], bool]:
    """Load a manifest from disk.

    Dispatches to the sqlite backend when the path suffix is .db/.sqlite/.sqlite3,
    otherwise reads the JSON backend.

    Returns (manifest_dict, was_corrupt_recovered).
    If the file is missing and auto_create is True, returns an empty manifest.
    If the file is corrupt, backs up to manifest.corrupt.<ts>.json and returns empty.
    """
    if _is_sqlite_backend(path):
        from manifest_sqlite import load_manifest as _sqlite_load
        return _sqlite_load(path, auto_create=auto_create)

    if not path.exists():
        if auto_create:
            return empty_manifest(), False
        raise FileNotFoundError(f"Manifest not found: {path}")

    try:
        content = path.read_text(encoding="utf-8").strip()
        if not content:
            return empty_manifest(), False
        data = json.loads(content)
    except (json.JSONDecodeError, OSError) as exc:
        # Back up and start fresh.
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        backup_path = path.with_name(f"manifest.corrupt.{timestamp}.json")
        try:
            shutil.copy2(path, backup_path)
        except OSError:
            pass  # If we can't even copy, proceed anyway
        return empty_manifest(), True

    if not isinstance(data, dict):
        return empty_manifest(), True

    if data.get("schema_version") != SCHEMA_VERSION:
        # Wrong schema; defer to migration script.
        raise ValueError(
            f"Manifest has schema_version {data.get('schema_version')!r}, "
            f"expected {SCHEMA_VERSION}. Run migrate_v1_to_v2.py first."
        )

    if "content_pieces" not in data:
        data["content_pieces"] = []

    return data, False


def atomic_write(path: Path, content: str) -> None:
    """Write `content` to `path` atomically (temp file + fsync + rename)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def save_manifest(path: Path, manifest: dict[str, Any]) -> None:
    """Save the manifest atomically.

    For the JSON backend, atomic_write() handles durability (temp file + fsync
    + rename) so a partial write never lands on disk. Concurrent writers from
    different processes are serialised by the caller wrapping the full
    read-modify-write in `manifest_lock.for_read_modify_write(path)`; the
    engine subcommands do this automatically.

    When the path has a sqlite suffix, dispatches to the sqlite backend which
    uses SQLite's own transactional locking via BEGIN IMMEDIATE.
    """
    if _is_sqlite_backend(path):
        from manifest_sqlite import save_manifest as _sqlite_save
        _sqlite_save(path, manifest)
        return

    manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
    content = json.dumps(manifest, indent=2, ensure_ascii=False)
    atomic_write(path, content)


# ----------------------------------------------------------------------------
# Content piece operations
# ----------------------------------------------------------------------------


def find_piece_by_slug(manifest: dict[str, Any], slug: str) -> dict[str, Any] | None:
    """Find a content piece by exact slug match."""
    if not slug:
        return None
    for piece in manifest.get("content_pieces", []):
        if piece.get("canonical_slug") == slug:
            return piece
    return None


def find_piece_by_id(manifest: dict[str, Any], content_id: str) -> dict[str, Any] | None:
    """Find a content piece by exact content_id match."""
    if not content_id:
        return None
    for piece in manifest.get("content_pieces", []):
        if piece.get("content_id") == content_id:
            return piece
    return None


def fuzzy_match_piece(
    manifest: dict[str, Any],
    title: str | None = None,
    slug: str | None = None,
    threshold: float = 0.80,
) -> tuple[dict[str, Any] | None, float]:
    """Find a piece via fuzzy matching on title and/or slug.

    Used for cross-session linking: the user generates Medium images today,
    comes back days later asking for LinkedIn images for "the same post"
    but expressed slightly differently. We try to find the existing piece.

    Returns (best_match, confidence_score). Score is 0..1; if below threshold,
    returns (None, score).

    Match strategy:
      1. Exact slug match (confidence 1.0)
      2. Exact title match (confidence 0.95)
      3. Fuzzy slug similarity (SequenceMatcher ratio)
      4. Fuzzy title similarity (SequenceMatcher ratio)
    """
    if not title and not slug:
        return (None, 0.0)

    pieces = manifest.get("content_pieces", [])
    if not pieces:
        return (None, 0.0)

    best_piece: dict[str, Any] | None = None
    best_score = 0.0

    # 1. Exact slug match
    if slug:
        for piece in pieces:
            if piece.get("canonical_slug") == slug:
                return (piece, 1.0)

    # 2. Exact title match (case-insensitive)
    if title:
        title_lc = title.lower().strip()
        for piece in pieces:
            ptitle = (piece.get("canonical_title") or "").lower().strip()
            if ptitle == title_lc:
                if best_score < 0.95:
                    best_piece = piece
                    best_score = 0.95

    # 3 & 4. Fuzzy similarity
    for piece in pieces:
        scores: list[float] = []
        if slug:
            pslug = piece.get("canonical_slug") or ""
            if pslug:
                scores.append(SequenceMatcher(None, slug.lower(), pslug.lower()).ratio())
        if title:
            ptitle = piece.get("canonical_title") or ""
            if ptitle:
                scores.append(SequenceMatcher(None, title.lower(), ptitle.lower()).ratio())
        if not scores:
            continue
        # Use max of the available signals.
        score = max(scores)
        if score > best_score:
            best_piece = piece
            best_score = score

    if best_score >= threshold:
        return (best_piece, best_score)
    return (None, best_score)


def slugify(text: str) -> str:
    """Convert any string into a URL-safe kebab-case slug."""
    if not text:
        return "untitled"
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s\-]", "", text)
    text = re.sub(r"[\s\-]+", "-", text).strip("-")
    return text or "untitled"


# Folder name patterns that suggest the working directory is not where
# the user intends to keep their content-image history. These trigger a
# one-time confirmation in the skill workflow.
SUSPICIOUS_LOCATION_PATTERNS = [
    "content-image-suite",        # Inside the suite source folder
    "claude-skills",               # Inside a skills folder
    ".claude",                     # Inside the Claude config dir
    "Downloads",                   # In Downloads folder root
    "tmp",                         # /tmp or temp dirs
    "Desktop",                     # Just on the desktop
]


def is_suspicious_location(path: Path) -> tuple[bool, str]:
    """Check if the manifest path is in a folder that probably isn't where
    the user wants to store content images long-term.

    Returns (is_suspicious, reason). When True, the skill should ask the
    user once whether to redirect.
    """
    # Check the manifest's parent directory chain.
    abs_path = path.resolve()
    parts = abs_path.parts

    # Specifically detect: inside the suite source itself.
    for i, part in enumerate(parts):
        if part == "content-image-suite":
            # If the manifest is INSIDE the suite folder (not just nearby),
            # that's almost certainly accidental.
            return (True, f"Manifest is inside the suite source folder ({part})")

    # Home root: anything directly in $HOME (path looks like $HOME/content-images/...)
    try:
        home = Path.home().resolve()
        relative_to_home = abs_path.relative_to(home)
        # Path like 'content-images/manifest.json' is bad — sits directly in $HOME.
        if len(relative_to_home.parts) <= 2:
            return (True, f"Manifest is directly in your home folder")
    except ValueError:
        # Not under $HOME
        pass

    # /tmp or system temp
    if "/tmp/" in str(abs_path) or str(abs_path).startswith("/tmp"):
        return (True, "Manifest is in /tmp (will be wiped)")
    if "/var/folders/" in str(abs_path):  # macOS temp
        return (True, "Manifest is in macOS temp folders (will be wiped)")

    # Inside Downloads/ root (not a subdirectory)
    try:
        downloads = Path.home() / "Downloads"
        relative_to_downloads = abs_path.relative_to(downloads.resolve())
        # If only 2 levels deep (e.g. Downloads/content-images/manifest.json),
        # that's likely accidental
        if len(relative_to_downloads.parts) <= 2:
            return (True, "Manifest is at the top of your Downloads folder")
    except (ValueError, OSError):
        pass

    return (False, "")


# ----------------------------------------------------------------------------
# Upsert operations
# ----------------------------------------------------------------------------


def upsert_content_piece(
    manifest: dict[str, Any],
    *,
    canonical_title: str,
    canonical_slug: str,
    subject_themes: list[str],
    shared_identity: dict[str, str],
    first_seen_date: str | None = None,
    content_id: str | None = None,
) -> tuple[dict[str, Any], str]:
    """Insert or replace a content piece (without platform outputs).

    Returns (piece, action) where action is 'inserted' or 'replaced'.
    """
    if not first_seen_date:
        first_seen_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    if not DATE_RE.match(first_seen_date):
        raise ValueError(f"first_seen_date must be YYYY-MM-DD (got {first_seen_date!r})")

    if not SLUG_RE.match(canonical_slug):
        raise ValueError(f"canonical_slug must be lowercase kebab-case (got {canonical_slug!r})")

    if "style" not in shared_identity or "palette_id" not in shared_identity:
        raise ValueError("shared_identity must include 'style' and 'palette_id'")

    pieces = manifest.setdefault("content_pieces", [])

    existing = find_piece_by_slug(manifest, canonical_slug)
    if existing:
        # Update in place but preserve content_id and platform_outputs.
        existing["canonical_title"] = canonical_title
        existing["subject_themes"] = list(subject_themes)
        existing["shared_identity"] = dict(shared_identity)
        # Don't overwrite first_seen_date if it already exists.
        existing.setdefault("first_seen_date", first_seen_date)
        return existing, "replaced"

    new_piece = {
        "content_id": content_id or str(uuid.uuid4()),
        "canonical_title": canonical_title,
        "canonical_slug": canonical_slug,
        "first_seen_date": first_seen_date,
        "subject_themes": list(subject_themes),
        "shared_identity": dict(shared_identity),
        "platform_outputs": {},
    }
    pieces.append(new_piece)
    pieces.sort(key=lambda p: str(p.get("first_seen_date") or ""), reverse=True)
    return new_piece, "inserted"


def upsert_platform_output(
    piece: dict[str, Any],
    *,
    platform_id: str,
    format_name: str,
    compositions: dict[str, str],
    prompts: dict[str, str],
    image_paths: dict[str, str] | None = None,
    notes: str = "",
    generated_at: str | None = None,
) -> str:
    """Add or replace a platform output on a content piece.

    Returns 'inserted' or 'replaced'.
    """
    if not generated_at:
        generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    platform_outputs = piece.setdefault("platform_outputs", {})

    action = "replaced" if platform_id in platform_outputs else "inserted"

    # Verify compositions all differ
    comp_values = [v for v in compositions.values() if isinstance(v, str) and v]
    if len(comp_values) != len(set(comp_values)):
        raise ValueError(
            f"All composition slots must use different compositions: {comp_values}"
        )

    # Verify slot keys match between compositions and prompts
    if set(compositions.keys()) != set(prompts.keys()):
        raise ValueError(
            f"compositions and prompts must use the same slot keys; "
            f"got compositions={list(compositions.keys())} prompts={list(prompts.keys())}"
        )

    platform_outputs[platform_id] = {
        "format": format_name,
        "generated_at": generated_at,
        "compositions": dict(compositions),
        "prompts": dict(prompts),
        "image_paths": dict(image_paths or {}),
        "notes": notes,
    }
    return action


# ----------------------------------------------------------------------------
# Validation
# ----------------------------------------------------------------------------


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    """Run schema-level validation. Returns list of error messages (empty=valid)."""
    errors: list[str] = []

    if not isinstance(manifest, dict):
        return ["Manifest root must be a dict."]

    if manifest.get("schema_version") != SCHEMA_VERSION:
        errors.append(f"schema_version must be {SCHEMA_VERSION}.")

    pieces = manifest.get("content_pieces")
    if not isinstance(pieces, list):
        errors.append("content_pieces must be a list.")
        return errors

    seen_slugs: set[str] = set()
    seen_ids: set[str] = set()

    for idx, piece in enumerate(pieces):
        prefix = f"content_pieces[{idx}]"

        if not isinstance(piece, dict):
            errors.append(f"{prefix}: must be an object.")
            continue

        missing = REQUIRED_PIECE_FIELDS - set(piece.keys())
        if missing:
            errors.append(f"{prefix}: missing required fields {sorted(missing)}.")

        slug = piece.get("canonical_slug")
        if isinstance(slug, str):
            if not SLUG_RE.match(slug):
                errors.append(f"{prefix}.canonical_slug: must be kebab-case (got {slug!r}).")
            if slug in seen_slugs:
                errors.append(f"{prefix}.canonical_slug: duplicate slug {slug!r}.")
            seen_slugs.add(slug)

        cid = piece.get("content_id")
        if isinstance(cid, str):
            if cid in seen_ids:
                errors.append(f"{prefix}.content_id: duplicate id {cid!r}.")
            seen_ids.add(cid)

        date = piece.get("first_seen_date")
        if isinstance(date, str) and not DATE_RE.match(date):
            errors.append(f"{prefix}.first_seen_date: must be YYYY-MM-DD (got {date!r}).")

        themes = piece.get("subject_themes")
        if not isinstance(themes, list) or not all(isinstance(t, str) for t in themes):
            errors.append(f"{prefix}.subject_themes: must be a list of strings.")

        identity = piece.get("shared_identity")
        if not isinstance(identity, dict):
            errors.append(f"{prefix}.shared_identity: must be an object.")
        else:
            if not identity.get("style"):
                errors.append(f"{prefix}.shared_identity.style: required.")
            if not identity.get("palette_id"):
                errors.append(f"{prefix}.shared_identity.palette_id: required.")

        outputs = piece.get("platform_outputs")
        if not isinstance(outputs, dict):
            errors.append(f"{prefix}.platform_outputs: must be an object.")
        else:
            for pid, output in outputs.items():
                if not output:  # null is fine (placeholder for future)
                    continue
                if not isinstance(output, dict):
                    errors.append(f"{prefix}.platform_outputs[{pid}]: must be an object or null.")
                    continue
                # Compositions all different
                comps = output.get("compositions") or {}
                if isinstance(comps, dict):
                    vals = [v for v in comps.values() if v]
                    if len(vals) != len(set(vals)):
                        errors.append(
                            f"{prefix}.platform_outputs[{pid}].compositions: "
                            f"slots must use different compositions: {vals}"
                        )

    return errors
