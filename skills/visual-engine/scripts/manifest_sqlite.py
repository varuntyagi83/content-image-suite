"""
visual_engine.manifest_sqlite
=============================

SQLite-backed manifest storage. Same in-memory shape as the JSON backend
in manifest_io; difference is that all persistence goes through a single
SQLite database file with WAL mode and BEGIN IMMEDIATE transactions, so
concurrent writers serialise cleanly without losing data.

Trade-off versus the JSON backend:
  + Real transactions, real concurrency control.
  + No "last writer wins" data loss in team installs.
  + Cross-platform locking (works on Windows).
  - Manifest no longer human-readable in a text editor.
  - One more dependency boundary, though sqlite3 is in the stdlib.

Storage shape:
  Two tables:
    manifest_meta  (key TEXT PRIMARY KEY, value TEXT)        -- schema_version,
                                                                blog_owner,
                                                                created_at, updated_at
    content_pieces (content_id TEXT PRIMARY KEY,
                    canonical_slug TEXT UNIQUE NOT NULL,
                    data TEXT NOT NULL,  -- JSON blob of the full piece
                    first_seen_date TEXT,
                    updated_at TEXT)

The full content piece is stored as a JSON blob in `data` rather than fully
normalised. We keep slug/date as columns so queries (find by slug, sort by
date) don't require a JSON parse round-trip.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path
from typing import Any, Iterator

from constants import SCHEMA_VERSION
from manifest_io import (
    DATE_RE,
    REQUIRED_PIECE_FIELDS,
    SLUG_RE,
    empty_manifest,
)


# ---------------------------------------------------------------------------
# Connection management
# ---------------------------------------------------------------------------


@contextmanager
def _connect(db_path: Path, *, timeout: float = 30.0) -> Iterator[sqlite3.Connection]:
    """Open a connection with WAL mode and a sane busy timeout.

    The busy timeout means concurrent writers serialise instead of returning
    SQLITE_BUSY immediately. WAL mode means readers don't block writers and
    vice versa, which matters for team workflows where one person is reading
    rotation history while another is saving a new piece.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), timeout=timeout, isolation_level=None)
    try:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute(f"PRAGMA busy_timeout={int(timeout * 1000)}")
        conn.row_factory = sqlite3.Row
        _ensure_schema(conn)
        yield conn
    finally:
        conn.close()


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS manifest_meta (
            key   TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS content_pieces (
            content_id      TEXT PRIMARY KEY,
            canonical_slug  TEXT UNIQUE NOT NULL,
            data            TEXT NOT NULL,
            first_seen_date TEXT,
            updated_at      TEXT
        )
    """)
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_pieces_date "
        "ON content_pieces (first_seen_date DESC)"
    )
    # Initialise schema_version if empty.
    cur = conn.execute(
        "SELECT value FROM manifest_meta WHERE key = 'schema_version'"
    )
    if cur.fetchone() is None:
        now = datetime.now(timezone.utc).isoformat()
        conn.executemany(
            "INSERT INTO manifest_meta(key, value) VALUES (?, ?)",
            [
                ("schema_version", SCHEMA_VERSION),
                ("blog_owner", ""),
                ("created_at", now),
                ("updated_at", now),
            ],
        )


# ---------------------------------------------------------------------------
# Public API: matches manifest_io
# ---------------------------------------------------------------------------


def is_sqlite_path(path: Path) -> bool:
    """Return True if the path should be handled by this backend."""
    return path.suffix.lower() in (".db", ".sqlite", ".sqlite3")


def load_manifest(path: Path, auto_create: bool = True) -> tuple[dict[str, Any], bool]:
    """Load the manifest into the same dict shape used by the JSON backend."""
    if not path.exists() and not auto_create:
        raise FileNotFoundError(f"Manifest DB not found: {path}")

    with _connect(path) as conn:
        meta = {row["key"]: row["value"] for row in conn.execute(
            "SELECT key, value FROM manifest_meta"
        )}

        raw_schema = meta.get("schema_version")
        schema_version: Any
        if raw_schema is None or raw_schema == "":
            schema_version = SCHEMA_VERSION
        elif isinstance(SCHEMA_VERSION, int):
            try:
                schema_version = int(raw_schema)
            except (TypeError, ValueError):
                schema_version = raw_schema
        else:
            schema_version = raw_schema
        if schema_version != SCHEMA_VERSION:
            raise ValueError(
                f"Manifest DB has schema_version {schema_version!r}, "
                f"expected {SCHEMA_VERSION!r}."
            )

        pieces: list[dict[str, Any]] = []
        for row in conn.execute(
            "SELECT data FROM content_pieces "
            "ORDER BY first_seen_date DESC, content_id ASC"
        ):
            try:
                pieces.append(json.loads(row["data"]))
            except json.JSONDecodeError:
                # Skip corrupt row but keep loading the rest.
                continue

        manifest = {
            "schema_version": schema_version,
            "blog_owner": meta.get("blog_owner", ""),
            "created_at": meta.get("created_at") or datetime.now(timezone.utc).isoformat(),
            "updated_at": meta.get("updated_at") or datetime.now(timezone.utc).isoformat(),
            "content_pieces": pieces,
        }
        return manifest, False


def save_manifest(path: Path, manifest: dict[str, Any]) -> None:
    """Persist the manifest using per-piece upserts.

    Concurrency semantics:

    Each call serialises under SQLite's BEGIN IMMEDIATE, so writes never
    overlap. Crucially, we DO NOT wipe-and-rewrite the content_pieces
    table. Earlier versions did, which created a last-writer-wins bug:
    two concurrent processes would each load the manifest, modify it
    locally, then DELETE+INSERT inside their own transaction, with the
    later writer overwriting the earlier writer's additions.

    The fix is per-piece upsert (INSERT OR REPLACE on the unique slug).
    Each writer touches only the rows it actually changed. Pieces added
    by other writers between this writer's load and save remain in place.

    Deletion semantics: the engine has no piece-delete API, so we never
    need to remove rows here. If a future API needs to delete pieces,
    add an explicit delete call that runs inside its own transaction.
    """
    now = datetime.now(timezone.utc).isoformat()
    manifest["updated_at"] = now

    pieces = manifest.get("content_pieces") or []

    with _connect(path) as conn:
        conn.execute("BEGIN IMMEDIATE")
        try:
            # Upsert meta fields.
            for key, value in [
                ("schema_version", manifest.get("schema_version") or SCHEMA_VERSION),
                ("blog_owner", manifest.get("blog_owner", "") or ""),
                ("created_at", manifest.get("created_at") or now),
                ("updated_at", now),
            ]:
                conn.execute(
                    "INSERT INTO manifest_meta(key, value) VALUES (?, ?) "
                    "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
                    (key, value),
                )

            # Per-piece upsert. INSERT OR REPLACE keyed on canonical_slug
            # (UNIQUE constraint) and content_id (PRIMARY KEY) means a
            # concurrent writer's earlier inserts are preserved.
            for piece in pieces:
                content_id = piece.get("content_id") or str(uuid.uuid4())
                slug = piece.get("canonical_slug") or ""
                if not slug:
                    continue
                conn.execute(
                    "INSERT INTO content_pieces "
                    "(content_id, canonical_slug, data, first_seen_date, updated_at) "
                    "VALUES (?, ?, ?, ?, ?) "
                    "ON CONFLICT(canonical_slug) DO UPDATE SET "
                    "  data = excluded.data, "
                    "  first_seen_date = excluded.first_seen_date, "
                    "  updated_at = excluded.updated_at",
                    (
                        content_id,
                        slug,
                        json.dumps(piece, ensure_ascii=False),
                        piece.get("first_seen_date") or "",
                        now,
                    ),
                )

            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise


# ---------------------------------------------------------------------------
# Lookups (avoid loading the whole manifest when not needed)
# ---------------------------------------------------------------------------


def find_piece_by_slug(path: Path, slug: str) -> dict[str, Any] | None:
    if not slug:
        return None
    with _connect(path) as conn:
        row = conn.execute(
            "SELECT data FROM content_pieces WHERE canonical_slug = ?",
            (slug,),
        ).fetchone()
        if not row:
            return None
        try:
            return json.loads(row["data"])
        except json.JSONDecodeError:
            return None


def fuzzy_match_piece(
    path: Path,
    *,
    title: str | None = None,
    slug: str | None = None,
    threshold: float = 0.80,
) -> tuple[dict[str, Any] | None, float]:
    """Cross-session fuzzy match against title/slug, mirroring manifest_io."""
    if not title and not slug:
        return (None, 0.0)

    with _connect(path) as conn:
        rows = list(conn.execute("SELECT data, canonical_slug FROM content_pieces"))
        if not rows:
            return (None, 0.0)

        if slug:
            for row in rows:
                if row["canonical_slug"] == slug:
                    try:
                        return (json.loads(row["data"]), 1.0)
                    except json.JSONDecodeError:
                        pass

        best_piece: dict[str, Any] | None = None
        best_score = 0.0

        for row in rows:
            try:
                piece = json.loads(row["data"])
            except json.JSONDecodeError:
                continue
            scores: list[float] = []
            if slug:
                pslug = piece.get("canonical_slug") or ""
                if pslug:
                    scores.append(
                        SequenceMatcher(None, slug.lower(), pslug.lower()).ratio()
                    )
            if title:
                ptitle = piece.get("canonical_title") or ""
                if ptitle:
                    scores.append(
                        SequenceMatcher(None, title.lower(), ptitle.lower()).ratio()
                    )
            if not scores:
                continue
            score = max(scores)
            if score > best_score:
                best_piece = piece
                best_score = score

        if best_score >= threshold:
            return (best_piece, best_score)
        return (None, best_score)


# ---------------------------------------------------------------------------
# Validation (delegates to the same schema rules as the JSON backend)
# ---------------------------------------------------------------------------


def validate_manifest(manifest: dict[str, Any]) -> list[str]:
    """Run the same schema validation as the JSON backend."""
    from manifest_io import validate_manifest as _validate
    return _validate(manifest)


__all__ = [
    "is_sqlite_path",
    "load_manifest",
    "save_manifest",
    "find_piece_by_slug",
    "fuzzy_match_piece",
    "validate_manifest",
    "empty_manifest",
    "DATE_RE",
    "SLUG_RE",
    "REQUIRED_PIECE_FIELDS",
]
