"""
visual_engine.openai_provider
=============================

OpenAI image generation provider using gpt-image-2.

gpt-image-2 is OpenAI's state-of-the-art image generation model, released
April 21, 2026. It's the right choice for infographics specifically because:

  - It renders text legibly (significantly improved over gpt-image-1.5,
    which is OpenAI's stated improvement area for this model).
  - It supports arbitrary sizes (any resolution where: max edge <=3840px,
    edges are multiples of 16, aspect ratio <=3:1, total pixels between
    655,360 and 8,294,400). This means we can hit the exact 1024x1536
    Pinterest pin size, or scale up to 2K (2048x3072) for premium output.
  - It supports PNG/JPEG/WebP output with compression control.
  - Quality tiers (low/medium/high/auto) trade speed for fidelity.

Pricing (May 2026, per OpenAI docs):
  - Low:    1024x1536 = $0.005, 1024x1024 = $0.006
  - Medium: 1024x1536 = $0.041, 1024x1024 = $0.053
  - High:   1024x1536 = $0.165, 1024x1024 = $0.211

Default we use is medium portrait = $0.041/image.

API requirements:
  - OPENAI_API_KEY environment variable
  - OpenAI Organization Verification completed (one-time setup in the
    developer console at platform.openai.com/settings/organization/general)
  - openai>=1.50 Python SDK
"""

from __future__ import annotations

import base64
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


class OpenAIGenerationError(Exception):
    """Raised when OpenAI image generation fails."""

    def __init__(self, message: str, error_type: str = "openai_error"):
        super().__init__(message)
        self.message = message
        self.error_type = error_type


# Valid quality tiers per the gpt-image-2 API.
VALID_QUALITIES = {"low", "medium", "high", "auto"}

# Valid output formats.
VALID_FORMATS = {"png", "jpeg", "webp"}

# Model identifier. The current snapshot is gpt-image-2-2026-04-21; the
# unversioned alias "gpt-image-2" is recommended for normal use and tracks
# OpenAI's latest stable release.
DEFAULT_MODEL = "gpt-image-2"

# Size constraints from the gpt-image-2 docs.
MAX_EDGE_PIXELS = 3840
MIN_TOTAL_PIXELS = 655_360
MAX_TOTAL_PIXELS = 8_294_400
MAX_ASPECT_RATIO = 3.0


@dataclass
class GenerationResult:
    """Result of a successful OpenAI image generation."""

    local_path: str
    model: str
    size: str
    quality: str
    output_format: str
    bytes_written: int


