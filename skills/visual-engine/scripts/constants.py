"""
visual_engine.constants
=======================

Shared catalogs of styles, palettes, and compositions. All platform skills
import from here. Adding a new style/palette/composition is centralized.
"""

ALL_STYLES = [
    "editorial",
    "cinematic",
    "isometric",
    "collage",
    "neon-tech",
    "hand-drawn",
    "minimalist",
    "retro-print",
    # Infographic-family styles (used with OpenAI gpt-image provider).
    "infographic-modern",
    "infographic-editorial",
    "infographic-tech",
    "infographic-classic",
]

ALL_PALETTES = [
    "electric-dusk",
    "bone-and-rust",
    "midnight-circuit",
    "sunwashed",
    "monochrome-noir",
    "tropical-ink",
    "paper-and-pencil",
    "terminal-green",
    "soft-laboratory",
    "burnt-poster",
    "velvet-financial",
    "cold-architecture",
]

ALL_COMPOSITIONS = [
    "centered-subject",
    "rule-of-thirds-left",
    "rule-of-thirds-right",
    "overhead-flat-lay",
    "diagonal-motion",
    "worms-eye-view",
    "birds-eye-view",
    "split-frame",
    "silhouette",
    "frame-within-frame",
    "negative-space-dominant",
    "pattern-repetition",
    # Infographic-specific compositions (data-layout, not scene-layout).
    "vertical-stack",
    "grid-2x2",
    "grid-3x1",
    "headline-and-body",
    "dashboard-layout",
    "headline-and-illustration",
    "chart-with-callouts",
    "print-grid",
]

# Style → preferred palettes (used by recommendation engine as tiebreaker).
STYLE_PALETTE_AFFINITY = {
    "editorial": ["bone-and-rust", "paper-and-pencil", "burnt-poster", "velvet-financial"],
    "cinematic": ["monochrome-noir", "electric-dusk", "velvet-financial", "bone-and-rust"],
    "isometric": ["cold-architecture", "electric-dusk", "soft-laboratory", "terminal-green"],
    "collage": ["burnt-poster", "tropical-ink", "sunwashed", "paper-and-pencil"],
    "neon-tech": ["midnight-circuit", "terminal-green", "electric-dusk"],
    "hand-drawn": ["paper-and-pencil", "sunwashed", "bone-and-rust"],
    "minimalist": ["cold-architecture", "monochrome-noir", "soft-laboratory"],
    "retro-print": ["burnt-poster", "tropical-ink", "terminal-green"],
    # Infographic family.
    "infographic-modern": ["cold-architecture", "bone-and-rust", "velvet-financial", "paper-and-pencil"],
    "infographic-editorial": ["bone-and-rust", "velvet-financial", "paper-and-pencil", "burnt-poster"],
    "infographic-tech": ["cold-architecture", "midnight-circuit", "electric-dusk"],
    "infographic-classic": ["bone-and-rust", "paper-and-pencil", "velvet-financial", "monochrome-noir"],
}

# Composition phrasing for Gemini prompts.
COMPOSITION_PHRASING = {
    "centered-subject": "Subject centered in frame, symmetrical balance",
    "rule-of-thirds-left": "Subject in the left third, large negative space on the right",
    "rule-of-thirds-right": "Subject in the right third, large negative space on the left",
    "overhead-flat-lay": "Top-down overhead view, objects arranged on a flat surface",
    "diagonal-motion": "Strong diagonal composition from lower-left to upper-right",
    "worms-eye-view": "Low-angle shot looking up at the subject, dramatic perspective",
    "birds-eye-view": "High-angle shot looking down at the subject",
    "split-frame": "Frame divided vertically with contrasting content on each side",
    "silhouette": "Subject as silhouette against a brightly lit background",
    "frame-within-frame": "Subject viewed through a doorway, window, or screen",
    "negative-space-dominant": "Tiny subject, vast empty space dominating the composition",
    "pattern-repetition": "Repeating pattern of similar motifs filling the frame",
    # Infographic-specific.
    "vertical-stack": "Vertical stack of sections from top to bottom, each clearly separated",
    "grid-2x2": "Four sections arranged in a 2x2 grid, equal weight",
    "grid-3x1": "Three sections arranged vertically (or in a single column), equal weight",
    "headline-and-body": "Large headline at top, body content (chart or text blocks) below",
    "dashboard-layout": "Dashboard-style layout with KPI cards arranged like a product UI",
    "headline-and-illustration": "Serif headline at top, supporting illustration in the lower portion, integrated data callouts",
    "chart-with-callouts": "Large central chart with annotated callouts pointing to specific data points",
    "print-grid": "Rigorous typographic grid in the print-design tradition, horizontal rules separating sections",
}

# Schema version of the cross-platform manifest.
SCHEMA_VERSION = 2
