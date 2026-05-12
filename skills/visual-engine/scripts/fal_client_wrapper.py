"""
visual_engine.fal_client_wrapper
================================

Wraps fal.ai's API for image generation. Uses the `subscribe()` blocking
pattern which handles status polling internally. Single image per call.

Notes on the fal.ai API:
- Endpoint: fal-ai/gemini-3-pro-image-preview (Nano Banana Pro)
- Supported aspect_ratio values are a closed enum (see ASPECT_RATIOS_SUPPORTED).
  We map our richer "platform format" aspect ratios to the closest supported
  ratio. The image returned will be at the supported ratio; the caller is
  expected to crop/letterbox if a different final size is needed.
- Pricing: roughly $0.05-0.15 per image depending on resolution.
"""

from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

FAL_ENDPOINT = "fal-ai/gemini-3-pro-image-preview"

# The closed enum of aspect ratios fal.ai's Gemini 3 Pro Image endpoint accepts.
# Source: https://fal.ai/models/fal-ai/gemini-3-pro-image-preview/api
ASPECT_RATIOS_SUPPORTED = {
    "auto", "21:9", "16:9", "3:2", "4:3", "5:4", "1:1",
    "4:5", "3:4", "2:3", "9:16",
}

# Mapping from our platform-format aspect ratios to a supported fal.ai ratio.
# When the requested ratio is not directly supported (e.g. LinkedIn's 1.91:1,
# Meta's 1.91:1), we pick the visually closest supported ratio. The caller
# may want to crop the output to the exact ratio after download.
ASPECT_RATIO_FALLBACK = {
    "1.91:1": "16:9",   # LinkedIn cover, Meta feed, Meta event cover
}


class GenerationError(Exception):
    """Raised when image generation fails. Carries a structured error_type."""

    def __init__(self, error_type: str, message: str):
        super().__init__(message)
        self.error_type = error_type
        self.message = message


def normalize_aspect_ratio(aspect_ratio: str) -> tuple[str, bool]:
    """Map a requested aspect ratio to one fal.ai accepts.

    Returns:
        (normalized_ratio, was_remapped) — was_remapped is True if we had to
        substitute a different supported ratio for the request.
    """
    if aspect_ratio in ASPECT_RATIOS_SUPPORTED:
        return (aspect_ratio, False)
    if aspect_ratio in ASPECT_RATIO_FALLBACK:
        return (ASPECT_RATIO_FALLBACK[aspect_ratio], True)
    # Unknown ratio — default to auto and let the model decide.
    return ("auto", True)


def check_environment() -> str | None:
    """Return FAL_KEY or None if not set."""
    return os.environ.get("FAL_KEY")


def import_fal_client():
    """Lazy import so this module loads cleanly without fal-client installed."""
    try:
        import fal_client  # type: ignore
        return fal_client
    except ImportError:
        return None


def classify_error(exc: BaseException) -> tuple[str, str]:
    """Map any exception to (error_type, friendly_message).

    error_type is one of:
        rate_limit, timeout, policy_violation, auth, network,
        invalid_request, unknown.
    """
    msg = str(exc).lower()
    exc_name = type(exc).__name__.lower()

    # fal-client may raise its own typed exceptions; we check by name to avoid
    # importing fal_client at module load.
    if "fal" in exc_name and "timeout" in exc_name:
        return ("timeout", "fal.ai client timed out waiting for the result.")

    if "rate" in msg and "limit" in msg:
        return ("rate_limit", "fal.ai rate limit hit. Wait a few seconds and retry.")
    if "timeout" in msg or "timed out" in msg:
        return ("timeout", "Generation took too long. Retry, or fall back to prompt-only.")
    if any(k in msg for k in ("safety", "policy", "blocked", "moderation")):
        return ("policy_violation",
                "Gemini's content policy rejected the prompt. Try a less suggestive subject.")
    if "401" in msg or "403" in msg or "unauthorized" in msg or "forbidden" in msg \
            or ("invalid" in msg and "key" in msg):
        return ("auth", "fal.ai rejected the API key. Check FAL_KEY.")
    if "404" in msg and ("endpoint" in msg or "model" in msg or "not found" in msg):
        return ("invalid_request", "fal.ai endpoint not found. Check FAL_ENDPOINT.")
    if "400" in msg or "bad request" in msg or ("invalid" in msg and "aspect" in msg):
        return ("invalid_request", f"fal.ai rejected the request: {exc}")
    if any(k in msg for k in ("network", "connection", "dns", "resolve", "unreachable")):
        return ("network", "Network error reaching fal.ai.")
    return ("unknown", f"fal.ai generation failed: {exc}")


def download_image(url: str, dest: Path, timeout: int = 60) -> None:
    """Download an image from a URL to a local path.

    Validates the Content-Type looks like an image. Refuses HTML or text bodies.
    """
    req = Request(url, headers={"User-Agent": "content-image-suite/1.0"})
    try:
        with urlopen(req, timeout=timeout) as resp:
            if resp.status != 200:
                raise GenerationError("download_failed",
                                      f"HTTP {resp.status} downloading {url}")
            content_type = (resp.headers.get("Content-Type") or "").lower()
            if content_type and not content_type.startswith("image/"):
                raise GenerationError(
                    "download_failed",
                    f"fal.ai returned non-image content (type={content_type}) at {url}",
                )
            payload = resp.read()
    except (URLError, HTTPError, TimeoutError) as exc:
        raise GenerationError("download_failed",
                              f"Cannot download image from {url}: {exc}")

    if len(payload) < 1024:
        # Real images from fal.ai are at minimum tens of KB; a tiny payload
        # is almost certainly an error page or stub.
        raise GenerationError("download_failed",
                              f"Downloaded image is suspiciously small ({len(payload)}B).")

    # Write atomically: write to .partial, then rename. Prevents leaving a
    # half-written file if the process dies mid-write.
    partial = dest.with_suffix(dest.suffix + ".partial")
    try:
        partial.write_bytes(payload)
        os.replace(partial, dest)
    except OSError as exc:
        try:
            partial.unlink(missing_ok=True)
        except OSError:
            pass
        raise GenerationError("download_failed",
                              f"Cannot save image to {dest}: {exc}")


