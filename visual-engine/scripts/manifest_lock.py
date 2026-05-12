"""
visual_engine.manifest_lock
===========================

Cross-process advisory file locking for the JSON manifest backend.

The atomic_write() helper in manifest_io.py guarantees that a write never
leaves a half-written file on disk. It does not guarantee that two writers
won't both perform read-modify-write against the same content and produce a
last-writer-wins outcome.

For team installs where two teammates may run the same engine against a
shared manifest at the same time, we add fcntl.flock-based locking around
the full read-modify-write cycle. Held only for the duration of the cycle,
released even if the inner operation raises.

POSIX-only (macOS, Linux). On Windows the context manager is a no-op so
the engine remains usable; teams targeting Windows should switch to the
sqlite backend, which uses SQLite's own locking instead.
"""

from __future__ import annotations

import contextlib
import os
import time
from pathlib import Path
from typing import Iterator

try:
    import fcntl
    _HAVE_FCNTL = True
except ImportError:  # pragma: no cover - Windows
    _HAVE_FCNTL = False


DEFAULT_LOCK_TIMEOUT_SECONDS = 30.0
DEFAULT_POLL_INTERVAL_SECONDS = 0.1

_SQLITE_SUFFIXES = (".db", ".sqlite", ".sqlite3")


@contextlib.contextmanager
def for_read_modify_write(
    manifest_path: Path,
    *,
    timeout: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
) -> Iterator[None]:
    """Acquire the right kind of lock for a full read-modify-write cycle.

    - JSON manifests: acquire the sidecar fcntl lock so concurrent writers
      serialise across the load+mutate+save window.
    - SQLite manifests: no-op. SQLite's BEGIN IMMEDIATE inside save_manifest
      already gives transactional isolation; trying to layer a file lock on
      top would deadlock the WAL journal.
    """
    if manifest_path.suffix.lower() in _SQLITE_SUFFIXES:
        yield
        return
    with acquire(manifest_path, timeout=timeout):
        yield


class ManifestLockTimeout(RuntimeError):
    """Raised when the lock could not be acquired within the timeout window."""


def lock_path_for(manifest_path: Path) -> Path:
    """Return the sidecar lockfile path for a manifest."""
    return manifest_path.with_name(manifest_path.name + ".lock")


@contextlib.contextmanager
def acquire(
    manifest_path: Path,
    *,
    timeout: float = DEFAULT_LOCK_TIMEOUT_SECONDS,
    poll_interval: float = DEFAULT_POLL_INTERVAL_SECONDS,
) -> Iterator[None]:
    """Acquire an exclusive lock on a manifest's sidecar lockfile.

    Behaviour:
      - POSIX: uses fcntl.flock with LOCK_EX | LOCK_NB and polls until the lock
        is free or the timeout elapses.
      - Windows: yields immediately (no-op). Use the sqlite backend instead.

    The sidecar lockfile is created on first use and never removed. It is a
    zero-byte marker, safe to leave around.
    """
    if not _HAVE_FCNTL:
        # Windows or other platform without fcntl.
        yield
        return

    lock_path = lock_path_for(manifest_path)
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    fd = os.open(str(lock_path), os.O_RDWR | os.O_CREAT, 0o644)
    try:
        deadline = time.monotonic() + max(0.0, timeout)
        while True:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise ManifestLockTimeout(
                        f"Could not acquire manifest lock within {timeout}s. "
                        f"Lockfile: {lock_path}. Another writer is holding it; "
                        f"if that process has crashed, delete the lockfile to "
                        f"recover."
                    )
                time.sleep(poll_interval)

        try:
            yield
        finally:
            try:
                fcntl.flock(fd, fcntl.LOCK_UN)
            except OSError:
                pass
    finally:
        try:
            os.close(fd)
        except OSError:
            pass
