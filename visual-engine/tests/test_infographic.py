"""
Tests for the OpenAI provider and the infographic platform.

These tests focus on:
1. Size validation and aspect-ratio mapping (the openai_provider has its own
   normalization logic since gpt-image-2's constraints differ from fal/Gemini's)
2. Error handling when openai key is missing or the openai package isn't installed
3. The infographic platform's rotation behavior (light philosophy, no
   illustration styles allowed)
4. The text_mode=allow path through build_prompt (bypasses label-risk)

We do NOT make real API calls. The OpenAI client is mocked.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts dir to path so imports resolve
SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))


class TestOpenAIProviderSizeValidation:
    """Test gpt-image-2 size constraint enforcement."""

    def test_valid_pinterest_pin_size(self):
        from openai_provider import _validate_size
        w, h = _validate_size(1024, 1536)
        assert w == 1024 and h == 1536

    def test_valid_square(self):
        from openai_provider import _validate_size
        w, h = _validate_size(1024, 1024)
        assert w == 1024 and h == 1024

    def test_valid_landscape(self):
        from openai_provider import _validate_size
        w, h = _validate_size(1536, 1024)
        assert w == 1536 and h == 1024

    def test_rounds_to_multiple_of_16(self):
        from openai_provider import _validate_size
        # 1000x1500 → should round to 1008x1504 (multiples of 16)
        w, h = _validate_size(1000, 1500)
        assert w % 16 == 0
        assert h % 16 == 0

    def test_clamps_max_edge(self):
        from openai_provider import _validate_size
        w, h = _validate_size(5000, 3000)
        # max edge 5000 → should be clamped to 3840
        assert max(w, h) <= 3840

    def test_rejects_too_wide_aspect(self):
        from openai_provider import _validate_size, OpenAIGenerationError
        # 4:1 ratio violates the 3:1 max
        with pytest.raises(OpenAIGenerationError) as exc_info:
            _validate_size(2000, 500)
        assert "ratio" in str(exc_info.value).lower() or "3:1" in str(exc_info.value)

    def test_rejects_zero_dimensions(self):
        from openai_provider import _validate_size, OpenAIGenerationError
        with pytest.raises(OpenAIGenerationError):
            _validate_size(0, 1000)
        with pytest.raises(OpenAIGenerationError):
            _validate_size(1000, 0)

    def test_scales_up_tiny_images(self):
        from openai_provider import _validate_size, MIN_TOTAL_PIXELS
        # 100x100 = 10,000 pixels — way below 655,360 minimum
        w, h = _validate_size(100, 100)
        assert w * h >= MIN_TOTAL_PIXELS


class TestOpenAIAspectMapping:
    """Test that aspect ratio strings map to sensible (w, h) tuples."""

    def test_pinterest_pin_aspect_to_size(self):
        from openai_provider import _aspect_and_format_to_size
        w, h = _aspect_and_format_to_size("2:3")
        assert w == 1024 and h == 1536

    def test_square_aspect(self):
        from openai_provider import _aspect_and_format_to_size
        w, h = _aspect_and_format_to_size("1:1")
        assert w == 1024 and h == 1024

    def test_landscape_aspect(self):
        from openai_provider import _aspect_and_format_to_size
        w, h = _aspect_and_format_to_size("3:2")
        assert w == 1536 and h == 1024

    def test_direct_dimension_hint_overrides_aspect(self):
        from openai_provider import _aspect_and_format_to_size
        w, h = _aspect_and_format_to_size("1:1", width_hint=2048, height_hint=1024)
        # Should use hints (validated) instead of square default
        assert w == 2048 and h == 1024

    def test_unknown_aspect_falls_back_to_square(self):
        from openai_provider import _aspect_and_format_to_size
        w, h = _aspect_and_format_to_size("totally-bogus")
        assert w == 1024 and h == 1024


class TestOpenAIProviderErrors:
    """Test error paths in the provider."""

    def test_missing_api_key_raises(self, tmp_path):
        from openai_provider import generate_image, OpenAIGenerationError

        # Clear the env var
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(OpenAIGenerationError) as exc_info:
                generate_image(
                    prompt="test",
                    aspect_ratio="1:1",
                    output_path=tmp_path / "out.png",
                )
            assert exc_info.value.error_type == "missing_credentials"

    def test_invalid_quality_raises(self, tmp_path):
        """Invalid quality string is rejected.

        Note: this test requires the `openai` package to be installed because
        the provider checks for it before validating arguments. If openai isn't
        installed, we get missing_dependency first (which is also correct
        behavior — fail fast on the dependency).
        """
        from openai_provider import generate_image, OpenAIGenerationError

        # Skip if openai package isn't available (CI sandbox)
        try:
            import openai  # noqa: F401
        except ImportError:
            pytest.skip("openai package not installed")

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with pytest.raises(OpenAIGenerationError) as exc_info:
                generate_image(
                    prompt="test",
                    aspect_ratio="1:1",
                    output_path=tmp_path / "out.png",
                    quality="ultra",  # type: ignore  # invalid
                )
            assert exc_info.value.error_type == "bad_args"

    def test_invalid_format_raises(self, tmp_path):
        """Invalid output_format string is rejected. See note in
        test_invalid_quality_raises about openai package dependency.
        """
        from openai_provider import generate_image, OpenAIGenerationError

        try:
            import openai  # noqa: F401
        except ImportError:
            pytest.skip("openai package not installed")

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with pytest.raises(OpenAIGenerationError) as exc_info:
                generate_image(
                    prompt="test",
                    aspect_ratio="1:1",
                    output_path=tmp_path / "out.png",
                    output_format="gif",  # type: ignore  # invalid
                )
            assert exc_info.value.error_type == "bad_args"

    def test_missing_openai_package_raises(self, tmp_path):
        """When openai package isn't installed, we get a clear error."""
        from openai_provider import generate_image, OpenAIGenerationError

        # This test only fires when openai isn't installed
        try:
            import openai  # noqa: F401
            pytest.skip("openai package IS installed; skipping the not-installed test")
        except ImportError:
            pass

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}):
            with pytest.raises(OpenAIGenerationError) as exc_info:
                generate_image(
                    prompt="test",
                    aspect_ratio="1:1",
                    output_path=tmp_path / "out.png",
                )
            assert exc_info.value.error_type == "missing_dependency"


