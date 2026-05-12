"""Tests for rotation.py - parameterized rotation engine."""
import pytest

from constants import ALL_PALETTES, ALL_STYLES
from rotation import (
    _established_palette_for_consistency,
    _platform_history,
    compute_rotation,
    compute_shared_identity,
)


class TestPlatformHistoryExtraction:
    def test_empty_manifest_returns_empty(self, empty_manifest):
        assert _platform_history(empty_manifest, "medium") == []

    def test_extracts_only_relevant_platform(self, populated_manifest):
        twitter_hist = _platform_history(populated_manifest, "twitter")
        assert len(twitter_hist) == 1
        assert twitter_hist[0]["style"] == "cinematic"

    def test_filters_null_outputs(self, populated_manifest):
        # 'meta' is null on all pieces
        meta_hist = _platform_history(populated_manifest, "meta")
        assert meta_hist == []

    def test_sorted_descending_by_date(self, populated_manifest):
        medium_hist = _platform_history(populated_manifest, "medium")
        dates = [h["post_date"] for h in medium_hist]
        assert dates == sorted(dates, reverse=True)

    def test_carries_shared_identity_to_history_entry(self, populated_manifest):
        medium_hist = _platform_history(populated_manifest, "medium")
        # Most recent piece uses isometric
        assert medium_hist[0]["style"] == "isometric"
        assert medium_hist[0]["palette_id"] == "electric-dusk"


class TestEmptyHistoryRotation:
    def test_empty_manifest_medium(self, empty_manifest):
        rot = compute_rotation(empty_manifest, "medium")
        # All 8 styles allowed (no exclusions)
        assert len(rot["allowed_styles"]) == 8
        assert len(rot["allowed_palettes"]) == 12
        assert rot["philosophy"] == "aggressive"
        assert rot["recommended_style"]
        assert rot["recommended_palette"]

    def test_empty_manifest_linkedin_excludes_collage(self, empty_manifest):
        rot = compute_rotation(empty_manifest, "linkedin")
        assert "collage" not in rot["allowed_styles"]

    def test_empty_manifest_twitter_excludes_cinematic_collage(self, empty_manifest):
        rot = compute_rotation(empty_manifest, "twitter")
        assert "cinematic" not in rot["allowed_styles"]
        assert "collage" not in rot["allowed_styles"]

    def test_empty_manifest_instagram_excludes_neon_retro(self, empty_manifest):
        rot = compute_rotation(empty_manifest, "instagram")
        assert "neon-tech" not in rot["allowed_styles"]
        assert "retro-print" not in rot["allowed_styles"]

    def test_first_post_note_present(self, empty_manifest):
        rot = compute_rotation(empty_manifest, "medium")
        assert any("First post" in n for n in rot["notes"])

    def test_recommended_style_for_technical_post(self, empty_manifest):
        rot = compute_rotation(empty_manifest, "medium", post_type="technical")
        # Technical post-type prefers isometric, minimalist, neon-tech
        assert rot["recommended_style"] in ("isometric", "minimalist", "neon-tech")


class TestPopulatedHistoryRotation:
    def test_recent_style_excluded_medium(self, populated_manifest):
        # Most recent Medium post uses isometric
        rot = compute_rotation(populated_manifest, "medium")
        assert "isometric" not in rot["allowed_styles"]

    def test_recent_palette_excluded_medium(self, populated_manifest):
        rot = compute_rotation(populated_manifest, "medium")
        assert "electric-dusk" not in rot["allowed_palettes"]

    def test_multiple_recent_styles_excluded_when_window_3(self, populated_manifest):
        rot = compute_rotation(populated_manifest, "medium")
        # Medium history: isometric (newest), editorial, cinematic
        # Window=3 should exclude all three
        for s in ["isometric", "editorial", "cinematic"]:
            assert s not in rot["allowed_styles"], f"{s} should be excluded with window=3"

    def test_old_palette_back_in_rotation(self, populated_manifest):
        rot = compute_rotation(populated_manifest, "medium")
        # If palette window is 4 and we have only 3 medium posts, all 3 are excluded
        # but the other 9 palettes are still allowed.
        assert len(rot["allowed_palettes"]) >= 9

    def test_composition_rotation_per_slot(self, populated_manifest):
        rot = compute_rotation(populated_manifest, "medium")
        hero_allowed = rot["allowed_compositions"]["hero"]
        # Most recent hero used "centered-subject"
        assert "centered-subject" not in hero_allowed

    def test_forbidden_themes_includes_recent(self, populated_manifest):
        rot = compute_rotation(populated_manifest, "medium")
        # Most recent themes are "server racks" and "fuel gauge"
        themes = rot["forbidden_themes"]
        assert "server racks" in themes
        assert "fuel gauge" in themes


