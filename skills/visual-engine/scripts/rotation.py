"""
visual_engine.rotation
======================

The parameterized rotation engine. Takes a PlatformConfig and a manifest,
returns the allowed selections for the next post on that platform.

Key differences from v1:
- Reads the v2 cross-platform manifest schema
- Filters history by platform when computing rotation windows
- Implements "consistency mode" for Instagram (inverted rotation)
- Considers shared identity for cross-session linked content
"""

from __future__ import annotations

from typing import Any

from constants import ALL_COMPOSITIONS, ALL_PALETTES, ALL_STYLES, STYLE_PALETTE_AFFINITY
from platforms import (
    DEFAULT_POST_TYPE_PREFERENCES,
    PlatformConfig,
    get_platform,
)


def _platform_history(
    manifest: dict[str, Any],
    platform_id: str,
) -> list[dict[str, Any]]:
    """Extract the per-platform history from the cross-platform manifest.

    Returns a list of dicts shaped like:
        {
          "content_id": ...,
          "post_date": ...,
          "style": ...,
          "palette_id": ...,
          "compositions": {slot: name, ...},
          "subject_themes": [...],
          "notes": ...,
        }
    sorted descending by post_date.
    """
    pieces = manifest.get("content_pieces", [])
    history: list[dict[str, Any]] = []

    for piece in pieces:
        platform_outputs = piece.get("platform_outputs") or {}
        platform_data = platform_outputs.get(platform_id)
        if not platform_data:
            continue

        history.append({
            "content_id": piece.get("content_id"),
            "post_date": platform_data.get("generated_at") or piece.get("first_seen_date", ""),
            "style": piece.get("shared_identity", {}).get("style"),
            "palette_id": piece.get("shared_identity", {}).get("palette_id"),
            "compositions": platform_data.get("compositions", {}),
            "subject_themes": piece.get("subject_themes", []),
            "notes": platform_data.get("notes", ""),
        })

    history.sort(key=lambda e: str(e.get("post_date") or ""), reverse=True)
    return history


def _all_platforms_history(manifest: dict[str, Any]) -> list[dict[str, Any]]:
    """Flatten all platform outputs into a single chronological list.

    Used when 'cross-platform' rotation needs to consider what's been
    generated anywhere (e.g. for finding the right shared identity).
    """
    pieces = manifest.get("content_pieces", [])
    flat: list[dict[str, Any]] = []

    for piece in pieces:
        platform_outputs = piece.get("platform_outputs") or {}
        for platform_id, platform_data in platform_outputs.items():
            if not platform_data:
                continue
            flat.append({
                "platform_id": platform_id,
                "content_id": piece.get("content_id"),
                "post_date": platform_data.get("generated_at") or piece.get("first_seen_date", ""),
                "style": piece.get("shared_identity", {}).get("style"),
                "palette_id": piece.get("shared_identity", {}).get("palette_id"),
                "compositions": platform_data.get("compositions", {}),
                "subject_themes": piece.get("subject_themes", []),
            })

    flat.sort(key=lambda e: str(e.get("post_date") or ""), reverse=True)
    return flat


def _recent_field(history: list[dict[str, Any]], field: str, window: int) -> set[str]:
    """Return the set of values found at `field` in the last `window` entries."""
    values: set[str] = set()
    for entry in history[:window]:
        v = entry.get(field)
        if isinstance(v, str) and v:
            values.add(v)
    return values


def _recent_composition(
    history: list[dict[str, Any]],
    slot: str,
    window: int,
) -> set[str]:
    """Return composition values for a specific slot from the last `window` entries."""
    values: set[str] = set()
    for entry in history[:window]:
        compositions = entry.get("compositions") or {}
        if isinstance(compositions, dict):
            v = compositions.get(slot)
            if isinstance(v, str) and v:
                values.add(v)
    return values


def _recent_themes(history: list[dict[str, Any]], window: int) -> set[str]:
    """Return the union of subject_themes from the last `window` entries."""
    themes: set[str] = set()
    for entry in history[:window]:
        post_themes = entry.get("subject_themes") or []
        if isinstance(post_themes, list):
            for t in post_themes:
                if isinstance(t, str) and t.strip():
                    themes.add(t.lower().strip())
    return themes


def _detect_active_series(history: list[dict[str, Any]], window: int = 5) -> str | None:
    """Detect an active multi-part series by reading recent notes."""
    for entry in history[:window]:
        notes = entry.get("notes") or ""
        if "series:" in notes.lower():
            for part in notes.split(";"):
                for sub in part.split(","):
                    sub = sub.strip()
                    if sub.lower().startswith("series:"):
                        name = sub[len("series:"):].strip()
                        if name:
                            return name
    return None


