"""Tests for engine.py CLI - all subcommands."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ENGINE_PATH = Path(__file__).parent.parent / "scripts" / "engine.py"


def run_engine(*args, expect_success=True):
    """Run engine.py with given args, return (returncode, parsed_stdout, stderr)."""
    result = subprocess.run(
        [sys.executable, str(ENGINE_PATH), *args],
        capture_output=True, text=True,
    )
    if expect_success and result.returncode != 0:
        pytest.fail(f"engine.py failed (returncode={result.returncode}):\n"
                    f"stderr: {result.stderr}\nstdout: {result.stdout}")
    try:
        parsed = json.loads(result.stdout) if result.stdout.strip() else {}
    except json.JSONDecodeError:
        parsed = {"_raw": result.stdout}
    return result.returncode, parsed, result.stderr


class TestPlatformsSubcommand:
    def test_lists_all_6_platforms(self):
        rc, out, _ = run_engine("platforms")
        assert rc == 0
        assert "platforms" in out
        assert len(out["platforms"]) == 6
        ids = [p["platform_id"] for p in out["platforms"]]
        assert set(ids) == {"medium", "linkedin", "twitter", "instagram", "meta", "infographic"}

    def test_each_platform_has_formats(self):
        _, out, _ = run_engine("platforms")
        for p in out["platforms"]:
            assert len(p["formats"]) >= 1
            primaries = [f for f in p["formats"] if f["is_primary"]]
            assert len(primaries) == 1


class TestRotateSubcommand:
    def test_rotate_empty_manifest(self, tmp_path):
        manifest = tmp_path / "m.json"
        rc, out, _ = run_engine("rotate", "--manifest", str(manifest), "--platform", "medium")
        assert rc == 0
        assert len(out["allowed_styles"]) == 8
        assert out["platform"] == "medium"
        assert out["philosophy"] == "aggressive"

    def test_rotate_with_post_type(self, tmp_path):
        manifest = tmp_path / "m.json"
        _, out, _ = run_engine(
            "rotate", "--manifest", str(manifest),
            "--platform", "medium", "--post-type", "technical",
        )
        assert out["recommended_style"] in ("isometric", "minimalist", "neon-tech")

    def test_rotate_unknown_platform_fails(self, tmp_path):
        manifest = tmp_path / "m.json"
        rc, out, _ = run_engine(
            "rotate", "--manifest", str(manifest), "--platform", "snapchat",
            expect_success=False,
        )
        assert rc != 0
        assert out["status"] == "error"

    def test_rotate_with_locks(self, tmp_path):
        manifest = tmp_path / "m.json"
        _, out, _ = run_engine(
            "rotate", "--manifest", str(manifest), "--platform", "linkedin",
            "--locked-style", "editorial", "--locked-palette", "bone-and-rust",
        )
        assert out["allowed_styles"] == ["editorial"]
        assert out["allowed_palettes"] == ["bone-and-rust"]


class TestSharedIdentitySubcommand:
    def test_basic_intersection(self, tmp_path):
        manifest = tmp_path / "m.json"
        _, out, _ = run_engine(
            "shared-identity", "--manifest", str(manifest),
            "--platforms", "medium,linkedin,twitter",
            "--post-type", "technical",
        )
        assert out["style"]
        assert out["palette"]
        assert "per_platform_rotations" in out
        assert set(out["per_platform_rotations"].keys()) == {"medium", "linkedin", "twitter"}

    def test_empty_platforms_fails(self, tmp_path):
        manifest = tmp_path / "m.json"
        rc, _, _ = run_engine(
            "shared-identity", "--manifest", str(manifest), "--platforms", "",
            expect_success=False,
        )
        assert rc != 0


class TestBuildPromptSubcommand:
    def test_build_medium_hero(self):
        _, out, _ = run_engine(
            "build-prompt", "--platform", "medium", "--format", "hero",
            "--style", "editorial", "--palette", "bone-and-rust",
            "--composition", "centered-subject",
            "--subject", "A photographer in a dark room developing film by red light",
        )
        assert out["status"] == "ok"
        assert out["aspect_ratio"] == "16:9"
        assert "photographer" in out["prompt"].lower()
        # Should have hex codes
        assert "#" in out["prompt"]

    def test_build_invalid_style_fails(self):
        rc, out, _ = run_engine(
            "build-prompt", "--platform", "medium", "--format", "hero",
            "--style", "nonexistent", "--palette", "bone-and-rust",
            "--composition", "centered-subject", "--subject", "A subject",
            expect_success=False,
        )
        assert rc != 0


class TestManifestSubcommands:
    def test_upsert_then_get(self, tmp_path):
        manifest = tmp_path / "m.json"
        rc, out, _ = run_engine(
            "manifest", "upsert", "--manifest", str(manifest),
            "--title", "Test Post", "--slug", "test-post",
            "--style", "editorial", "--palette", "bone-and-rust",
            "--themes", "theme1,theme2",
        )
        assert out["action"] == "inserted"

        _, out, _ = run_engine(
            "manifest", "get", "--manifest", str(manifest), "--summary",
        )
        assert out["total_pieces"] == 1

    def test_upsert_replace_existing(self, tmp_path):
        manifest = tmp_path / "m.json"
        run_engine(
            "manifest", "upsert", "--manifest", str(manifest),
            "--title", "Old", "--slug", "post",
            "--style", "editorial", "--palette", "bone-and-rust",
        )
        _, out, _ = run_engine(
            "manifest", "upsert", "--manifest", str(manifest),
            "--title", "New", "--slug", "post",
            "--style", "isometric", "--palette", "cold-architecture",
        )
        assert out["action"] == "replaced"

    def test_add_output_then_find(self, tmp_path):
        manifest = tmp_path / "m.json"
        run_engine(
            "manifest", "upsert", "--manifest", str(manifest),
            "--title", "Test", "--slug", "test",
            "--style", "editorial", "--palette", "bone-and-rust",
        )
        rc, out, _ = run_engine(
            "manifest", "add-output", "--manifest", str(manifest),
            "--slug", "test", "--platform", "medium", "--format", "hero",
            "--compositions", "hero=centered-subject",
            "--prompts", "hero=A long enough prompt to pass validation",
        )
        assert rc == 0
        assert out["action"] == "inserted"

    def test_find_by_fuzzy(self, tmp_path):
        manifest = tmp_path / "m.json"
        run_engine(
            "manifest", "upsert", "--manifest", str(manifest),
            "--title", "How We Cut BigQuery Costs by 47%",
            "--slug", "bigquery-cost-optimization",
            "--style", "isometric", "--palette", "electric-dusk",
        )

        # Exact slug
        _, out, _ = run_engine(
            "manifest", "find", "--manifest", str(manifest),
            "--slug", "bigquery-cost-optimization",
        )
        assert out["matched"] is True
        assert out["confidence"] == 1.0

        # Fuzzy slug
        _, out, _ = run_engine(
            "manifest", "find", "--manifest", str(manifest),
            "--title", "How we cut BigQuery costs",
        )
        assert out["matched"] is True

        # No match
        _, out, _ = run_engine(
            "manifest", "find", "--manifest", str(manifest),
            "--title", "Something completely different",
        )
        assert out["matched"] is False

    def test_validate_passes_for_clean_manifest(self, tmp_path):
        manifest = tmp_path / "m.json"
        run_engine(
            "manifest", "upsert", "--manifest", str(manifest),
            "--title", "T", "--slug", "t",
            "--style", "editorial", "--palette", "bone-and-rust",
        )
        rc, out, _ = run_engine(
            "manifest", "validate", "--manifest", str(manifest),
        )
        assert rc == 0
        assert out["valid"] is True
