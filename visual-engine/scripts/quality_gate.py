"""
visual_engine.quality_gate
==========================

Post-generation image quality checks. Goes beyond OCR text-leak detection
to catch composition, palette, face-integrity, and mobile-thumbnail issues
that only a vision model can flag.

Two tiers:
  cheap  - one Claude Haiku call per image, returns a 4-axis scorecard.
  strict - cheap pass plus a second-opinion prompt-vs-image comparison.

Both are off by default. Opt in via --quality-gate on the engine generate
subcommand. The cheap tier is fast (~2-3s) and adds a few cents per image
in API cost; the strict tier roughly doubles both.

Design notes:
- Provider-agnostic surface: evaluate_image(...) returns a dict, callers
  read the same shape regardless of backend.
- Soft-fails when the SDK or key is missing. The engine should treat
  "unavailable" as a non-blocking outcome, not an error, so quality-gate
  off and quality-gate unavailable behave the same.
- No third-party validation library; we hand-parse the JSON response
  with bounded forgiveness for common LLM formatting glitches (trailing
  commentary, markdown fences).
"""

from __future__ import annotations

import base64
import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Thresholds
# ---------------------------------------------------------------------------

# Each axis is scored 0-10 by the vision model. A frame passes when every
# axis clears the floor. These floors are conservative on purpose: the
# point is to catch obvious failures, not to gate on taste.
DEFAULT_AXIS_FLOOR = 6
DEFAULT_AXES = (
    "face_integrity",
    "composition_clarity",
    "palette_adherence",
    "thumbnail_readability",
)

# Anthropic vision-capable models. We default to the cheapest currently
# available; callers can override via ANTHROPIC_QUALITY_MODEL env var.
DEFAULT_ANTHROPIC_CHEAP_MODEL = "claude-haiku-4-5-20251001"
DEFAULT_ANTHROPIC_STRICT_MODEL = "claude-haiku-4-5-20251001"

# OpenAI vision-capable models. gpt-4o-mini is the cheap default; users can
# override via OPENAI_QUALITY_MODEL env var. Use gpt-4o or newer for strict.
DEFAULT_OPENAI_CHEAP_MODEL = "gpt-4o-mini"
DEFAULT_OPENAI_STRICT_MODEL = "gpt-4o-mini"

# Provider precedence when --quality-provider is "auto". We prefer Anthropic
# when both keys are set because the Haiku prompt-following on JSON output is
# very tight, but either works and the choice has no effect on the result shape.
_AUTO_PROVIDER_ORDER = ("anthropic", "openai")


# ---------------------------------------------------------------------------
# Result shape
# ---------------------------------------------------------------------------


@dataclass
class QualityResult:
    """Outcome of one quality-gate evaluation."""
    status: str  # "ok" | "unavailable" | "error"
    passed: bool
    tier: str
    scores: dict[str, int] = field(default_factory=dict)
    issues: list[str] = field(default_factory=list)
    model: str = ""
    raw_response: str = ""
    error_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "passed": self.passed,
            "tier": self.tier,
            "scores": self.scores,
            "issues": self.issues,
            "model": self.model,
            "error_message": self.error_message,
        }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def evaluate_image(
    image_path: Path,
    *,
    tier: str = "cheap",
    prompt_context: str = "",
    palette_hint: str = "",
    style_hint: str = "",
    axis_floor: int = DEFAULT_AXIS_FLOOR,
    model: str | None = None,
    provider: str = "auto",
) -> QualityResult:
    """Evaluate a generated image against quality heuristics.

    Args:
        image_path:     Local path to the rendered PNG/JPEG.
        tier:           "cheap" (single vision call) or "strict" (cheap + comparison).
        prompt_context: The original generation prompt or its summary. Helps the
                        judge spot prompt-vs-image drift on the strict tier.
        palette_hint:   Free-text palette description ("bone-and-rust: bone white,
                        rust orange, forest, charcoal"). Lets the judge verify
                        palette adherence without us having to teach it the palette.
        style_hint:     Style label ("editorial", "isometric", etc.) used as a
                        prior for what "good composition" means here.
        axis_floor:     Per-axis minimum score to pass. Default 6/10.
        model:          Override the vision model. Defaults differ per provider.
        provider:       "auto" (default, prefer Anthropic, fall back to OpenAI),
                        "anthropic", or "openai".

    Returns:
        QualityResult. Check .status first:
          - "ok"          → use .passed and .scores
          - "unavailable" → SDK or key missing; do not treat as a failure
          - "error"       → API call blew up; .error_message has details
    """
    if tier not in ("cheap", "strict"):
        return QualityResult(
            status="error", passed=False, tier=tier,
            error_message=f"Unknown tier: {tier!r} (expected 'cheap' or 'strict')",
        )

    if not image_path.exists():
        return QualityResult(
            status="error", passed=False, tier=tier,
            error_message=f"Image not found: {image_path}",
        )

    resolved_provider, unavailable = _resolve_provider(provider)
    if unavailable is not None:
        return unavailable
    resolved_model = _resolve_model(resolved_provider, tier, model)

    cheap_result = _run_cheap_check(
        provider=resolved_provider,
        image_path=image_path,
        model=resolved_model,
        prompt_context=prompt_context,
        palette_hint=palette_hint,
        style_hint=style_hint,
        axis_floor=axis_floor,
    )

    if tier == "cheap":
        return cheap_result

    if cheap_result.status != "ok" or not cheap_result.passed:
        # Strict adds nothing if cheap already failed or couldn't run.
        cheap_result.tier = "strict"
        return cheap_result

    return _run_strict_check(
        provider=resolved_provider,
        image_path=image_path,
        base_result=cheap_result,
        model=resolved_model,
        prompt_context=prompt_context,
        axis_floor=axis_floor,
    )


