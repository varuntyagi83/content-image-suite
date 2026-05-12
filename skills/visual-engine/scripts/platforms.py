"""
visual_engine.platforms
=======================

Registry of platform-specific configurations. Each platform defines:
- Its output formats (aspect ratios, slot count, slot names)
- Its rotation philosophy (windows, or "consistency" mode)
- Its style/palette biases
- Its allowed input modes
- Its post-type heuristics for style recommendation

This is the single place where platforms differ. Platform skills are thin
wrappers that load their config from here and delegate to the engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


RotationPhilosophy = Literal["aggressive", "moderate", "light", "consistency"]


@dataclass
class OutputFormat:
    """One output format a platform supports (e.g. Medium hero, LinkedIn carousel slide)."""
    name: str                       # e.g. "hero", "carousel_slide", "story"
    aspect_ratio: str               # e.g. "16:9", "1:1", "9:16"
    width: int                      # pixel width
    height: int                     # pixel height
    is_primary: bool = False        # Is this the default for the platform?
    notes: str = ""                 # Any special handling notes


@dataclass
class PlatformConfig:
    """Full configuration for one platform."""

    platform_id: str                # e.g. "medium", "linkedin"
    display_name: str               # e.g. "Medium", "LinkedIn"

    # Output formats this platform supports
    output_formats: list[OutputFormat] = field(default_factory=list)

    # Rotation philosophy
    rotation_philosophy: RotationPhilosophy = "moderate"
    style_window: int = 3
    palette_window: int = 4
    composition_window: int = 2
    theme_window: int = 3

    # Style biases (recommendation order; not exclusion)
    preferred_styles: list[str] = field(default_factory=list)
    avoided_styles: list[str] = field(default_factory=list)

    # Default aspect ratio when caller doesn't specify
    default_aspect_ratio: str = "16:9"

    # Whether the platform expects long-form content (Medium) or short (Twitter)
    primary_input_mode: Literal["long-form", "short-form", "topic-only", "structured"] = "long-form"

    # For consistency-mode platforms (Instagram), the "lock" radius:
    # how strictly subsequent posts should match the established palette.
    consistency_palette_lock_strength: float = 0.0  # 0 = no lock, 1 = absolute lock

    # Whether this platform tolerates multi-slide outputs (carousels)
    supports_multi_slide: bool = False
    max_slides: int = 1

    # Display advice for prompt building
    mobile_thumbnail_critical: bool = False  # Twitter, Instagram
    text_overlay_friendly: bool = False      # LinkedIn, Meta


# Post-type style preferences (shared across platforms but each can override)
DEFAULT_POST_TYPE_PREFERENCES = {
    "technical": ["isometric", "minimalist", "neon-tech"],
    "essay": ["editorial", "cinematic", "hand-drawn"],
    "personal": ["cinematic", "hand-drawn", "editorial"],
    "opinion": ["editorial", "collage"],
    "ai-future": ["neon-tech", "isometric", "editorial"],
    "listicle": ["retro-print", "minimalist"],
    "cultural": ["collage", "editorial", "retro-print"],
    "tutorial": ["isometric", "minimalist"],
    "comparison": ["minimalist", "isometric", "editorial"],
    "hot-take": ["editorial", "collage", "neon-tech"],
}


# ----------------------------------------------------------------------------
# Platform configurations
# ----------------------------------------------------------------------------


MEDIUM = PlatformConfig(
    platform_id="medium",
    display_name="Medium",
    output_formats=[
        OutputFormat("hero", "16:9", 1920, 1080, is_primary=True,
                     notes="Top of article, sets the tone"),
        OutputFormat("inline_1", "4:3", 1600, 1200,
                     notes="First inline section break"),
        OutputFormat("inline_2", "4:3", 1600, 1200,
                     notes="Second inline section break"),
        OutputFormat("inline_3", "4:3", 1600, 1200,
                     notes="Third inline section break (optional)"),
    ],
    rotation_philosophy="aggressive",
    style_window=3,
    palette_window=4,
    composition_window=2,
    theme_window=3,
    preferred_styles=[
        "editorial", "cinematic", "isometric", "collage",
        "neon-tech", "hand-drawn", "minimalist", "retro-print",
    ],
    avoided_styles=["infographic-modern", "infographic-editorial", "infographic-tech", "infographic-classic"],
    default_aspect_ratio="16:9",
    primary_input_mode="long-form",
    supports_multi_slide=False,
    max_slides=4,  # hero + 3 inline counts as 4 outputs
    mobile_thumbnail_critical=False,
    text_overlay_friendly=False,
)


LINKEDIN = PlatformConfig(
    platform_id="linkedin",
    display_name="LinkedIn",
    output_formats=[
        OutputFormat("cover", "1.91:1", 1200, 627, is_primary=True,
                     notes="Single image cover for text post"),
        OutputFormat("carousel_slide", "1:1", 1080, 1080,
                     notes="Square slide for multi-slide carousel (5-10 slides)"),
    ],
    rotation_philosophy="moderate",
    style_window=2,           # shorter than Medium - LinkedIn moves fast
    palette_window=3,
    composition_window=2,
    theme_window=2,
    preferred_styles=["editorial", "minimalist", "isometric", "neon-tech"],
    avoided_styles=["collage", "infographic-modern", "infographic-editorial", "infographic-tech", "infographic-classic"],   # too busy for LinkedIn feed; infographic styles belong to infographic platform
    default_aspect_ratio="1.91:1",
    primary_input_mode="short-form",
    supports_multi_slide=True,
    max_slides=10,
    mobile_thumbnail_critical=True,    # LinkedIn is mostly mobile
    text_overlay_friendly=True,         # LinkedIn carousels often have text
)


TWITTER = PlatformConfig(
    platform_id="twitter",
    display_name="Twitter/X",
    output_formats=[
        OutputFormat("single", "16:9", 1600, 900, is_primary=True,
                     notes="Single tweet image, 16:9 preview"),
        OutputFormat("thread_card", "1:1", 1080, 1080,
                     notes="Square card for thread anchor tweet"),
    ],
    rotation_philosophy="light",        # Twitter is ephemeral
    style_window=1,                     # only avoid immediate repeat
    palette_window=2,
    composition_window=1,
    theme_window=1,
    preferred_styles=["minimalist", "retro-print", "editorial"],
    avoided_styles=["cinematic", "collage", "infographic-modern", "infographic-editorial", "infographic-tech", "infographic-classic"],   # both lose at thumbnail size; infographic styles for infographic platform
    default_aspect_ratio="16:9",
    primary_input_mode="short-form",
    supports_multi_slide=False,
    max_slides=1,
    mobile_thumbnail_critical=True,
    text_overlay_friendly=False,
)


INSTAGRAM = PlatformConfig(
    platform_id="instagram",
    display_name="Instagram",
    output_formats=[
        OutputFormat("feed", "1:1", 1080, 1080, is_primary=True,
                     notes="Square feed post; the grid is the brand"),
        OutputFormat("story", "9:16", 1080, 1920,
                     notes="Vertical Story or Reel cover"),
        OutputFormat("carousel_slide", "1:1", 1080, 1080,
                     notes="Square slide for carousel (2-10 slides)"),
    ],
    rotation_philosophy="consistency",   # INVERTED: maintain, don't vary
    style_window=0,                       # don't enforce style change
    palette_window=0,                     # don't enforce palette change
    composition_window=1,                 # only compositions vary
    theme_window=2,                       # subjects can vary moderately
    preferred_styles=["cinematic", "editorial", "minimalist", "hand-drawn"],
    avoided_styles=["neon-tech", "retro-print", "infographic-modern", "infographic-editorial", "infographic-tech", "infographic-classic"],   # too jarring for grid coherence; infographic styles for infographic platform
    default_aspect_ratio="1:1",
    primary_input_mode="topic-only",
    supports_multi_slide=True,
    max_slides=10,
    consistency_palette_lock_strength=0.85,   # strong lock to established palette
    mobile_thumbnail_critical=True,
    text_overlay_friendly=False,
)


META = PlatformConfig(
    platform_id="meta",
    display_name="Meta/Facebook",
    output_formats=[
        OutputFormat("feed", "1.91:1", 1200, 630, is_primary=True,
                     notes="Standard FB feed image (matches Open Graph spec)"),
        OutputFormat("event_cover", "1.91:1", 1920, 1005,
                     notes="Event cover image, larger format"),
    ],
    rotation_philosophy="light",
    style_window=1,
    palette_window=2,
    composition_window=1,
    theme_window=1,
    preferred_styles=["minimalist", "editorial", "cinematic"],
    avoided_styles=["infographic-modern", "infographic-editorial", "infographic-tech", "infographic-classic"],   # infographic styles belong to infographic platform
    default_aspect_ratio="1.91:1",
    primary_input_mode="short-form",
    supports_multi_slide=False,
    max_slides=1,
    mobile_thumbnail_critical=False,
    text_overlay_friendly=True,
)


INFOGRAPHIC = PlatformConfig(
    platform_id="infographic",
    display_name="Infographic",
    output_formats=[
        OutputFormat("pinterest_pin", "2:3", 1024, 1536, is_primary=True,
                     notes="Tall pin format. Pinterest, content marketing, "
                           "vertical share. The default infographic format."),
        OutputFormat("square_card", "1:1", 1024, 1024,
                     notes="Square data card. LinkedIn carousel slides, "
                           "dense single-stat callouts, Instagram feed."),
        OutputFormat("landscape_poster", "3:2", 1536, 1024,
                     notes="Wide poster. Blog post embeds, presentation slides, "
                           "horizontal data visualization."),
    ],
    rotation_philosophy="light",       # infographics in a series should LOOK like a series
    style_window=1,                    # only avoid immediate repeat
    palette_window=2,
    composition_window=1,
    theme_window=1,
    # Infographics use a dedicated style family — registered in style_templates/
    preferred_styles=[
        "infographic-modern", "infographic-editorial",
        "infographic-tech", "infographic-classic",
    ],
    # The editorial-illustration styles don't fit infographic conventions —
    # too painterly, not structured enough for data presentation.
    avoided_styles=[
        "cinematic", "hand-drawn", "collage", "neon-tech",
        "retro-print", "editorial", "minimalist", "isometric",
    ],
    default_aspect_ratio="2:3",
    primary_input_mode="structured",   # data points / steps / stats, not narrative
    supports_multi_slide=True,         # an infographic SERIES is common
    max_slides=10,
    mobile_thumbnail_critical=True,    # Pinterest is mobile-first
    text_overlay_friendly=True,        # text IS the content here
    # Infographics with OpenAI need a heavier consistency bias —
    # a 3-pin Pinterest series should share a clear visual identity.
    consistency_palette_lock_strength=0.7,
)


REGISTRY: dict[str, PlatformConfig] = {
    "medium": MEDIUM,
    "linkedin": LINKEDIN,
    "twitter": TWITTER,
    "instagram": INSTAGRAM,
    "meta": META,
    "infographic": INFOGRAPHIC,
}


def get_platform(platform_id: str) -> PlatformConfig:
    """Look up a platform config by id. Raises KeyError if not registered."""
    pid = platform_id.lower().strip()
    # Accept common aliases.
    aliases = {
        "x": "twitter",
        "twitter/x": "twitter",
        "facebook": "meta",
        "fb": "meta",
        "ig": "instagram",
        "insta": "instagram",
        "li": "linkedin",
        "pin": "infographic",
        "pinterest": "infographic",
        "info": "infographic",
        "infographics": "infographic",
    }
    pid = aliases.get(pid, pid)
    if pid not in REGISTRY:
        raise KeyError(f"Unknown platform: {platform_id!r}. Known: {list(REGISTRY.keys())}")
    return REGISTRY[pid]


def all_platforms() -> list[PlatformConfig]:
    """Return all registered platforms in registration order."""
    return list(REGISTRY.values())


def get_format(platform_id: str, format_name: str) -> OutputFormat:
    """Get a specific output format from a platform."""
    config = get_platform(platform_id)
    for fmt in config.output_formats:
        if fmt.name == format_name:
            return fmt
    raise KeyError(
        f"Format {format_name!r} not in platform {platform_id!r}. "
        f"Available: {[f.name for f in config.output_formats]}"
    )