class TestLockedStyle:
    def test_locked_style_overrides_window(self, populated_manifest):
        # Lock to isometric even though it's the most recent style
        rot = compute_rotation(populated_manifest, "medium", locked_style="isometric")
        assert rot["allowed_styles"] == ["isometric"]
        assert rot["recommended_style"] == "isometric"

    def test_locked_palette_overrides_window(self, populated_manifest):
        rot = compute_rotation(populated_manifest, "medium", locked_palette="electric-dusk")
        assert rot["allowed_palettes"] == ["electric-dusk"]


class TestInstagramConsistencyMode:
    def test_consistency_locks_after_3_posts(self, instagram_consistency_manifest):
        rot = compute_rotation(instagram_consistency_manifest, "instagram")
        # All 4 IG posts use cinematic + monochrome-noir
        assert rot["consistency_locked"] is True
        assert rot["recommended_style"] == "cinematic"
        assert rot["recommended_palette"] == "monochrome-noir"

    def test_consistency_mode_notes(self, instagram_consistency_manifest):
        rot = compute_rotation(instagram_consistency_manifest, "instagram")
        assert any("consistency mode" in n.lower() for n in rot["notes"])

    def test_consistency_only_for_instagram(self, populated_manifest):
        # Other platforms should never enter consistency mode
        for pid in ["medium", "linkedin", "twitter", "meta"]:
            rot = compute_rotation(populated_manifest, pid)
            assert rot["consistency_locked"] is False

    def test_consistency_no_lock_under_3_posts(self):
        # Only 2 IG posts: not enough history
        manifest = {
            "schema_version": 2,
            "content_pieces": [
                {
                    "content_id": "1", "canonical_title": "T1", "canonical_slug": "t1",
                    "first_seen_date": "2026-04-20", "subject_themes": [],
                    "shared_identity": {"style": "cinematic", "palette_id": "monochrome-noir"},
                    "platform_outputs": {
                        "instagram": {
                            "format": "feed", "generated_at": "2026-04-20",
                            "compositions": {"feed": "centered-subject"},
                            "prompts": {"feed": "..."}, "image_paths": {}, "notes": "",
                        },
                    },
                },
                {
                    "content_id": "2", "canonical_title": "T2", "canonical_slug": "t2",
                    "first_seen_date": "2026-04-19", "subject_themes": [],
                    "shared_identity": {"style": "cinematic", "palette_id": "monochrome-noir"},
                    "platform_outputs": {
                        "instagram": {
                            "format": "feed", "generated_at": "2026-04-19",
                            "compositions": {"feed": "rule-of-thirds-left"},
                            "prompts": {"feed": "..."}, "image_paths": {}, "notes": "",
                        },
                    },
                },
            ],
        }
        rot = compute_rotation(manifest, "instagram")
        assert rot["consistency_locked"] is False

    def test_established_palette_picks_mode(self):
        history = [
            {"style": "cinematic", "palette_id": "monochrome-noir"},
            {"style": "cinematic", "palette_id": "monochrome-noir"},
            {"style": "cinematic", "palette_id": "monochrome-noir"},
            {"style": "editorial", "palette_id": "bone-and-rust"},
        ]
        style, palette = _established_palette_for_consistency(history)
        assert style == "cinematic"
        assert palette == "monochrome-noir"

    def test_established_palette_below_confidence_returns_none(self):
        """If no style dominates >40% of recent posts, don't lock."""
        # 4 entries, no style or palette has more than 1 occurrence.
        history = [
            {"style": "cinematic", "palette_id": "monochrome-noir"},
            {"style": "editorial", "palette_id": "bone-and-rust"},
            {"style": "hand-drawn", "palette_id": "paper-and-pencil"},
            {"style": "minimalist", "palette_id": "cold-architecture"},
        ]
        style, palette = _established_palette_for_consistency(history, minimum_confidence=0.40)
        # No style has > 40% (each is 25%), so no lock.
        assert style is None
        assert palette is None

    def test_established_palette_tie_prefers_more_recent(self):
        """On a tie in counts, the more recent entry wins."""
        # history[0] is most recent. 2 cinematic + 2 editorial = tie.
        # cinematic appears at index 0 (more recent), editorial at index 2.
        # Expected: cinematic wins.
        history = [
            {"style": "cinematic", "palette_id": "monochrome-noir"},
            {"style": "cinematic", "palette_id": "monochrome-noir"},
            {"style": "editorial", "palette_id": "bone-and-rust"},
            {"style": "editorial", "palette_id": "bone-and-rust"},
        ]
        style, palette = _established_palette_for_consistency(history)
        assert style == "cinematic"
        assert palette == "monochrome-noir"


