"""Tests for prompt_builder.py - building Gemini prompts."""
import pytest

from prompt_builder import (
    build_prompt, extract_lead_sentence, format_palette,
    load_palette_hex_codes, load_style_template, platform_negatives,
)
from platforms import get_platform


class TestLoadStyleTemplate:
    def test_loads_all_8_styles(self, engine_dir):
        for style in ["editorial", "cinematic", "isometric", "collage",
                      "neon-tech", "hand-drawn", "minimalist", "retro-print"]:
            body = load_style_template(style, engine_dir)
            assert len(body) > 100, f"{style} template is too short"

    def test_missing_style_raises(self, engine_dir):
        with pytest.raises(FileNotFoundError):
            load_style_template("nonexistent-style", engine_dir)


class TestExtractLeadSentence:
    def test_finds_first_quoted_lead(self):
        body = """# Style

Some intro.

## Reference Phrasing for Gemini
Lead with one of:
- "Editorial illustration in the style of a New Yorker cover, painterly..."
- "Mixed media editorial illustration..."

## Other Section
- "Should not be picked"
"""
        assert "Editorial illustration" in extract_lead_sentence(body)

    def test_returns_empty_when_no_section(self):
        body = "No reference phrasing here."
        assert extract_lead_sentence(body) == ""

    def test_handles_each_real_template(self, engine_dir):
        for style in ["editorial", "cinematic", "isometric", "collage",
                      "neon-tech", "hand-drawn", "minimalist", "retro-print"]:
            body = load_style_template(style, engine_dir)
            lead = extract_lead_sentence(body)
            assert lead, f"{style}: no lead sentence found"
            assert len(lead) > 20, f"{style}: lead too short"


class TestLoadPaletteHexCodes:
    def test_loads_electric_dusk(self, engine_dir):
        colors = load_palette_hex_codes("electric-dusk", engine_dir)
        assert len(colors) >= 2  # palettes usually have 3-5 colors
        for name, hex_code in colors:
            assert hex_code.startswith("#")
            assert len(hex_code) in (4, 7)

    def test_loads_each_palette(self, engine_dir):
        from constants import ALL_PALETTES
        for palette_id in ALL_PALETTES:
            colors = load_palette_hex_codes(palette_id, engine_dir)
            assert len(colors) >= 2, f"{palette_id} has too few colors"

    def test_unknown_palette_returns_empty(self, engine_dir):
        colors = load_palette_hex_codes("nonexistent-palette-xyz", engine_dir)
        assert colors == []


class TestFormatPalette:
    def test_formats_with_hex(self):
        colors = [("Cobalt", "#2C3DD7"), ("Coral", "#FF6B7A")]
        result = format_palette(colors)
        assert "#2C3DD7" in result
        assert "cobalt" in result.lower()

    def test_empty_returns_empty(self):
        assert format_palette([]) == ""


class TestPlatformNegatives:
    def test_includes_thumbnail_clause_for_mobile_critical(self):
        twitter = get_platform("twitter")
        negs = platform_negatives(twitter)
        assert "thumbnail" in negs.lower()

    def test_excludes_thumbnail_for_medium(self):
        medium = get_platform("medium")
        negs = platform_negatives(medium)
        assert "thumbnail" not in negs.lower()

    def test_always_includes_baseline_negatives(self):
        for pid in ["medium", "linkedin", "twitter", "instagram", "meta"]:
            negs = platform_negatives(get_platform(pid))
            assert "logo" in negs.lower() or "watermark" in negs.lower()


class TestBuildPromptIntegration:
    def test_basic_medium_hero(self, engine_dir):
        prompt, fmt, _ = build_prompt(
            platform_id="medium", format_name="hero",
            style="editorial", palette_id="bone-and-rust",
            composition="centered-subject",
            subject="A woman at a wooden desk reviewing handwritten invoices",
            engine_dir=engine_dir,
        )
        assert fmt.aspect_ratio == "16:9"
        assert "16:9" in prompt
        assert "woman" in prompt.lower()
        assert "centered" in prompt.lower()
        # Should include hex codes
        assert "#" in prompt

    def test_linkedin_carousel_slide(self, engine_dir):
        prompt, fmt, _ = build_prompt(
            platform_id="linkedin", format_name="carousel_slide",
            style="isometric", palette_id="electric-dusk",
            composition="rule-of-thirds-left",
            subject="A glowing server rack with a fuel gauge",
            engine_dir=engine_dir,
        )
        assert fmt.aspect_ratio == "1:1"
        assert fmt.width == 1080

    def test_twitter_includes_thumbnail_negatives(self, engine_dir):
        prompt, _, _ = build_prompt(
            platform_id="twitter", format_name="single",
            style="minimalist", palette_id="monochrome-noir",
            composition="centered-subject",
            subject="A single chess piece on an empty board",
            engine_dir=engine_dir,
        )
        assert "thumbnail" in prompt.lower()

    def test_instagram_story_aspect(self, engine_dir):
        prompt, fmt, _ = build_prompt(
            platform_id="instagram", format_name="story",
            style="cinematic", palette_id="monochrome-noir",
            composition="negative-space-dominant",
            subject="A single morning coffee on a sunlit table",
            engine_dir=engine_dir,
        )
        assert fmt.aspect_ratio == "9:16"
        assert "9:16" in prompt

    def test_custom_negatives_overrides_default(self, engine_dir):
        prompt, _, _ = build_prompt(
            platform_id="meta", format_name="event_cover",
            style="editorial", palette_id="bone-and-rust",
            composition="rule-of-thirds-left",
            subject="A conference floor",
            engine_dir=engine_dir,
            custom_negatives="No people in foreground. Leave space for text overlay.",
        )
        assert "text overlay" in prompt

    def test_prompt_has_no_double_spaces(self, engine_dir):
        prompt, _, _ = build_prompt(
            platform_id="medium", format_name="hero",
            style="editorial", palette_id="bone-and-rust",
            composition="centered-subject",
            subject="A subject",
            engine_dir=engine_dir,
        )
        assert "  " not in prompt

    def test_prompt_is_substantial_length(self, engine_dir):
        prompt, _, _ = build_prompt(
            platform_id="medium", format_name="hero",
            style="editorial", palette_id="bone-and-rust",
            composition="centered-subject",
            subject="A subject",
            engine_dir=engine_dir,
        )
        # Should be more than 200 chars (full prompt with negatives)
        assert len(prompt) > 200

    def test_invalid_style_raises(self, engine_dir):
        with pytest.raises(FileNotFoundError):
            build_prompt(
                platform_id="medium", format_name="hero",
                style="nonexistent", palette_id="bone-and-rust",
                composition="centered-subject", subject="A subject",
                engine_dir=engine_dir,
            )

    def test_invalid_platform_raises(self, engine_dir):
        with pytest.raises(KeyError):
            build_prompt(
                platform_id="snapchat", format_name="story",
                style="editorial", palette_id="bone-and-rust",
                composition="centered-subject", subject="A subject",
                engine_dir=engine_dir,
            )

    def test_invalid_format_raises(self, engine_dir):
        with pytest.raises(KeyError):
            build_prompt(
                platform_id="medium", format_name="story",  # Medium has no story
                style="editorial", palette_id="bone-and-rust",
                composition="centered-subject", subject="A subject",
                engine_dir=engine_dir,
            )
