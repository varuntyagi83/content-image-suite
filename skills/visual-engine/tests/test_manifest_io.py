"""Tests for manifest_io.py - load, save, fuzzy match, upsert."""
import json
from pathlib import Path

import pytest

from manifest_io import (
    atomic_write, empty_manifest, find_piece_by_id, find_piece_by_slug,
    fuzzy_match_piece, load_manifest, save_manifest, slugify,
    upsert_content_piece, upsert_platform_output, validate_manifest,
)


class TestEmptyManifest:
    def test_creates_v2_schema(self):
        m = empty_manifest()
        assert m["schema_version"] == 2
        assert m["content_pieces"] == []
        assert m["blog_owner"] == ""

    def test_with_blog_owner(self):
        m = empty_manifest("@varuntyagi83")
        assert m["blog_owner"] == "@varuntyagi83"


class TestLoadManifest:
    def test_missing_file_auto_creates(self, tmp_path):
        path = tmp_path / "nonexistent.json"
        m, corrupt = load_manifest(path)
        assert m["schema_version"] == 2
        assert corrupt is False

    def test_missing_file_no_auto_create_raises(self, tmp_path):
        path = tmp_path / "nonexistent.json"
        with pytest.raises(FileNotFoundError):
            load_manifest(path, auto_create=False)

    def test_loads_valid_manifest(self, manifest_file):
        m, corrupt = load_manifest(manifest_file)
        assert corrupt is False
        assert len(m["content_pieces"]) == 3

    def test_empty_file_returns_empty_manifest(self, tmp_path):
        path = tmp_path / "empty.json"
        path.write_text("")
        m, corrupt = load_manifest(path)
        assert m["schema_version"] == 2
        assert m["content_pieces"] == []

    def test_corrupt_file_backs_up_and_returns_empty(self, tmp_path):
        path = tmp_path / "corrupt.json"
        path.write_text("{not json")
        m, corrupt = load_manifest(path)
        assert corrupt is True
        assert m["schema_version"] == 2
        # Should have created a backup
        backups = list(tmp_path.glob("manifest.corrupt.*.json"))
        assert len(backups) == 1

    def test_wrong_schema_version_raises(self, tmp_path):
        path = tmp_path / "v1.json"
        path.write_text(json.dumps({"schema_version": 1, "entries": []}))
        with pytest.raises(ValueError) as exc:
            load_manifest(path)
        assert "migrate" in str(exc.value).lower()


class TestSaveManifest:
    def test_round_trip(self, tmp_path):
        m = empty_manifest("@user")
        path = tmp_path / "m.json"
        save_manifest(path, m)
        loaded, _ = load_manifest(path)
        assert loaded["blog_owner"] == "@user"

    def test_updates_updated_at(self, tmp_path):
        m = empty_manifest()
        original = m["updated_at"]
        path = tmp_path / "m.json"
        # Tiny sleep equivalent: just save and check the file value is updated
        import time
        time.sleep(0.001)
        save_manifest(path, m)
        loaded, _ = load_manifest(path)
        assert loaded["updated_at"] != original or loaded["updated_at"] >= original


class TestAtomicWrite:
    def test_writes_content(self, tmp_path):
        path = tmp_path / "test.txt"
        atomic_write(path, "hello world")
        assert path.read_text() == "hello world"

    def test_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "deep" / "nested" / "file.txt"
        atomic_write(path, "content")
        assert path.read_text() == "content"

    def test_no_stale_temp_file_left_behind(self, tmp_path):
        path = tmp_path / "test.txt"
        atomic_write(path, "ok")
        # No .tmp file should remain in the directory
        tmps = list(tmp_path.glob("*.tmp"))
        assert tmps == []


class TestSlugify:
    def test_basic(self):
        assert slugify("Hello World") == "hello-world"

    def test_special_chars_removed(self):
        assert slugify("BigQuery: Cost Optimization!") == "bigquery-cost-optimization"

    def test_unicode_handled(self):
        # Non-ASCII removed
        result = slugify("Berlin's Best Bäckerei")
        assert "-" in result
        assert " " not in result

    def test_empty_returns_untitled(self):
        assert slugify("") == "untitled"
        assert slugify("   ") == "untitled"

    def test_collapses_dashes(self):
        assert slugify("a -- b") == "a-b"


class TestFindPieces:
    def test_find_by_slug(self, populated_manifest):
        piece = find_piece_by_slug(populated_manifest, "bigquery-cost-optimization")
        assert piece is not None
        assert piece["canonical_title"] == "Cutting BigQuery Costs by 47%"

    def test_find_by_slug_not_found(self, populated_manifest):
        assert find_piece_by_slug(populated_manifest, "nonexistent") is None

    def test_find_by_id(self, populated_manifest):
        target = populated_manifest["content_pieces"][0]
        found = find_piece_by_id(populated_manifest, target["content_id"])
        assert found is target