def _extract_image_url(result: Any) -> str:
    """Pull the first image URL out of a fal.ai result, raising on any malformation."""
    if not isinstance(result, dict):
        raise GenerationError("unknown",
                              f"fal.ai returned non-dict response (got {type(result).__name__})")

    images = result.get("images")
    if not isinstance(images, list) or not images:
        raise GenerationError("unknown",
                              "fal.ai response had no images. "
                              f"Keys present: {sorted(result.keys())}")

    first = images[0]
    if not isinstance(first, dict):
        raise GenerationError("unknown",
                              f"fal.ai images[0] is not a dict (got {type(first).__name__})")

    url = first.get("url")
    if not isinstance(url, str) or not url:
        raise GenerationError("unknown",
                              "fal.ai images[0] had no usable url field. "
                              f"Keys present: {sorted(first.keys())}")

    return url


def generate_image(
    *,
    prompt: str,
    aspect_ratio: str,
    output_path: Path,
    timeout: int = 180,
    retry_once: bool = True,
    num_images: int = 1,
) -> dict[str, Any]:
    """Generate one image from a prompt and save it locally.

    Uses fal_client.subscribe() which polls the queue internally.

    Args:
        prompt: The full Gemini prompt text.
        aspect_ratio: Requested aspect ratio. If not in the supported enum,
                      will be remapped (and the result dict will indicate so).
        output_path: Where to save the downloaded PNG.
        timeout: Total client-side deadline in seconds.
        retry_once: If True, retry once on rate_limit/timeout/network errors.
        num_images: Always 1 in current usage. Future-proofing.

    Returns:
        Dict with keys: status, local_path, remote_url, duration_seconds,
                        aspect_ratio_used, aspect_ratio_was_remapped,
                        aspect_ratio_requested.

    Raises:
        GenerationError on any failure, with .error_type set.
    """
    # ----- Input validation -----
    if not isinstance(prompt, str) or len(prompt.strip()) < 30:
        raise GenerationError("invalid_prompt", "Prompt is too short (under 30 chars).")
    if len(prompt) > 4000:
        raise GenerationError("invalid_prompt", "Prompt is too long (over 4000 chars).")
    if num_images < 1 or num_images > 4:
        raise GenerationError("invalid_request", "num_images must be 1-4.")

    if not check_environment():
        raise GenerationError(
            "fal_key_missing",
            "FAL_KEY environment variable is not set. "
            "Set it with: export FAL_KEY=your_key",
        )

    fal_client = import_fal_client()
    if fal_client is None:
        raise GenerationError(
            "fal_client_missing",
            "fal-client package not installed. Install with: pip install fal-client",
        )

    # Map aspect ratio to one fal accepts.
    normalized_aspect, was_remapped = normalize_aspect_ratio(aspect_ratio)

    # Ensure output directory exists.
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise GenerationError("invalid_request",
                              f"Cannot create output directory {output_path.parent}: {exc}")

    # ----- Submit + wait, with one retry on transient errors -----
    start = time.time()
    attempts = 2 if retry_once else 1
    result: Any = None
    last_error: tuple[str, str] | None = None

    for attempt in range(attempts):
        try:
            arguments = {
                "prompt": prompt,
                "aspect_ratio": normalized_aspect,
                "num_images": num_images,
            }
            # subscribe() blocks until the request is complete or fails.
            # It handles polling internally so we don't need our own loop.
            # client_timeout is supported by recent fal-client versions.
            # Pass it best-effort; if unsupported, retry without it.
            try:
                result = fal_client.subscribe(
                    FAL_ENDPOINT,
                    arguments=arguments,
                    with_logs=False,
                    client_timeout=timeout,
                )
            except TypeError:
                # Older fal-client without client_timeout kwarg.
                result = fal_client.subscribe(
                    FAL_ENDPOINT,
                    arguments=arguments,
                    with_logs=False,
                )
            break
        except BaseException as exc:  # noqa: BLE001 — we classify all errors
            last_error = classify_error(exc)
            transient = last_error[0] in ("rate_limit", "timeout", "network")
            if attempt < attempts - 1 and transient:
                time.sleep(5)
                last_error = None
                continue
            raise GenerationError(*last_error)

    if result is None:
        # Shouldn't reach here — the loop either breaks (success) or raises.
        raise GenerationError(*(last_error or ("unknown", "fal.ai returned no result.")))

    # ----- Parse the result and download the image -----
    image_url = _extract_image_url(result)
    download_image(image_url, output_path)

    return {
        "status": "ok",
        "local_path": str(output_path),
        "remote_url": image_url,
        "duration_seconds": round(time.time() - start, 2),
        "aspect_ratio_used": normalized_aspect,
        "aspect_ratio_was_remapped": was_remapped,
        "aspect_ratio_requested": aspect_ratio,
    }