def _resolve_provider(requested: str) -> tuple[str, QualityResult | None]:
    """Pick a usable provider. Returns (provider_name, optional unavailable result)."""
    candidates: list[str]
    if requested == "auto":
        candidates = list(_AUTO_PROVIDER_ORDER)
    elif requested in ("anthropic", "openai"):
        candidates = [requested]
    else:
        return "", QualityResult(
            status="error", passed=False, tier="",
            error_message=f"Unknown provider: {requested!r}",
        )

    last_reason = ""
    for name in candidates:
        ok, reason = _provider_ready(name)
        if ok:
            return name, None
        last_reason = reason

    return "", QualityResult(
        status="unavailable", passed=True, tier="",
        error_message=last_reason or "No quality-gate provider configured.",
    )


def _provider_ready(name: str) -> tuple[bool, str]:
    if name == "anthropic":
        try:
            import anthropic  # noqa: F401
        except ImportError:
            return False, "anthropic SDK not installed (pip install anthropic)"
        if not os.environ.get("ANTHROPIC_API_KEY"):
            return False, "ANTHROPIC_API_KEY not set"
        return True, ""
    if name == "openai":
        try:
            import openai  # noqa: F401
        except ImportError:
            return False, "openai SDK not installed (pip install 'openai>=1.50')"
        if not os.environ.get("OPENAI_API_KEY"):
            return False, "OPENAI_API_KEY not set"
        return True, ""
    return False, f"Unknown provider: {name}"


def _resolve_model(provider: str, tier: str, override: str | None) -> str:
    if override:
        return override
    if provider == "anthropic":
        return (
            os.environ.get("ANTHROPIC_QUALITY_MODEL")
            or (DEFAULT_ANTHROPIC_STRICT_MODEL if tier == "strict"
                else DEFAULT_ANTHROPIC_CHEAP_MODEL)
        )
    if provider == "openai":
        return (
            os.environ.get("OPENAI_QUALITY_MODEL")
            or (DEFAULT_OPENAI_STRICT_MODEL if tier == "strict"
                else DEFAULT_OPENAI_CHEAP_MODEL)
        )
    return ""


# ---------------------------------------------------------------------------
# Cheap tier: single multi-axis scorecard
# ---------------------------------------------------------------------------


_CHEAP_SYSTEM = (
    "You are a senior art director reviewing AI-generated images for use on "
    "social platforms. Score images strictly on technical execution, not "
    "taste. Reply with JSON only, no preamble."
)


def _cheap_user_prompt(
    *, prompt_context: str, palette_hint: str, style_hint: str,
) -> str:
    parts = [
        "Score the attached image on four 0-10 axes. Reply with a single JSON "
        "object exactly matching this schema:",
        "",
        "{",
        '  "face_integrity": int 0-10,           // faces look like real faces. '
        '10 = anatomically correct; 0 = melted or distorted. If no faces, return 10.',
        '  "composition_clarity": int 0-10,      // clear focal point, balanced '
        'frame, not muddy or busy.',
        '  "palette_adherence": int 0-10,        // colors stay within the '
        'requested palette.',
        '  "thumbnail_readability": int 0-10,    // would still read at a '
        '200px LinkedIn / mobile feed thumbnail.',
        '  "issues": [string, ...]               // short, specific notes on '
        'anything below 7 on any axis. Empty if all axes are 7+.',
        "}",
        "",
        "Be strict. A 7 is fine; 5 or below is a real defect.",
    ]
    if prompt_context:
        parts.append(f"\nOriginal generation prompt (for context): {prompt_context[:800]}")
    if palette_hint:
        parts.append(f"\nRequested palette: {palette_hint}")
    if style_hint:
        parts.append(f"\nRequested style: {style_hint}")
    return "\n".join(parts)