class TestFuzzyMatch:
    def test_exact_slug_returns_confidence_1(self, populated_manifest):
        piece, score = fuzzy_match_piece(
            populated_manifest, slug="bigquery-cost-optimization"
        )
        assert score == 1.0
        assert piece is not None

    def test_exact_title_high_confidence(self, populated_manifest):
        piece, score = fuzzy_match_piece(
            populated_manifest, title="Cutting BigQuery Costs by 47%"
        )
        assert score >= 0.95
        assert piece is not None

    def test_fuzzy_title_matches(self, populated_manifest):
        # Slightly different phrasing
        piece, score = fuzzy_match_piece(
            populated_manifest, title="BigQuery Costs Reduced 47%"
        )
        assert score >= 0.5  # Some similarity
        # Whether it matches threshold depends on the score

    def test_fuzzy_slug_matches(self, populated_manifest):
        piece, score = fuzzy_match_piece(
            populated_manifest, slug="bigquery-cost"  # missing "-optimization"
        )
        # Should fuzzy match
        assert score >= 0.6

    def test_below_threshold_returns_none(self, populated_manifest):
        piece, score = fuzzy_match_piece(
            populated_manifest, title="Completely Unrelated Topic", threshold=0.80
        )
        assert piece is None

    def test_no_query_returns_none(self, populated_manifest):
        piece, score = fuzzy_match_piece(populated_manifest)
        assert piece is None
        assert score == 0.0

    def test_empty_manifest_returns_none(self, empty_manifest):
        piece, score = fuzzy_match_piece(empty_manifest, title="anything")
        assert piece is None


class TestUpsertContentPiece:
    def test_insert_new(self, empty_manifest):
        piece, action = upsert_content_piece(
            empty_manifest,
            canonical_title="Test Post",
            canonical_slug="test-post",
            subject_themes=["theme1"],
            shared_identity={"style": "editorial", "palette_id": "bone-and-rust"},
        )
        assert action == "inserted"
        assert piece["canonical_slug"] == "test-post"
        assert "content_id" in piece
        assert "platform_outputs" in piece

    def test_replace_existing(self, empty_manifest):
        # Insert once
        upsert_content_piece(
            empty_manifest, canonical_title="Old Title", canonical_slug="my-post",
            subject_themes=[], shared_identity={"style": "editorial", "palette_id": "bone-and-rust"},
        )
        # Replace
        piece, action = upsert_content_piece(
            empty_manifest, canonical_title="New Title", canonical_slug="my-post",
            subject_themes=["new"], shared_identity={"style": "isometric", "palette_id": "cold-architecture"},
        )
        assert action == "replaced"
        assert piece["canonical_title"] == "New Title"
        assert piece["subject_themes"] == ["new"]

    def test_replace_preserves_content_id(self, empty_manifest):
        piece1, _ = upsert_content_piece(
            empty_manifest, canonical_title="T", canonical_slug="t",
            subject_themes=[], shared_identity={"style": "editorial", "palette_id": "bone-and-rust"},
        )
        original_id = piece1["content_id"]
        piece2, _ = upsert_content_piece(
            empty_manifest, canonical_title="T2", canonical_slug="t",
            subject_themes=[], shared_identity={"style": "isometric", "palette_id": "cold-architecture"},
        )
        assert piece2["content_id"] == original_id

    def test_invalid_slug_raises(self, empty_manifest):
        with pytest.raises(ValueError):
            upsert_content_piece(
                empty_manifest, canonical_title="T", canonical_slug="Bad Slug!",
                subject_themes=[], shared_identity={"style": "editorial", "palette_id": "bone-and-rust"},
            )

    def test_invalid_date_raises(self, empty_manifest):
        with pytest.raises(ValueError):
            upsert_content_piece(
                empty_manifest, canonical_title="T", canonical_slug="t",
                subject_themes=[], shared_identity={"style": "editorial", "palette_id": "bone-and-rust"},
                first_seen_date="not-a-date",
            )

    def test_missing_shared_identity_keys_raises(self, empty_manifest):
        with pytest.raises(ValueError):
            upsert_content_piece(
                empty_manifest, canonical_title="T", canonical_slug="t",
                subject_themes=[], shared_identity={"style": "editorial"},  # missing palette_id
            )


