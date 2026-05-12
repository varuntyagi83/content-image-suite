"""Tests for migrate_v1_to_v2.py."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from migrate_v1_to_v2 import migrate_entry, migrate_manifest


def make_v1_entry(**overrides):
    base = {
        "id": "post-1",
        "post_slug": "my-post",
        "post_title": "My Post",
        "post_date": "2026-04-15",
        "post_url": "https://medium.com/@user/my-post",
        "style": "editorial",
        "palette_id": "bone-and-rust",
        "compositions": {"hero": "centered-subject"},
        "subject_themes": ["theme1", "theme2"],
        "prompts": {"hero": "An old prompt"},
        "generated_image_paths": {"hero": "/tmp/hero.png"},
        "notes": "",
    }
    base.update(overrides)
    return base


class TestMigrateEntry:
    def test_basic_migration(self):
        v1 = make_v1_entry()
        v2 = migrate_entry(v1)
        assert v2["canonical_title"] == "My Post"
        assert v2["canonical_slug"] == "my-post"
        assert v2["first_seen_date"] == "2026-04-15"
        assert v2["shared_identity"] == {"style": "editorial", "palette_id": "bone-and-rust"}
        assert v2["content_id"] == "post-1"

    def test_medium_output_populated(self):
        v1 = make_v1_entry()
        v2 = migrate_entry(v1)
        medium = v2["platform_outputs"]["medium"]
        assert medium["format"] == "hero"
        assert medium["compositions"] == {"hero": "centered-subject"}
        assert medium["prompts"] == {"hero": "An old prompt"}

    def test_other_platforms_null(self):
        v2 = migrate_entry(make_v1_entry())
        for pid in ["linkedin", "twitter", "instagram", "meta"]:
            assert v2["platform_outputs"][pid] is None

    def test_missing_id_generates_uuid(self):
        v1 = make_v1_entry()
        del v1["id"]
        v2 = migrate_entry(v1)
        assert len(v2["content_id"]) >= 8  # UUID

    def test_missing_style_defaults_to_editorial(self):
        v1 = make_v1_entry()
        del v1["style"]
        v2 = migrate_entry(v1)
        assert v2["shared_identity"]["style"] == "editorial"

    def test_themes_preserved(self):
        v1 = make_v1_entry(subject_themes=["a", "b", "c"])
        v2 = migrate_entry(v1)
        assert v2["subject_themes"] == ["a", "b", "c"]

    def test_post_url_carried_forward(self):
        v1 = make_v1_entry(post_url="https://x.com/post")
        v2 = migrate_entry(v1)
        assert v2.get("post_url") == "https://x.com/post"


class TestMigrateManifest:
    def test_v1_to_v2_basic(self):
        v1 = {
            "schema_version": 1,
            "blog_owner": "@user",
            "entries": [make_v1_entry()],
        }
        v2 = migrate_manifest(v1)
        assert v2["schema_version"] == 2
        assert v2["blog_owner"] == "@user"
        assert len(v2["content_pieces"]) == 1
        assert v2.get("_migrated_from_v1") is True

    def test_already_v2_returned_unchanged(self):
        v2_input = {
            "schema_version": 2, "blog_owner": "@user",
            "content_pieces": [],
        }
        result = migrate_manifest(v2_input)
        assert result is v2_input

    def test_unknown_version_raises(self):
        bad = {"schema_version": 99, "entries": []}
        with pytest.raises(ValueError):
            migrate_manifest(bad)

    def test_pieces_sorted_descending(self):
        v1 = {
            "schema_version": 1,
            "entries": [
                make_v1_entry(post_slug="a", id="a", post_date="2026-01-01"),
                make_v1_entry(post_slug="b", id="b", post_date="2026-05-01"),
                make_v1_entry(post_slug="c", id="c", post_date="2026-03-01"),
            ],
        }
        v2 = migrate_manifest(v1)
        dates = [p["first_seen_date"] for p in v2["content_pieces"]]
        assert dates == ["2026-05-01", "2026-03-01", "2026-01-01"]

    def test_invalid_entries_skipped(self):
        v1 = {
            "schema_version": 1,
            "entries": [
                make_v1_entry(post_slug="ok"),
                "not a dict",
                None,
            ],
        }
        v2 = migrate_manifest(v1)
        assert len(v2["content_pieces"]) == 1

    def test_empty_entries(self):
        v1 = {"schema_version": 1, "entries": []}
        v2 = migrate_manifest(v1)
        assert v2["content_pieces"] == []


class TestMigrationCLI:
    """Test the script via subprocess."""

    def test_cli_migrates_file_in_place_with_backup(self, tmp_path):
        v1 = {
            "schema_version": 1,
            "blog_owner": "@user",
            "entries": [make_v1_entry()],
        }
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(json.dumps(v1))

        script = Path(__file__).parent.parent / "scripts" / "migrate_v1_to_v2.py"
        result = subprocess.run(
            [sys.executable, str(script), str(manifest_path)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0

        # Verify migrated content
        migrated = json.loads(manifest_path.read_text())
        assert migrated["schema_version"] == 2

        # Verify backup
        backup = manifest_path.with_suffix(".json.v1.backup")
        assert backup.exists()
        backup_data = json.loads(backup.read_text())
        assert backup_data["schema_version"] == 1

    def test_cli_no_backup_flag(self, tmp_path):
        v1 = {"schema_version": 1, "entries": [make_v1_entry()]}
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text(json.dumps(v1))

        script = Path(__file__).parent.parent / "scripts" / "migrate_v1_to_v2.py"
        result = subprocess.run(
            [sys.executable, str(script), str(manifest_path), "--no-backup"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        backup = manifest_path.with_suffix(".json.v1.backup")
        assert not backup.exists()

    def test_cli_output_path(self, tmp_path):
        v1 = {"schema_version": 1, "entries": [make_v1_entry()]}
        manifest_path = tmp_path / "v1.json"
        manifest_path.write_text(json.dumps(v1))
        out_path = tmp_path / "v2.json"

        script = Path(__file__).parent.parent / "scripts" / "migrate_v1_to_v2.py"
        result = subprocess.run(
            [sys.executable, str(script), str(manifest_path),
             "--output", str(out_path)],
            capture_output=True, text=True,
        )
        assert result.returncode == 0
        assert out_path.exists()
        # Original should be unchanged
        original = json.loads(manifest_path.read_text())
        assert original["schema_version"] == 1