def _pick_recommendation(
    allowed: list[str],
    preferences: list[str] | None,
    fallback_order: list[str] | None = None,
) -> str | None:
    """Pick the best item from `allowed` using `preferences`, then fallback."""
    if not allowed:
        return None
    if preferences:
        for pref in preferences:
            if pref in allowed:
                return pref
    if fallback_order:
        for item in fallback_order:
            if item in allowed:
                return item
    return allowed[0]


def _established_palette_for_consistency(
    history: list[dict[str, Any]],
    minimum_history: int = 3,
    minimum_confidence: float = 0.40,
) -> tuple[str | None, str | None]:
    """For consistency-mode platforms, find the established style+palette.

    Looks at the last 5-10 posts on the platform and identifies the most
    frequently used style + palette. Returns (None, None) when:
      - There are fewer than `minimum_history` posts on this platform, OR
      - The most-used style/palette appears in less than `minimum_confidence`
        of recent posts (no clear winner; nothing to lock to).

    On ties (same count), prefers the MORE RECENT style/palette. This matters
    because the user's preferences evolve, and the most-recent tied entry is
    the better predictor of intent.
    """
    if len(history) < minimum_history:
        return (None, None)

    # Look at last 8 entries. history is already sorted desc by date.
    recent = history[:8]
    total = len(recent)

    style_counts: dict[str, int] = {}
    palette_counts: dict[str, int] = {}
    style_last_seen: dict[str, int] = {}    # lower index = more recent
    palette_last_seen: dict[str, int] = {}

    for idx, entry in enumerate(recent):
        s = entry.get("style")
        p = entry.get("palette_id")
        if isinstance(s, str) and s:
            style_counts[s] = style_counts.get(s, 0) + 1
            style_last_seen.setdefault(s, idx)
        if isinstance(p, str) and p:
            palette_counts[p] = palette_counts.get(p, 0) + 1
            palette_last_seen.setdefault(p, idx)

    # Pick the modes. On ties, prefer the most recently seen.
    # Sort key: (-count, last_seen_index) — higher count wins, then smaller
    # last-seen index (more recent) wins on count tie.
    def best(counts: dict[str, int], last_seen: dict[str, int]) -> tuple[str | None, float]:
        if not counts:
            return (None, 0.0)
        items = sorted(
            counts.items(),
            key=lambda kv: (-kv[1], last_seen.get(kv[0], 999)),
        )
        winner, winning_count = items[0]
        confidence = winning_count / total if total else 0.0
        return (winner, confidence)

    style, style_confidence = best(style_counts, style_last_seen)
    palette, palette_confidence = best(palette_counts, palette_last_seen)

    # If no clear winner (no item exceeds the confidence floor), don't lock.
    if style_confidence < minimum_confidence or palette_confidence < minimum_confidence:
        return (None, None)

    return (style, palette)