def _run_cheap_check(
    *,
    provider: str,
    image_path: Path,
    model: str,
    prompt_context: str,
    palette_hint: str,
    style_hint: str,
    axis_floor: int,
) -> QualityResult:
    user_text = _cheap_user_prompt(
        prompt_context=prompt_context,
        palette_hint=palette_hint,
        style_hint=style_hint,
    )

    try:
        encoded, media_type = _encode_image(image_path)
    except OSError as exc:
        return QualityResult(
            status="error", passed=False, tier="cheap",
            error_message=f"Could not read image: {exc}",
        )

    raw_text, err = _vision_call(
        provider=provider,
        model=model,
        system=_CHEAP_SYSTEM,
        user_text=user_text,
        encoded=encoded,
        media_type=media_type,
        max_tokens=600,
    )
    if err is not None:
        return QualityResult(
            status="error", passed=False, tier="cheap", model=model,
            error_message=err,
        )

    parsed = _parse_json_loosely(raw_text)
    if parsed is None:
        return QualityResult(
            status="error", passed=False, tier="cheap", model=model,
            raw_response=raw_text,
            error_message="Could not parse JSON from the model response.",
        )

    scores = {
        axis: _coerce_int_in_range(parsed.get(axis), lo=0, hi=10, default=0)
        for axis in DEFAULT_AXES
    }
    issues = parsed.get("issues") or []
    if not isinstance(issues, list):
        issues = [str(issues)]
    issues = [str(x) for x in issues]

    passed = all(scores[axis] >= axis_floor for axis in DEFAULT_AXES)

    return QualityResult(
        status="ok",
        passed=passed,
        tier="cheap",
        scores=scores,
        issues=issues,
        model=f"{provider}:{model}",
        raw_response=raw_text,
    )


# ---------------------------------------------------------------------------
# Strict tier: prompt-vs-image fidelity comparison
# ---------------------------------------------------------------------------


_STRICT_SYSTEM = (
    "You are a senior reviewer checking whether an AI-generated image faithfully "
    "delivers what its prompt asked for. Reply with JSON only."
)


def _strict_user_prompt(prompt_context: str) -> str:
    return (
        "Compare the attached image against this generation prompt:\n\n"
        f"PROMPT:\n{prompt_context[:2000]}\n\n"
        "Reply with a single JSON object:\n"
        "{\n"
        '  "fidelity_score": int 0-10,  // how well the image matches the prompt\n'
        '  "missing_elements": [string, ...],  // requested elements not visible\n'
        '  "added_elements": [string, ...]     // visible elements not requested\n'
        "}\n\n"
        "Be strict. The subject, composition, palette and style hints in the "
        "prompt are all in scope. Cosmetic differences are fine; semantic drift is not."
    )


def _run_strict_check(
    *,
    provider: str,
    image_path: Path,
    base_result: QualityResult,
    model: str,
    prompt_context: str,
    axis_floor: int,
) -> QualityResult:
    if not prompt_context:
        # Without the prompt there's nothing to compare against; treat as a pass.
        base_result.tier = "strict"
        return base_result

    try:
        encoded, media_type = _encode_image(image_path)
    except OSError as exc:
        return QualityResult(
            status="error", passed=False, tier="strict", model=model,
            scores=base_result.scores, issues=base_result.issues,
            error_message=f"Could not read image: {exc}",
        )

    raw_text, err = _vision_call(
        provider=provider,
        model=model,
        system=_STRICT_SYSTEM,
        user_text=_strict_user_prompt(prompt_context),
        encoded=encoded,
        media_type=media_type,
        max_tokens=600,
    )
    if err is not None:
        return QualityResult(
            status="error", passed=False, tier="strict", model=model,
            scores=base_result.scores, issues=base_result.issues,
            error_message=err,
        )

    parsed = _parse_json_loosely(raw_text) or {}

    fidelity = _coerce_int_in_range(parsed.get("fidelity_score"), lo=0, hi=10, default=0)
    missing = [str(x) for x in (parsed.get("missing_elements") or []) if x]
    added = [str(x) for x in (parsed.get("added_elements") or []) if x]

    merged_scores = dict(base_result.scores)
    merged_scores["prompt_fidelity"] = fidelity

    merged_issues = list(base_result.issues)
    if missing:
        merged_issues.append("Missing from image: " + "; ".join(missing))
    if added:
        merged_issues.append("Unexpected in image: " + "; ".join(added))

    passed = base_result.passed and fidelity >= axis_floor

    return QualityResult(
        status="ok",
        passed=passed,
        tier="strict",
        scores=merged_scores,
        issues=merged_issues,
        model=f"{provider}:{model}",
        raw_response=raw_text,
    )