class TestInfographicPlatform:
    """Test that the infographic platform is correctly configured."""

    def test_registered(self):
        from platforms import get_platform
        infographic = get_platform("infographic")
        assert infographic.platform_id == "infographic"

    def test_aliases(self):
        from platforms import get_platform
        for alias in ["pin", "pinterest", "info", "infographics"]:
            assert get_platform(alias).platform_id == "infographic"

    def test_has_three_formats(self):
        from platforms import get_platform
        infographic = get_platform("infographic")
        format_names = {f.name for f in infographic.output_formats}
        assert format_names == {"pinterest_pin", "square_card", "landscape_poster"}

    def test_pinterest_pin_is_primary(self):
        from platforms import get_platform
        infographic = get_platform("infographic")
        primary = [f for f in infographic.output_formats if f.is_primary]
        assert len(primary) == 1
        assert primary[0].name == "pinterest_pin"
        assert primary[0].width == 1024
        assert primary[0].height == 1536

    def test_avoids_illustration_styles(self):
        from platforms import get_platform
        infographic = get_platform("infographic")
        # Infographic platform should avoid all the editorial-illustration styles
        for illustration_style in ["editorial", "cinematic", "hand-drawn",
                                    "collage", "neon-tech", "retro-print",
                                    "isometric", "minimalist"]:
            assert illustration_style in infographic.avoided_styles, (
                f"Expected {illustration_style} to be in infographic.avoided_styles"
            )

    def test_prefers_infographic_styles(self):
        from platforms import get_platform
        infographic = get_platform("infographic")
        assert "infographic-modern" in infographic.preferred_styles
        assert "infographic-editorial" in infographic.preferred_styles
        assert "infographic-tech" in infographic.preferred_styles
        assert "infographic-classic" in infographic.preferred_styles

    def test_light_rotation_philosophy(self):
        from platforms import get_platform
        infographic = get_platform("infographic")
        assert infographic.rotation_philosophy == "light"