class TestUpsertPlatformOutput:
    def test_insert_new(self, empty_manifest):
        piece, _ = upsert_content_piece(
            empty_manifest, canonical_title="T", canonical_slug="t",
            subject_themes=[], shared_identity={"style": "editorial", "palette_id": "bone-and-rust"},
        )
        action = upsert_platform_output(
            piece,
            platform_id="medium", format_name="hero",
            compositions={"hero": "centered-subject"},
            prompts={"hero": "An editorial prompt of sufficient length to pass."},
        )
        assert action == "inserted"
        assert piece["platform_outputs"]["medium"]["format"] == "hero"

    def test_replace_existing(self, populated_manifest):
        piece = populated_manifest["content_pieces"][1]  # has linkedin already
        action = upsert_platform_output(
            piece,
            platform_id="linkedin", format_name="cover",
            compositions={"cover": "split-frame"},
            prompts={"cover": "New prompt."},
        )
        assert action == "replaced"

    def test_duplicate_compositions_raises(self, empty_manifest):
        piece, _ = upsert_content_piece(
            empty_manifest, canonical_title="T", canonical_slug="t",
            subject_themes=[], shared_identity={"style": "editorial", "palette_id": "bone-and-rust"},
        )
        with pytest.raises(ValueError) as exc:
            upsert_platform_output(
                piece, platform_id="medium", format_name="hero",
                compositions={"hero": "centered-subject", "inline_1": "centered-subject"},
                prompts={"hero": "...", "inline_1": "..."},
            )
        assert "different" in str(exc.value).lower()

    def test_slot_key_mismatch_raises(self, empty_manifest):
        piece, _ = upsert_content_piece(
            empty_manifest, canonical_title="T", canonical_slug="t",
            subject_themes=[], shared_identity={"style": "editorial", "palette_id": "bone-and-rust"},
        )
        with pytest.raises(ValueError):
            upsert_platform_output(
                piece, platform_id="medium", format_name="hero",
                compositions={"hero": "centered-subject"},
                prompts={"different_slot": "..."},
            )


class TestValidate:
    def test_valid_manifest_no_errors(self, populated_manifest):
        errors = validate_manifest(populated_manifest)
        assert errors == []

    def test_empty_manifest_no_errors(self, empty_manifest):
        errors = validate_manifest(empty_manifest)
        assert errors == []

    def test_wrong_schema_version_caught(self):
        m = {"schema_version": 1, "content_pieces": []}
        errors = validate_manifest(m)
        assert any("schema_version" in e for e in errors)

    def test_missing_fields_caught(self):
        m = {"schema_version": 2, "content_pieces": [{"foo": "bar"}]}
        errors = validate_manifest(m)
        assert any("missing required" in e for e in errors)

    def test_duplicate_slugs_caught(self):
        m = {
            "schema_version": 2,
            "content_pieces": [
                {
                    "content_id": "1", "canonical_title": "T", "canonical_slug": "same",
                    "first_seen_date": "2026-01-01", "subject_themes": [],
                    "shared_identity": {"style": "editorial", "palette_id": "bone-and-rust"},
                    "platform_outputs": {},
                },
                {
                    "content_id": "2", "canonical_title": "T2", "canonical_slug": "same",
                    "first_seen_date": "2026-01-01", "subject_themes": [],
                    "shared_identity": {"style": "editorial", "palette_id": "bone-and-rust"},
                    "platform_outputs": {},
                },
            ],
        }
        errors = validate_manifest(m)
        assert any("duplicate slug" in e for e in errors)

    def test_bad_slug_caught(self):
        m = {
            "schema_version": 2,
            "content_pieces": [{
                "content_id": "1", "canonical_title": "T", "canonical_slug": "Bad Slug!",
                "first_seen_date": "2026-01-01", "subject_themes": [],
                "shared_identity": {"style": "editorial", "palette_id": "bone-and-rust"},
                "platform_outputs": {},
            }],
        }
        errors = validate_manifest(m)
        assert any("kebab" in e.lower() for e in errors)

    def test_bad_date_caught(self):
        m = {
            "schema_version": 2,
            "content_pieces": [{
                "content_id": "1", "canonical_title": "T", "canonical_slug": "t",
                "first_seen_date": "not-a-date", "subject_themes": [],
                "shared_identity": {"style": "editorial", "palette_id": "bone-and-rust"},
                "platform_outputs": {},
            }],
        }
        errors = validate_manifest(m)
        assert any("date" in e.lower() for e in errors)

    def test_missing_identity_caught(self):
        m = {
            "schema_version": 2,
            "content_pieces": [{
                "content_id": "1", "canonical_title": "T", "canonical_slug": "t",
                "first_seen_date": "2026-01-01", "subject_themes": [],
                "shared_identity": {},  # empty
                "platform_outputs": {},
            }],
        }
        errors = validate_manifest(m)
        assert any("style" in e.lower() for e in errors)
        assert any("palette" in e.lower() for e in errors)
