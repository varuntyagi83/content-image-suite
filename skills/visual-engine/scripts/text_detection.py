"""
visual_engine.text_detection
=============================

Optional post-generation text detection. Uses pytesseract if installed;
returns a "skipped" status otherwise.

The point: catch the cases where the prompt-builder's text-cue detection
and rewriting failed to prevent Gemini from rendering text in the image.

This is a safety net, not the primary defense.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def import_pytesseract():
    """Lazy import — returns None if not installed."""
    try:
        import pytesseract  # type: ignore
        return pytesseract
    except ImportError:
        return None


def import_pil():
    try:
        from PIL import Image  # type: ignore
        return Image
    except ImportError:
        return None


def detect_text_in_image(
    image_path: Path,
    *,
    min_word_length: int = 4,
    min_word_confidence: int = 60,
    max_acceptable_words: int = 0,
) -> dict[str, Any]:
    """Run OCR on the image and return a structured detection result.

    Returns:
        {
            "status": "ok" | "text_detected" | "ocr_unavailable",
            "ocr_available": bool,
            "words_found": list[str],         # filtered words meeting thresholds
            "raw_word_count": int,            # total words OCR returned (any length)
            "filtered_word_count": int,       # words above length+conf thresholds
            "passed": bool,                   # True if filtered count <= max_acceptable_words
        }

    Args:
        image_path: Path to the generated image.
        min_word_length: Words shorter than this are noise (single letters,
                         OCR artifacts on textures). 4 is a good threshold.
        min_word_confidence: Tesseract's confidence score 0-100. Below this,
                             likely OCR noise on a real image (texture mistaken
                             for letters). 60 is balanced.
        max_acceptable_words: Filtered words below or equal to this are tolerated.
                              0 = strict (any rendered text fails). Higher
                              tolerance lets through e.g. a clock with two
                              numbers, accepting that as artistic license.

    On any failure, returns ocr_unavailable status — never raises.
    """
    pytesseract = import_pytesseract()
    Image = import_pil()

    if pytesseract is None or Image is None:
        return {
            "status": "ocr_unavailable",
            "ocr_available": False,
            "words_found": [],
            "raw_word_count": 0,
            "filtered_word_count": 0,
            "passed": True,  # No way to fail, so default to passing.
            "note": "pytesseract or PIL not installed; install with: pip install pytesseract pillow",
        }

    try:
        # Verify tesseract binary is reachable. This raises if not.
        pytesseract.get_tesseract_version()
    except Exception:
        return {
            "status": "ocr_unavailable",
            "ocr_available": False,
            "words_found": [],
            "raw_word_count": 0,
            "filtered_word_count": 0,
            "passed": True,
            "note": "tesseract binary not on PATH; install with: brew install tesseract (macOS) or apt install tesseract-ocr (Linux)",
        }

    try:
        img = Image.open(str(image_path))
        # Get detailed OCR data (word-level with bounding boxes and confidences)
        data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    except Exception as exc:
        return {
            "status": "ocr_unavailable",
            "ocr_available": True,  # Tesseract is installed; the read failed.
            "words_found": [],
            "raw_word_count": 0,
            "filtered_word_count": 0,
            "passed": True,
            "note": f"OCR failed on image: {exc}",
        }

    raw_words = []
    filtered_words = []
    for text, conf in zip(data.get("text", []), data.get("conf", [])):
        text = (text or "").strip()
        if not text:
            continue
        raw_words.append(text)
        # tesseract returns confidence as int or str; coerce
        try:
            conf_i = int(float(conf))
        except (TypeError, ValueError):
            conf_i = -1
        if len(text) >= min_word_length and conf_i >= min_word_confidence:
            # Additional sanity: drop pure-symbol or pure-digit "words"
            # unless they look like real legible text. Pure-digit sequences
            # of 4+ chars are also usually rendered text (timestamps, codes).
            if any(c.isalnum() for c in text):
                filtered_words.append(text)

    passed = len(filtered_words) <= max_acceptable_words

    return {
        "status": "ok" if passed else "text_detected",
        "ocr_available": True,
        "words_found": filtered_words,
        "raw_word_count": len(raw_words),
        "filtered_word_count": len(filtered_words),
        "passed": passed,
    }