def compute_rotation(
    manifest: dict[str, Any],
    platform: PlatformConfig | str,
    post_type: str | None = None,
    locked_style: str | None = None,
    locked_palette: str | None = None,
) -> dict[str, Any]:
    """Run rotation for a specific platform.

    Args:
        manifest: The cross-platform manifest dict (v2 schema).
        platform: PlatformConfig or platform_id string.
        post_type: Optional post-type hint for style recommendation.
        locked_style: If set, force this style (overrides rotation).
                      Used by orchestrator to enforce shared identity.
        locked_palette: If set, force this palette.

    Returns:
        Dict with keys:
            allowed_styles, allowed_palettes, allowed_compositions (per slot),
            forbidden_themes, recommended_style, recommended_palette, notes,
            philosophy (echoes the platform's rotation philosophy).
    """
    if isinstance(platform, str):
        platform = get_platform(platform)

    history = _platform_history(manifest, platform.platform_id)
    notes: list[str] = []
    philosophy = platform.rotation_philosophy

    # ----- Series detection -----
    active_series = _detect_active_series(history)
    if active_series:
        notes.append(
            f"Active series '{active_series}' detected on {platform.display_name}. "
            "Style and palette locked to series identity."
        )
        last_series_entry = history[0] if history else {}
        locked_style = locked_style or last_series_entry.get("style")
        locked_palette = locked_palette or last_series_entry.get("palette_id")

    # ----- Consistency mode (Instagram) -----
    consistency_locked = False
    if philosophy == "consistency" and not locked_style and not locked_palette:
        established_style, established_palette = _established_palette_for_consistency(history)
        if established_style and established_palette:
            notes.append(
                f"{platform.display_name} consistency mode: locking to established "
                f"style '{established_style}' and palette '{established_palette}'."
            )
            locked_style = established_style
            locked_palette = established_palette
            consistency_locked = True

    # ----- Slot list comes from platform -----
    slot_names = [fmt.name for fmt in platform.output_formats]

    # ----- Empty history (first post on this platform) -----
    if not history and not locked_style and not locked_palette:
        notes.append(
            f"First post on {platform.display_name}. All styles, palettes, and "
            "compositions are unconstrained."
        )

        # Apply platform style biases.
        candidate_styles = [s for s in ALL_STYLES if s not in platform.avoided_styles]
        if not candidate_styles:
            candidate_styles = list(ALL_STYLES)

        post_type_prefs = DEFAULT_POST_TYPE_PREFERENCES.get(post_type or "", [])
        recommended_style = _pick_recommendation(
            candidate_styles,
            preferences=[s for s in (post_type_prefs + platform.preferred_styles) if s in candidate_styles],
            fallback_order=platform.preferred_styles or candidate_styles,
        )
        recommended_palette = _pick_recommendation(
            ALL_PALETTES,
            preferences=STYLE_PALETTE_AFFINITY.get(recommended_style or "", []),
            fallback_order=ALL_PALETTES,
        )

        return {
            "platform": platform.platform_id,
            "philosophy": philosophy,
            "allowed_styles": candidate_styles,
            "allowed_palettes": list(ALL_PALETTES),
            "allowed_compositions": {slot: list(ALL_COMPOSITIONS) for slot in slot_names},
            "forbidden_themes": [],
            "recommended_style": recommended_style,
            "recommended_palette": recommended_palette,
            "notes": notes,
            "consistency_locked": consistency_locked,
        }

    # ----- Apply rotation windows -----
    if locked_style:
        allowed_styles = [locked_style] if locked_style in ALL_STYLES else list(ALL_STYLES)
    else:
        used_styles = _recent_field(history, "style", platform.style_window)
        allowed_styles = [
            s for s in ALL_STYLES
            if s not in used_styles and s not in platform.avoided_styles
        ]
        if not allowed_styles:
            # Relax avoided_styles before relaxing the window
            allowed_styles = [s for s in ALL_STYLES if s not in used_styles]
        if not allowed_styles:
            # Last-resort: relax the window
            relaxed_window = max(1, platform.style_window - 1)
            relaxed_used = _recent_field(history, "style", relaxed_window)
            allowed_styles = [s for s in ALL_STYLES if s not in relaxed_used] or list(ALL_STYLES)
            notes.append(f"All styles used within rotation window; relaxed window to {relaxed_window}.")

    if locked_palette:
        allowed_palettes = [locked_palette] if locked_palette in ALL_PALETTES else list(ALL_PALETTES)
    else:
        used_palettes = _recent_field(history, "palette_id", platform.palette_window)
        allowed_palettes = [p for p in ALL_PALETTES if p not in used_palettes]
        if not allowed_palettes:
            relaxed_window = max(1, platform.palette_window - 1)
            relaxed_used = _recent_field(history, "palette_id", relaxed_window)
            allowed_palettes = [p for p in ALL_PALETTES if p not in relaxed_used] or list(ALL_PALETTES)
            notes.append(f"All palettes used within rotation window; relaxed window to {relaxed_window}.")

    # ----- Composition rules (per slot) -----
    allowed_compositions: dict[str, list[str]] = {}
    for slot in slot_names:
        if platform.composition_window <= 0:
            # Some platforms (Instagram in pure consistency) want no rotation
            allowed_compositions[slot] = list(ALL_COMPOSITIONS)
            continue
        used = _recent_composition(history, slot, platform.composition_window)
        allowed = [c for c in ALL_COMPOSITIONS if c not in used]
        if not allowed:
            allowed = list(ALL_COMPOSITIONS)
        allowed_compositions[slot] = allowed

    # ----- Theme exclusions -----
    forbidden_themes = sorted(_recent_themes(history, platform.theme_window))

    # ----- Recommendations -----
    post_type_prefs = DEFAULT_POST_TYPE_PREFERENCES.get(post_type or "", [])
    recommended_style = _pick_recommendation(
        allowed_styles,
        preferences=[s for s in (post_type_prefs + platform.preferred_styles)],
        fallback_order=platform.preferred_styles or allowed_styles,
    )
    recommended_palette = _pick_recommendation(
        allowed_palettes,
        preferences=STYLE_PALETTE_AFFINITY.get(recommended_style or "", []),
        fallback_order=allowed_palettes,
    )

    return {
        "platform": platform.platform_id,
        "philosophy": philosophy,
        "allowed_styles": allowed_styles,
        "allowed_palettes": allowed_palettes,
        "allowed_compositions": allowed_compositions,
        "forbidden_themes": forbidden_themes,
        "recommended_style": recommended_style,
        "recommended_palette": recommended_palette,
        "notes": notes,
        "consistency_locked": consistency_locked,
    }