class TestIllustrationPlatformsAvoidInfographicStyles:
    """The other platforms should NOT pull in infographic styles via rotation."""

    @pytest.mark.parametrize("platform_id", [
        "medium", "linkedin", "twitter", "instagram", "meta"
    ])
    def test_avoids_infographic_styles(self, platform_id):
        from platforms import get_platform
        platform = get_platform(platform_id)
        for inf_style in ["infographic-modern", "infographic-editorial",
                          "infographic-tech", "infographic-classic"]:
            assert inf_style in platform.avoided_styles, (
                f"Expected {platform_id} to avoid {inf_style}"
            )


class TestBuildPromptTextModeAllow:
    """When text_mode='allow', the label-risk detection should be bypassed."""

    def test_text_mode_allow_skips_label_risk(self, tmp_path):
        from prompt_builder import build_prompt

        engine_dir = Path(__file__).parent.parent

        # This subject has tons of label-shaped text that would normally
        # trigger detection (ALL-CAPS, quoted strings, comma-separated labels)
        subject = (
            'Headline: "THE FIVE-TOOL TRAP". '
            'Section 1: title "REPORTS", number "2 HRS", body "pulling data". '
            'Section 2: title "INSPIRATION", number "847", body "screenshots saved". '
            'Footer: "by Varun Tyagi · voltic.ai".'
        )

        prompt, fmt, metadata = build_prompt(
            platform_id="infographic",
            format_name="pinterest_pin",
            style="infographic-modern",
            palette_id="cold-architecture",
            composition="vertical-stack",
            subject=subject,
            engine_dir=engine_dir,
            text_mode="allow",
        )

        # With text_mode=allow, label risk detection should be disabled.
        assert metadata["label_risk_detected"] is False
        assert metadata["subject_was_rewritten"] is False
        # The subject should appear verbatim in the prompt
        assert "THE FIVE-TOOL TRAP" in prompt

    def test_text_mode_block_still_detects_labels(self, tmp_path):
        from prompt_builder import build_prompt

        engine_dir = Path(__file__).parent.parent

        subject = "INSPIRATION folder full of saved screenshots"

        prompt, fmt, metadata = build_prompt(
            platform_id="medium",
            format_name="hero",
            style="editorial",
            palette_id="bone-and-rust",
            composition="centered-subject",
            subject=subject,
            engine_dir=engine_dir,
            text_mode="block",  # default for illustration skills
        )

        # With text_mode=block, the ALL-CAPS "INSPIRATION" should trigger detection
        assert metadata["label_risk_detected"] is True


class TestInfographicStyleTemplatesExist:
    """The four infographic styles need actual template files."""

    @pytest.mark.parametrize("style", [
        "infographic-modern",
        "infographic-editorial",
        "infographic-tech",
        "infographic-classic",
    ])
    def test_template_file_exists(self, style):
        engine_dir = Path(__file__).parent.parent
        template_path = engine_dir / "assets" / "style_templates" / f"{style}.md"
        assert template_path.exists(), f"Missing style template: {template_path}"

    @pytest.mark.parametrize("style", [
        "infographic-modern",
        "infographic-editorial",
        "infographic-tech",
        "infographic-classic",
    ])
    def test_template_has_reference_phrasing(self, style):
        engine_dir = Path(__file__).parent.parent
        template_path = engine_dir / "assets" / "style_templates" / f"{style}.md"
        content = template_path.read_text()
        # Every style template needs this section so extract_lead_sentence can find a lead
        assert "## Reference Phrasing for OpenAI" in content or "## Reference Phrasing" in content


class TestSubjectExtractionInfographicReferenceExists:
    """The infographic-specific subject extraction reference should be installed."""

    def test_reference_file_exists(self):
        engine_dir = Path(__file__).parent.parent
        ref_path = engine_dir / "references" / "subject-extraction-infographic.md"
        assert ref_path.exists()

    def test_reference_has_structured_format(self):
        engine_dir = Path(__file__).parent.parent
        ref_path = engine_dir / "references" / "subject-extraction-infographic.md"
        content = ref_path.read_text()
        # The reference should teach the structured Headline/Section/Footer format
        assert "Headline:" in content
        assert "Section" in content
        assert "Footer" in content