# ---------------------------------------------------------------------------
# Provider-specific vision call. Returns (text, error_message_or_None).
# ---------------------------------------------------------------------------


def _vision_call(
    *,
    provider: str,
    model: str,
    system: str,
    user_text: str,
    encoded: str,
    media_type: str,
    max_tokens: int,
) -> tuple[str, str | None]:
    if provider == "anthropic":
        return _vision_call_anthropic(
            model=model, system=system, user_text=user_text,
            encoded=encoded, media_type=media_type, max_tokens=max_tokens,
        )
    if provider == "openai":
        return _vision_call_openai(
            model=model, system=system, user_text=user_text,
            encoded=encoded, media_type=media_type, max_tokens=max_tokens,
        )
    return "", f"Unknown provider: {provider}"


def _vision_call_anthropic(
    *, model: str, system: str, user_text: str,
    encoded: str, media_type: str, max_tokens: int,
) -> tuple[str, str | None]:
    try:
        import anthropic
    except ImportError:
        return "", "anthropic SDK missing"
    try:
        client = anthropic.Anthropic()
        response = client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": media_type,
                            "data": encoded,
                        },
                    },
                    {"type": "text", "text": user_text},
                ],
            }],
        )
    except Exception as exc:
        return "", f"{type(exc).__name__}: {exc}"

    text = "".join(
        b.text for b in response.content if getattr(b, "type", "") == "text"
    )
    return text, None


def _vision_call_openai(
    *, model: str, system: str, user_text: str,
    encoded: str, media_type: str, max_tokens: int,
) -> tuple[str, str | None]:
    try:
        import openai
    except ImportError:
        return "", "openai SDK missing"
    try:
        client = openai.OpenAI()
        response = client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:{media_type};base64,{encoded}",
                                "detail": "low",
                            },
                        },
                    ],
                },
            ],
        )
    except Exception as exc:
        return "", f"{type(exc).__name__}: {exc}"

    choices = getattr(response, "choices", None) or []
    if not choices:
        return "", "OpenAI returned no choices"
    message = getattr(choices[0], "message", None)
    if message is None:
        return "", "OpenAI returned no message"
    content = getattr(message, "content", "") or ""
    return content, None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _encode_image(path: Path) -> tuple[str, str]:
    """Read an image, return (base64_string, media_type)."""
    data = path.read_bytes()
    suffix = path.suffix.lower()
    media_type = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(suffix, "image/png")
    return base64.standard_b64encode(data).decode("ascii"), media_type


_JSON_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _parse_json_loosely(text: str) -> dict[str, Any] | None:
    """Try hard to extract a JSON object from a model response."""
    if not text:
        return None

    # Strip markdown fences if present.
    fence_match = _JSON_FENCE_RE.search(text)
    if fence_match:
        text = fence_match.group(1)

    # Fast path.
    try:
        result = json.loads(text)
        return result if isinstance(result, dict) else None
    except json.JSONDecodeError:
        pass

    # Slow path: find the first { ... } block that parses.
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            ch = text[i]
            if ch == "{":
                depth += 1
            elif ch == "}":
                depth -= 1
                if depth == 0:
                    candidate = text[start:i + 1]
                    try:
                        result = json.loads(candidate)
                        if isinstance(result, dict):
                            return result
                    except json.JSONDecodeError:
                        break
                    break
        start = text.find("{", start + 1)

    return None


def _coerce_int_in_range(value: Any, *, lo: int, hi: int, default: int) -> int:
    """Coerce a model output to an int and clamp it. Tolerant of strings."""
    try:
        if isinstance(value, bool):
            return default
        if isinstance(value, (int, float)):
            return max(lo, min(hi, int(value)))
        if isinstance(value, str):
            stripped = value.strip()
            if stripped:
                return max(lo, min(hi, int(float(stripped))))
    except (TypeError, ValueError):
        pass
    return default