def compute_shared_identity(
    manifest: dict[str, Any],
    platforms: list[str],
    post_type: str | None = None,
) -> dict[str, Any]:
    """Find ONE style+palette that works for all listed platforms.

    Used by the orchestrator when generating multi-platform images with
    strong coordination. The picked style+palette should:
      - Be in the allowed set for every platform listed
      - Respect each platform's avoided_styles
      - Default to a recommendation that fits all of them

    Returns:
        Dict with keys: style, palette, per_platform_rotations, notes.
    """
    if not platforms:
        raise ValueError("Must specify at least one platform")

    notes: list[str] = []

    # Compute rotation per platform without locks.
    per_platform: dict[str, dict[str, Any]] = {}
    for pid in platforms:
        per_platform[pid] = compute_rotation(manifest, pid, post_type=post_type)

    # Intersect allowed styles across platforms.
    allowed_styles_intersection: set[str] = set(ALL_STYLES)
    for pid, rot in per_platform.items():
        allowed_styles_intersection &= set(rot["allowed_styles"])

    if not allowed_styles_intersection:
        # No style satisfies all platforms (rare). Pick whichever style is allowed
        # for the MOST platforms.
        notes.append(
            "No single style is allowed by all platforms simultaneously. "
            "Picking the style allowed for the most of them."
        )
        score: dict[str, int] = {s: 0 for s in ALL_STYLES}
        for pid, rot in per_platform.items():
            for s in rot["allowed_styles"]:
                score[s] += 1
        best_score = max(score.values())
        allowed_styles_intersection = {s for s, sc in score.items() if sc == best_score}

    # Intersect allowed palettes.
    allowed_palettes_intersection: set[str] = set(ALL_PALETTES)
    for pid, rot in per_platform.items():
        allowed_palettes_intersection &= set(rot["allowed_palettes"])

    if not allowed_palettes_intersection:
        notes.append("No palette allowed by all platforms; relaxing.")
        score = {p: 0 for p in ALL_PALETTES}
        for pid, rot in per_platform.items():
            for p in rot["allowed_palettes"]:
                score[p] += 1
        best_score = max(score.values())
        allowed_palettes_intersection = {p for p, sc in score.items() if sc == best_score}

    # Pick a style. If consistency-mode platforms in the mix, prefer their lock.
    consistency_locks: list[tuple[str, str]] = []
    for pid, rot in per_platform.items():
        if rot.get("consistency_locked"):
            recs = (rot["recommended_style"], rot["recommended_palette"])
            if recs[0] and recs[1]:
                consistency_locks.append(recs)

    if consistency_locks:
        # Use the first consistency-locked platform's identity if it's in the allowed set.
        for s, p in consistency_locks:
            if s in allowed_styles_intersection and p in allowed_palettes_intersection:
                notes.append("Adopted consistency-mode platform's established identity.")
                return {
                    "style": s,
                    "palette": p,
                    "per_platform_rotations": per_platform,
                    "notes": notes,
                }

    # Otherwise: rank intersection by post-type preference, then platform preferences.
    post_type_prefs = DEFAULT_POST_TYPE_PREFERENCES.get(post_type or "", [])
    style = _pick_recommendation(
        sorted(allowed_styles_intersection),
        preferences=post_type_prefs,
        fallback_order=sorted(allowed_styles_intersection),
    )

    palette = _pick_recommendation(
        sorted(allowed_palettes_intersection),
        preferences=STYLE_PALETTE_AFFINITY.get(style or "", []),
        fallback_order=sorted(allowed_palettes_intersection),
    )

    return {
        "style": style,
        "palette": palette,
        "per_platform_rotations": per_platform,
        "notes": notes,
    }
