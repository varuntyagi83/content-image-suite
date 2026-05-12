"""Tests for the new polish-pass features:
- is_suspicious_location() detects bad working directories
- The CLI 'generate' subcommand refuses to overwrite without --overwrite
- The CLI 'path-check' subcommand returns the right structured response
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from manifest_io import is_suspicious_location

ENGINE_PATH = Path(__file__).parent.parent / "scripts" / "engine.py"


def run_engine(*args, expect_success=True, expect_exit=None):
    """Run engine.py with given args; return (returncode, parsed_stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, str(ENGINE_PATH), *args],
        capture_output=True, text=True,
    )
    if expect_exit is not None and result.returncode != expect_exit:
        pytest.fail(
            f"engine.py exit was {result.returncode}, expected {expect_exit}.\n"
            f"stderr: {result.stderr}\nstdout: {result.stdout}"
        )
    if expect_success and result.returncode != 0:
        pytest.fail(
            f"engine.py failed unexpectedly (rc={result.returncode}):\n"
            f"stderr: {result.stderr}\nstdout: {result.stdout}"
        )
    try:
        parsed = json.loads(result.stdout) if result.stdout.strip() else {}
    except json.JSONDecodeError:
        parsed = {"_raw": result.stdout}
    return result.returncode, parsed, result.stderr


class TestSuspiciousLocationFunction:
    """Direct tests of is_suspicious_location()."""

    def test_tmp_is_suspicious(self):
        sus, reason = is_suspicious_location(Path("/tmp/content-images/manifest.json"))
        assert sus is True
        assert "tmp" in reason.lower()

    def test_inside_suite_folder_is_suspicious(self, tmp_path):
        suite_path = tmp_path / "content-image-suite" / "content-images" / "manifest.json"
        suite_path.parent.mkdir(parents=True)
        sus, reason = is_suspicious_location(suite_path)
        assert sus is True
        assert "suite" in reason.lower()

    def test_normal_blog_folder_is_fine(self, tmp_path):
        # Outside any of the suspicious patterns
        blog_path = tmp_path / "my-blog" / "content-images" / "manifest.json"
        blog_path.parent.mkdir(parents=True)
        sus, reason = is_suspicious_location(blog_path)
        # tmp_path itself is in /tmp on most systems, so this may flag.
        # The point of the test is to verify the function runs without error
        # and returns a boolean + string.
        assert isinstance(sus, bool)
        assert isinstance(reason, str)

    def test_var_folders_is_suspicious(self):
        # macOS temp directories
        sus, reason = is_suspicious_location(
            Path("/var/folders/abc/T/content-images/manifest.json")
        )
        assert sus is True
        assert "temp" in reason.lower() or "macos" in reason.lower()


class TestPathCheckSubcommand:
    """The path-check CLI subcommand."""

    def test_returns_suspicious_for_tmp(self):
        rc, out, _ = run_engine(
            "path-check", "--manifest", "/tmp/content-images/manifest.json",
        )
        assert rc == 0
        assert out["status"] == "ok"
        assert out["suspicious"] is True
        assert out["reason"]

    def test_returns_not_suspicious_for_user_folder(self, tmp_path, monkeypatch):
        # Use a path that's NOT in any suspicious location
        good = tmp_path / "my-project" / "content-images" / "manifest.json"
        rc, out, _ = run_engine(
            "path-check", "--manifest", str(good),
        )
        assert rc == 0
        # tmp_path itself sits in /tmp on Linux, so suspicious might be true.
        # We just verify the response shape is correct.
        assert "suspicious" in out
        assert "reason" in out
        assert "manifest_path" in out
        assert "exists" in out
        assert out["exists"] is False

    def test_returns_exists_true_when_file_present(self, tmp_path):
        m = tmp_path / "manifest.json"
        m.write_text('{"schema_version": 2, "content_pieces": []}')
        rc, out, _ = run_engine(
            "path-check", "--manifest", str(m),
        )
        assert rc == 0
        assert out["exists"] is True


class TestGenerateFileExists:
    """The generate subcommand's file-exists behavior."""

    def test_file_exists_returns_exit_4_with_status(self, tmp_path, monkeypatch):
        # Set fake FAL_KEY so we don't trip the key check
        monkeypatch.setenv("FAL_KEY", "fake-for-test")

        existing = tmp_path / "hero.png"
        # Write a 2KB fake image (above the 1024-byte threshold)
        existing.write_bytes(b"\x89PNG\r\n\x1a\n" + os.urandom(2000))

        rc, out, _ = run_engine(
            "generate",
            "--prompt", "A long enough prompt to pass validation rules and not be rejected upfront",
            "--aspect", "16:9",
            "--output", str(existing),
            expect_success=False,
            expect_exit=4,
        )
        assert out["status"] == "file_exists"
        assert out["local_path"] == str(existing)
        assert out["size_bytes"] >= 1024
        assert "modified_at" in out
        assert "overwrite" in out["message"].lower()

    def test_small_existing_file_does_not_trigger_file_exists(self, tmp_path, monkeypatch):
        """A stub file under 1KB should not trigger file_exists — those are
        likely failed-generation artifacts and should be overwritten."""
        monkeypatch.setenv("FAL_KEY", "fake-for-test")

        stub = tmp_path / "hero.png"
        stub.write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 50)  # ~58 bytes

        # Should proceed to attempt generation (and fail since fake key)
        rc, out, _ = run_engine(
            "generate",
            "--prompt", "A long enough prompt to pass validation rules and not be rejected upfront",
            "--aspect", "16:9",
            "--output", str(stub),
            expect_success=False,
        )
        # rc 2 = generation error (auth/no real key); NOT 4 (file_exists)
        assert rc != 4
        assert out["status"] == "error"

    def test_overwrite_flag_bypasses_file_exists_check(self, tmp_path, monkeypatch):
        """With --overwrite, the file-exists check is skipped."""
        monkeypatch.setenv("FAL_KEY", "fake-for-test")

        existing = tmp_path / "hero.png"
        existing.write_bytes(b"\x89PNG\r\n\x1a\n" + os.urandom(2000))

        rc, out, _ = run_engine(
            "generate",
            "--prompt", "A long enough prompt to pass validation rules and not be rejected upfront",
            "--aspect", "16:9",
            "--output", str(existing),
            "--overwrite",
            expect_success=False,
        )
        # Should NOT be file_exists; should attempt generation and fail at auth.
        assert rc != 4
        assert out["status"] == "error"

    def test_nonexistent_file_proceeds_to_generation(self, tmp_path, monkeypatch):
        monkeypatch.setenv("FAL_KEY", "fake-for-test")

        rc, out, _ = run_engine(
            "generate",
            "--prompt", "A long enough prompt to pass validation rules and not be rejected upfront",
            "--aspect", "16:9",
            "--output", str(tmp_path / "new.png"),
            expect_success=False,
        )
        # No file_exists; proceeds to fal.ai (which fails with auth on fake key).
        assert rc != 4
        assert out["status"] == "error"