def _round_to_multiple_of_16(value: int) -> int:
    """Round a pixel dimension to the nearest multiple of 16."""
    return max(16, ((value + 8) // 16) * 16)


def _validate_size(width: int, height: int) -> tuple[int, int]:
    """Validate and normalize a size to gpt-image-2's constraints.

    Returns (width, height) clamped/rounded to fit:
      - max edge <= 3840
      - both edges multiples of 16
      - aspect ratio (long/short) <= 3:1
      - total pixels in [655_360, 8_294_400]

    Raises OpenAIGenerationError if the input can't be normalized.
    """
    if width <= 0 or height <= 0:
        raise OpenAIGenerationError(
            f"Invalid dimensions: {width}x{height}. Both must be positive.",
            error_type="bad_args",
        )

    # Clamp max edge.
    if max(width, height) > MAX_EDGE_PIXELS:
        scale = MAX_EDGE_PIXELS / max(width, height)
        width = int(width * scale)
        height = int(height * scale)

    # Round to multiples of 16.
    width = _round_to_multiple_of_16(width)
    height = _round_to_multiple_of_16(height)

    # Check aspect ratio.
    long_edge = max(width, height)
    short_edge = min(width, height)
    if long_edge / short_edge > MAX_ASPECT_RATIO:
        raise OpenAIGenerationError(
            f"Aspect ratio {long_edge}:{short_edge} ({long_edge/short_edge:.2f}:1) "
            f"exceeds gpt-image-2's max of 3:1.",
            error_type="bad_args",
        )

    # Check total pixels (after rounding); scale up if too small.
    total = width * height
    if total < MIN_TOTAL_PIXELS:
        scale = (MIN_TOTAL_PIXELS / total) ** 0.5
        width = _round_to_multiple_of_16(int(width * scale * 1.05))   # 5% buffer
        height = _round_to_multiple_of_16(int(height * scale * 1.05))
        total = width * height
        if total < MIN_TOTAL_PIXELS:
            raise OpenAIGenerationError(
                f"Cannot scale {width}x{height} to meet minimum pixel count "
                f"({MIN_TOTAL_PIXELS}). Got total={total}.",
                error_type="bad_args",
            )

    if total > MAX_TOTAL_PIXELS:
        scale = (MAX_TOTAL_PIXELS / total) ** 0.5 * 0.98   # 2% safety
        width = _round_to_multiple_of_16(int(width * scale))
        height = _round_to_multiple_of_16(int(height * scale))

    return (width, height)


def _aspect_and_format_to_size(
    aspect: str,
    width_hint: int = 0,
    height_hint: int = 0,
) -> tuple[int, int]:
    """Map an aspect ratio string + optional dim hints to a valid (w, h).

    For infographics we want the *native* Pinterest pin size (1024x1536),
    not a generic square fallback. The aspect ratio mapping below targets
    the typical infographic format choices.
    """
    a = aspect.lower().strip().replace(" ", "")

    # Direct hint takes priority if provided.
    if width_hint and height_hint:
        return _validate_size(width_hint, height_hint)

    # Common infographic + social aspect ratios.
    aspect_table = {
        "1:1":      (1024, 1024),
        "1x1":      (1024, 1024),
        "2:3":      (1024, 1536),     # Pinterest pin (target)
        "3:2":      (1536, 1024),     # landscape poster
        "3:4":      (1024, 1360),     # softer portrait
        "4:3":      (1360, 1024),
        "9:16":     (1024, 1808),     # vertical mobile
        "16:9":     (1808, 1024),     # widescreen
        "1.91:1":   (1808, 944),      # LinkedIn / OG share
        "21:9":     (2160, 928),
    }
    if a in aspect_table:
        w, h = aspect_table[a]
        return _validate_size(w, h)

    # Try to parse "W:H" arbitrary ratios.
    if ":" in a:
        try:
            wr, hr = a.split(":")
            wr_f, hr_f = float(wr), float(hr)
            if wr_f > 0 and hr_f > 0:
                # Target ~1.5 megapixels with the requested ratio.
                target_pixels = 1_500_000
                width = int((target_pixels * wr_f / hr_f) ** 0.5)
                height = int(target_pixels / width)
                return _validate_size(width, height)
        except ValueError:
            pass

    # Final fallback: square.
    return (1024, 1024)


def generate_image(
    *,
    prompt: str,
    aspect_ratio: str,
    output_path: Path,
    model: str = DEFAULT_MODEL,
    quality: Literal["low", "medium", "high", "auto"] = "medium",
    output_format: Literal["png", "jpeg", "webp"] = "png",
    output_compression: int = 0,
    width_hint: int = 0,
    height_hint: int = 0,
    timeout: int = 180,
    retry_once: bool = True,
) -> dict:
    """Generate an image via gpt-image-2.

    Args:
        prompt: The full text prompt.
        aspect_ratio: e.g. "2:3", "1:1". Mapped to a concrete pixel size.
        output_path: Where to write the resulting image file.
        model: OpenAI model id. Default "gpt-image-2".
        quality: "low" | "medium" | "high" | "auto"
        output_format: "png" (default), "jpeg", or "webp"
        output_compression: 0-100, applies only to jpeg/webp. 0 disables.
        width_hint, height_hint: Direct size override. If both provided,
            they're validated against gpt-image-2 constraints and used
            instead of aspect_ratio.
        timeout: Per-request timeout in seconds.
        retry_once: If True, retry once on transient failures.

    Returns a dict in the same shape as fal_client_wrapper:
      {
        "status": "ok",
        "local_path": "...",
        "model": "gpt-image-2",
        "size": "1024x1536",
        "quality": "medium",
        "output_format": "png",
        "bytes_written": 1234567,
        "provider": "openai-gpt-image",
      }
    """
    if not os.environ.get("OPENAI_API_KEY"):
        raise OpenAIGenerationError(
            "OPENAI_API_KEY environment variable is not set. Add it to your shell "
            "or .env file and try again. Get a key at "
            "https://platform.openai.com/api-keys. Note: gpt-image-2 also "
            "requires Organization Verification at "
            "platform.openai.com/settings/organization/general (one-time setup).",
            error_type="missing_credentials",
        )

    try:
        from openai import OpenAI
    except ImportError:
        raise OpenAIGenerationError(
            "The `openai` Python package is not installed. Run "
            "`pip install 'openai>=1.50'` (or `pip install -r requirements.txt` "
            "from the visual-engine directory).",
            error_type="missing_dependency",
        )

    if quality not in VALID_QUALITIES:
        raise OpenAIGenerationError(
            f"Invalid quality {quality!r}. Must be one of {sorted(VALID_QUALITIES)}.",
            error_type="bad_args",
        )

    if output_format not in VALID_FORMATS:
        raise OpenAIGenerationError(
            f"Invalid output_format {output_format!r}. Must be one of "
            f"{sorted(VALID_FORMATS)}.",
            error_type="bad_args",
        )

    if output_compression and output_format == "png":
        # OpenAI ignores compression for PNG; warn silently by clearing it.
        output_compression = 0

    width, height = _aspect_and_format_to_size(
        aspect_ratio, width_hint, height_hint
    )
    size_str = f"{width}x{height}"

    client = OpenAI(timeout=timeout)

    def _call() -> str:
        """Make the API call. Returns base64-encoded image data."""
        # Build kwargs; compression is only valid for jpeg/webp.
        kwargs: dict = {
            "model": model,
            "prompt": prompt,
            "size": size_str,
            "quality": quality,
            "output_format": output_format,
            "n": 1,
        }
        if output_compression and output_format in ("jpeg", "webp"):
            kwargs["output_compression"] = output_compression

        response = client.images.generate(**kwargs)
        if not response.data:
            raise OpenAIGenerationError(
                "OpenAI returned no image data in response.",
                error_type="empty_response",
            )
        return response.data[0].b64_json

    try:
        b64_data = _call()
    except OpenAIGenerationError:
        raise
    except Exception as exc:  # noqa: BLE001
        if retry_once:
            try:
                b64_data = _call()
            except Exception as retry_exc:  # noqa: BLE001
                raise OpenAIGenerationError(
                    f"OpenAI image generation failed after retry: {retry_exc}",
                    error_type="api_error",
                ) from retry_exc
        else:
            raise OpenAIGenerationError(
                f"OpenAI image generation failed: {exc}",
                error_type="api_error",
            ) from exc

    # Decode and write.
    try:
        image_bytes = base64.b64decode(b64_data)
    except Exception as exc:  # noqa: BLE001
        raise OpenAIGenerationError(
            f"Failed to decode base64 image data: {exc}",
            error_type="decode_error",
        ) from exc

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(image_bytes)

    return {
        "status": "ok",
        "local_path": str(output_path),
        "model": model,
        "size": size_str,
        "quality": quality,
        "output_format": output_format,
        "bytes_written": len(image_bytes),
        "provider": "openai-gpt-image",
    }
