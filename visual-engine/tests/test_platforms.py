"""Tests for platforms.py - the platform configuration registry."""
import pytest

from platforms import (
    INSTAGRAM, LINKEDIN, MEDIUM, META, TWITTER,
    all_platforms, get_format, get_platform,
)


class TestPlatformRegistry:
    def test_all_six_platforms_registered(self):
        platforms = all_platforms()
        ids = {p.platform_id for p in platforms}
        assert ids == {"medium", "linkedin", "twitter", "instagram", "meta", "infographic"}

    def test_get_platform_by_id(self):
        assert get_platform("medium").platform_id == "medium"
        assert get_platform("linkedin").platform_id == "linkedin"

    def test_get_platform_case_insensitive(self):
        assert get_platform("MEDIUM").platform_id == "medium"
        assert get_platform("Twitter").platform_id == "twitter"

    def test_get_platform_aliases(self):
        assert get_platform("x").platform_id == "twitter"
        assert get_platform("X").platform_id == "twitter"
        assert get_platform("ig").platform_id == "instagram"
        assert get_platform("insta").platform_id == "instagram"
        assert get_platform("facebook").platform_id == "meta"
        assert get_platform("fb").platform_id == "meta"
        assert get_platform("li").platform_id == "linkedin"

    def test_unknown_platform_raises(self):
        with pytest.raises(KeyError):
            get_platform("snapchat")

    def test_unknown_platform_error_lists_known(self):
        with pytest.raises(KeyError) as exc:
            get_platform("snapchat")
        assert "medium" in str(exc.value)


class TestPlatformConfigurations:
    """Verify each platform has its declared properties."""

    def test_medium_aggressive_rotation(self):
        assert MEDIUM.rotation_philosophy == "aggressive"
        assert MEDIUM.style_window == 3
        assert MEDIUM.palette_window == 4

    def test_medium_hero_format(self):
        hero = get_format("medium", "hero")
        assert hero.aspect_ratio == "16:9"
        assert hero.is_primary
        assert hero.width == 1920

    def test_medium_inline_formats_43(self):
        inline_1 = get_format("medium", "inline_1")
        assert inline_1.aspect_ratio == "4:3"

    def test_linkedin_moderate_rotation(self):
        assert LINKEDIN.rotation_philosophy == "moderate"
        assert LINKEDIN.text_overlay_friendly
        assert LINKEDIN.mobile_thumbnail_critical
        assert LINKEDIN.supports_multi_slide
        assert LINKEDIN.max_slides == 10

    def test_linkedin_avoids_collage(self):
        assert "collage" in LINKEDIN.avoided_styles

    def test_linkedin_carousel_slide_format(self):
        slide = get_format("linkedin", "carousel_slide")
        assert slide.aspect_ratio == "1:1"
        assert slide.width == 1080

    def test_linkedin_cover_format(self):
        cover = get_format("linkedin", "cover")
        assert cover.aspect_ratio == "1.91:1"
        assert cover.is_primary

    def test_twitter_light_rotation(self):
        assert TWITTER.rotation_philosophy == "light"
        assert TWITTER.style_window == 1
        assert TWITTER.mobile_thumbnail_critical

    def test_twitter_avoids_cinematic_and_collage(self):
        assert "cinematic" in TWITTER.avoided_styles
        assert "collage" in TWITTER.avoided_styles

    def test_instagram_consistency_rotation(self):
        assert INSTAGRAM.rotation_philosophy == "consistency"
        assert INSTAGRAM.style_window == 0  # no style enforcement
        assert INSTAGRAM.palette_window == 0
        assert INSTAGRAM.consistency_palette_lock_strength > 0

    def test_instagram_avoids_jarring_styles(self):
        assert "neon-tech" in INSTAGRAM.avoided_styles
        assert "retro-print" in INSTAGRAM.avoided_styles

    def test_instagram_formats(self):
        feed = get_format("instagram", "feed")
        assert feed.aspect_ratio == "1:1"
        story = get_format("instagram", "story")
        assert story.aspect_ratio == "9:16"
        assert story.width == 1080
        assert story.height == 1920

    def test_meta_text_overlay_friendly(self):
        assert META.text_overlay_friendly

    def test_meta_event_cover_format(self):
        cover = get_format("meta", "event_cover")
        assert cover.aspect_ratio == "1.91:1"
        assert cover.width == 1920

    def test_all_platforms_have_at_least_one_format(self):
        for p in all_platforms():
            assert len(p.output_formats) >= 1, f"{p.platform_id} has no formats"

    def test_all_platforms_have_exactly_one_primary_format(self):
        for p in all_platforms():
            primaries = [f for f in p.output_formats if f.is_primary]
            assert len(primaries) == 1, f"{p.platform_id} has {len(primaries)} primary formats"


class TestGetFormat:
    def test_known_format(self):
        fmt = get_format("medium", "hero")
        assert fmt.name == "hero"

    def test_unknown_format_raises(self):
        with pytest.raises(KeyError):
            get_format("medium", "story")  # Medium doesn't have stories

    def test_unknown_format_error_lists_available(self):
        with pytest.raises(KeyError) as exc:
            get_format("twitter", "carousel_slide")
        assert "single" in str(exc.value) or "thread_card" in str(exc.value)
