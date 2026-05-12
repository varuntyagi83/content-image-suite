"""Tests for the optional OCR-based text detection module."""
from __future__ import annotations

from pathlib import Path

import pytest

from text_detection import detect_text_in_image, import_pil, import_pytesseract


class TestTextDetectionGracefulFallback:
    """The module handles missing dependencies gracefully."""

    def test_returns_unavailable_on_missing_image(self, tmp_path):
        result = detect_text_in_image(tmp_path / "does-not-exist.png")
        # Either ocr_unavailable (missing dep) or ok (file missing but no error path)
        # The important thing: it never raises.
        assert "status" in result
        assert "passed" in result
        assert "ocr_available" in result

    def test_returns_structured_response_always(self, tmp_path):
        result = detect_text_in_image(tmp_path / "anything.png")
        # Check shape regardless of dependency availability.
        assert "words_found" in result
        assert "raw_word_count" in result
        assert "filtered_word_count" in result
        assert isinstance(result["passed"], bool)


# Only run these tests if pytesseract + PIL are both available.
pytest_skip_no_ocr = pytest.mark.skipif(
    import_pytesseract() is None or import_pil() is None,
    reason="pytesseract or PIL not installed",
)


@pytest_skip_no_ocr
class TestTextDetectionWithOCRInstalled:
    """End-to-end tests with synthetic images. Only run if OCR is available."""

    def _make_image_with_text(self, tmp_path, text):
        Image = import_pil()
        from PIL import ImageDraw, ImageFont
        img = Image.new('RGB', (1200, 800), color='white')
        draw = ImageDraw.Draw(img)
        # Try common font paths; fall back to default if unavailable
        font = None
        for font_path in [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/Library/Fonts/Arial.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]:
            try:
                font = ImageFont.truetype(font_path, 80)
                break
            except (OSError, IOError):
                continue
        if font is None:
            font = ImageFont.load_default()
        draw.text((100, 200), text, fill='black', font=font)
        out = tmp_path / "text_test.png"
        img.save(str(out))
        return out

    def _make_image_no_text(self, tmp_path):
        Image = import_pil()
        from PIL import ImageDraw
        img = Image.new('RGB', (1200, 800), color='lightblue')
        draw = ImageDraw.Draw(img)
        draw.ellipse([200, 200, 600, 600], fill='red')
        draw.rectangle([700, 300, 1100, 500], fill='green')
        out = tmp_path / "no_text.png"
        img.save(str(out))
        return out

    def test_detects_rendered_text(self, tmp_path):
        img = self._make_image_with_text(tmp_path, "INSPIRATION")
        result = detect_text_in_image(img)
        # Should pass on the existence-check path (since OCR is available)
        if result["status"] == "ocr_unavailable":
            pytest.skip("Tesseract binary not on PATH in test environment")
        assert result["status"] == "text_detected"
        assert result["passed"] is False
        assert any("INSPIRATION" in w.upper() for w in result["words_found"])

    def test_passes_text_free_image(self, tmp_path):
        img = self._make_image_no_text(tmp_path)
        result = detect_text_in_image(img)
        if result["status"] == "ocr_unavailable":
            pytest.skip("Tesseract binary not on PATH in test environment")
        assert result["status"] == "ok"
        assert result["passed"] is True
        assert result["words_found"] == []

    def test_max_acceptable_words_threshold(self, tmp_path):
        img = self._make_image_with_text(tmp_path, "INSPIRATION DRAFTS")
        # With max_acceptable_words=5, even some text should pass
        result = detect_text_in_image(img, max_acceptable_words=5)
        if result["status"] == "ocr_unavailable":
            pytest.skip("Tesseract binary not on PATH in test environment")
        # The OCR may find a few words but the threshold tolerates them
        assert result["passed"] is True