class TestSeriesDetection:
    def test_series_locks_identity(self):
        manifest = {
            "schema_version": 2,
            "content_pieces": [
                {
                    "content_id": "1", "canonical_title": "T1", "canonical_slug": "t1",
                    "first_seen_date": "2026-05-01", "subject_themes": [],
                    "shared_identity": {"style": "cinematic", "palette_id": "velvet-financial"},
                    "platform_outputs": {
                        "medium": {
                            "format": "hero", "generated_at": "2026-05-01",
                            "compositions": {"hero": "centered-subject"},
                            "prompts": {"hero": "..."}, "image_paths": {},
                            "notes": "series: ai-strategy-deep-dive",
                        },
                    },
                },
            ],
        }
        rot = compute_rotation(manifest, "medium")
        # The series should lock the style+palette even though normally rotation
        # would exclude them.
        assert rot["recommended_style"] == "cinematic"
        assert rot["recommended_palette"] == "velvet-financial"
        assert any("series" in n.lower() for n in rot["notes"])


class TestRotationWindowRelaxation:
    def test_relaxes_when_all_styles_exhausted(self):
        # 8 medium posts using each style once
        pieces = []
        for i, s in enumerate(ALL_STYLES):
            pieces.append({
                "content_id": f"id-{i}",
                "canonical_title": f"Post {i}",
                "canonical_slug": f"post-{i}",
                "first_seen_date": f"2026-04-{20 - i:02d}",
                "subject_themes": [],
                "shared_identity": {"style": s, "palette_id": "bone-and-rust"},
                "platform_outputs": {
                    "medium": {
                        "format": "hero",
                        "generated_at": f"2026-04-{20 - i:02d}",
                        "compositions": {"hero": "centered-subject"},
                        "prompts": {"hero": "..."},
                        "image_paths": {}, "notes": "",
                    },
                },
            })
        manifest = {"schema_version": 2, "content_pieces": pieces}
        # With window=3, the 3 most recent styles are excluded.
        # But there are 8 styles total, so 5 should still be allowed.
        rot = compute_rotation(manifest, "medium")
        assert len(rot["allowed_styles"]) == 5


class TestSharedIdentity:
    def test_intersects_allowed_styles(self, empty_manifest):
        # On empty manifest: LinkedIn excludes collage, Twitter excludes cinematic+collage
        # Intersection of {all minus collage} and {all minus cinematic, collage} = {all minus cinematic, collage}
        result = compute_shared_identity(empty_manifest, ["linkedin", "twitter"])
        assert result["style"] in ALL_STYLES
        assert result["style"] != "collage"
        assert result["style"] != "cinematic"

    def test_picks_for_technical_post(self, empty_manifest):
        result = compute_shared_identity(
            empty_manifest, ["medium", "linkedin", "twitter"], post_type="technical"
        )
        # Technical prefers isometric/minimalist/neon-tech
        assert result["style"] in ("isometric", "minimalist", "neon-tech")

    def test_returns_per_platform_rotations(self, empty_manifest):
        result = compute_shared_identity(empty_manifest, ["medium", "linkedin"])
        assert "medium" in result["per_platform_rotations"]
        assert "linkedin" in result["per_platform_rotations"]

    def test_empty_platforms_raises(self, empty_manifest):
        with pytest.raises(ValueError):
            compute_shared_identity(empty_manifest, [])

    def test_consistency_lock_overrides_intersection(self, instagram_consistency_manifest):
        # If IG is in the mix and has consistency lock to cinematic+monochrome-noir,
        # other platforms should adopt that identity.
        result = compute_shared_identity(
            instagram_consistency_manifest, ["medium", "instagram"]
        )
        assert result["style"] == "cinematic"
        assert result["palette"] == "monochrome-noir"

    def test_single_platform(self, empty_manifest):
        result = compute_shared_identity(empty_manifest, ["medium"])
        assert result["style"] is not None
        assert result["palette"] is not None
