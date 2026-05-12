"""
visual_engine.prompt_builder
============================

Build a complete Gemini prompt from structured inputs. Loads the relevant
style template, plugs in subject/composition/palette, adds platform-aware
technical specs and negatives.
"""

from __future__ import annotations

import re
from pathlib import Path

from constants import COMPOSITION_PHRASING
from platforms import OutputFormat, PlatformConfig, get_format, get_platform


def load_style_template(style: str, engine_dir: Path) -> str:
    """Load the body of a style template .md file."""
    template_path = engine_dir / "assets" / "style_templates" / f"{style}.md"
    if not template_path.exists():
        raise FileNotFoundError(f"Style template not found: {template_path}")
    return template_path.read_text(encoding="utf-8")


def extract_lead_sentence(template_body: str) -> str:
    """Pull the first 'Reference Phrasing for Gemini' line from a style template.

    Style templates have a section like:
      ## Reference Phrasing for Gemini
      Lead the prompt with one of:
      - "Editorial illustration in the style of..."
      - "..."

    We grab the first quoted line.
    """
    in_section = False
    for line in template_body.splitlines():
        line = line.rstrip()
        if line.startswith("## Reference Phrasing"):
            in_section = True
            continue
        if in_section:
            if line.startswith("##"):
                # Hit next section
                break
            stripped = line.strip()
            if stripped.startswith("- ") and '"' in stripped:
                # Extract the quoted lead.
                start = stripped.find('"')
                end = stripped.rfind('"')
                if start >= 0 and end > start:
                    return stripped[start + 1:end]
    return ""


def load_palette_hex_codes(palette_id: str, engine_dir: Path) -> list[tuple[str, str]]:
    """Parse hex codes for a named palette from references/palettes.md.

    Returns a list of (color_name, hex_code) tuples.
    """
    palettes_path = engine_dir / "references" / "palettes.md"
    if not palettes_path.exists():
        return []

    text = palettes_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    in_palette = False
    colors: list[tuple[str, str]] = []
    for line in lines:
        if line.startswith("##"):
            # Section header. Check if it's our palette.
            in_palette = palette_id in line.lower()
            if not in_palette and colors:
                # We've moved past our palette.
                break
            continue
        if in_palette:
            # Look for lines like: - Cobalt #2C3DD7
            stripped = line.strip()
            if stripped.startswith("- ") and "#" in stripped:
                content = stripped[2:].strip()
                hash_pos = content.find("#")
                name = content[:hash_pos].strip().rstrip(":, ")
                hex_part = content[hash_pos:].split()[0].rstrip(",.")
                if hex_part.startswith("#") and len(hex_part) in (4, 7):
                    colors.append((name, hex_part))
    return colors


def format_palette(colors: list[tuple[str, str]]) -> str:
    """Format palette colors as a Gemini-friendly string."""
    if not colors:
        return ""
    parts = [f"{name.lower()} ({hex_code})" for name, hex_code in colors]
    return "Palette restricted to: " + ", ".join(parts) + "."


def platform_negatives(platform: PlatformConfig) -> str:
    """Get platform-aware negative-prompt string."""
    base = "No text, no logos, no watermarks. Avoid generic stock photo aesthetics. No clichéd AI imagery (glowing brains, blue circuit lines, robot hands typing on keyboards)."
    if platform.mobile_thumbnail_critical:
        base += " Image must remain readable at small mobile thumbnail size."
    return base


# Regex patterns to detect "label-shaped" content in subject strings that
# Gemini may render as visible text on the image.

# Comma-separated capitalized noun phrases like
#   "campaign metrics, competitor intelligence, creative output, reporting"
_LABEL_LIST_PATTERN = re.compile(
    r"(?:\b[A-Z][a-z]+(?:\s+[a-z]+){0,3}\b\s*,\s*){2,}\b[A-Z][a-z]+",
)

# Quoted text. Anything in quotes gets rendered.
_QUOTED_PATTERN = re.compile(r"['\"][^'\"]{2,40}['\"]")

# ALL-CAPS words of length 4+ — Gemini reads these as signage. "INSPIRATION"
# folder, "DRAFTS" archive, "ARCHIVE" stamp, etc. Allows common acronyms (KPI,
# CTA, UI) since those are 2-3 chars.
_ALL_CAPS_WORD_PATTERN = re.compile(r"\b[A-Z]{4,}\b")

# Explicit text-rendering verbs: "a sign that says/reads", "labeled X",
# "with the word X", "marked X", "stamped X", etc.
_TEXT_VERB_PATTERN = re.compile(
    r"\b(?:says|reads|labeled|labelled|titled|inscribed|stamped|marked|written|"
    r"engraved|printed|spelling|spells|displays?)\b",
    re.IGNORECASE,
)

# Time strings like "4:30 AM", "10:15", "9 PM" — Gemini renders clocks legibly.
_TIME_STRING_PATTERN = re.compile(
    r"\b(?:1[0-2]|0?[1-9])(?::[0-5][0-9])?\s*(?:AM|PM|am|pm)\b|"
    r"\b(?:[01]?[0-9]|2[0-3]):[0-5][0-9]\b",
)

# Specific UI element types that invite labels: "the X tab", "X button",
# "the Settings panel". Conservative — matches "[Word] tab|button|menu|panel".
_UI_LABEL_PATTERN = re.compile(
    r"\b[A-Z][a-zA-Z]+\s+(?:tab|button|menu|panel|dropdown|toggle)\b",
)


def detect_label_risk(subject: str) -> tuple[bool, str]:
    """Detect subjects that are likely to cause Gemini to render text in the image.

    Catches:
      1. Comma-separated capitalized phrases ("Campaign Metrics, Reporting, Output")
      2. Quoted text ('a sign that reads "OPEN"')
      3. ALL-CAPS words length 4+ (INSPIRATION, DRAFTS, ARCHIVE — common folder/sign labels)
      4. Explicit text-rendering verbs ("a folder labeled X", "a sign that says Y")
      5. Time strings ("4:30 AM", "10:15", "9 PM" — Gemini renders clocks legibly)
      6. UI element + named label ("the Settings panel", "the Reports tab")
      7. Multiple short comma-separated segments (heuristic catch-all)

    Returns (risk_detected, reason). When True, the prompt should both
    rewrite the subject AND escalate negatives.
    """
    # 1. Comma-separated capitalized noun phrases
    if _LABEL_LIST_PATTERN.search(subject):
        return (True, "comma-separated capitalized phrases")

    # 2. Quoted text
    if _QUOTED_PATTERN.search(subject):
        return (True, "quoted phrases the model may render as visible text")

    # 3. ALL-CAPS words length 4+
    if _ALL_CAPS_WORD_PATTERN.search(subject):
        match = _ALL_CAPS_WORD_PATTERN.search(subject)
        return (True, f"all-caps word '{match.group()}' that the model may render as a sign or label")

    # 4. Explicit text-rendering verbs
    if _TEXT_VERB_PATTERN.search(subject):
        match = _TEXT_VERB_PATTERN.search(subject)
        return (True, f"text-rendering verb '{match.group()}' invites visible text")

    # 5. Time strings
    if _TIME_STRING_PATTERN.search(subject):
        match = _TIME_STRING_PATTERN.search(subject)
        return (True, f"time string '{match.group()}' will be rendered legibly on clocks")

    # 6. UI labels with named tabs/buttons
    if _UI_LABEL_PATTERN.search(subject):
        match = _UI_LABEL_PATTERN.search(subject)
        return (True, f"UI element label '{match.group()}' invites visible text")

    # 7. Multi-segment heuristic
    segments = [s.strip() for s in subject.split(",") if s.strip()]
    if len(segments) >= 3:
        short_label_count = sum(
            1 for s in segments
            if 5 <= len(s) <= 40 and not any(verb in s.lower() for verb in [
                " is ", " are ", " has ", " with ", " of ", " in ", " on ", " at ",
            ])
        )
        if short_label_count >= 3:
            return (True, "multiple short label-like phrases")

    return (False, "")


# Aggressive anti-text negative used when label risk is detected.
STRONG_TEXT_NEGATIVE = (
    "CRITICAL: render zero text, zero letters, zero words, zero captions, "
    "zero labels, zero typography, zero signs, zero readable characters, "
    "zero clock faces with legible numbers, and zero folder labels anywhere "
    "in the image. The image must be purely visual — no written language of "
    "any kind. No annotated diagrams, no UI mockups with labels, no titled "
    "charts. All text-like surfaces (paper, screens, signs, folders) must "
    "show illegible squiggle marks or abstract shapes, never readable text."
)


def rewrite_subject_to_remove_text_cues(subject: str) -> str:
    """Rewrite a subject string to remove cues that invite Gemini to render text.

    Performs these substitutions:
      - ALL-CAPS words → the lowercase word with "unlabeled" or "illegible"
      - Quoted text → "[illegible text]"
      - Time strings on clocks → "an unreadable clock face"
      - "labeled X" → "with an unreadable label"
      - "that says/reads X" → "with illegible text"

    Conservative — only modifies the explicit textual cues, leaves the rest
    of the subject intact.
    """
    rewritten = subject

    # Replace ALL-CAPS labels with their lowercase + "(unlabeled)"
    # e.g. "INSPIRATION folder" → "a folder (label illegible)"
    def replace_caps(match: re.Match) -> str:
        return "(label illegible)"
    rewritten = _ALL_CAPS_WORD_PATTERN.sub(replace_caps, rewritten)

    # Replace quoted strings with [illegible text]
    rewritten = _QUOTED_PATTERN.sub("[illegible text]", rewritten)

    # Replace "that says/reads X" → "with illegible text"
    rewritten = re.sub(
        r"\bthat\s+(?:says|reads|displays?)\s+[^,.]+",
        "with illegible text",
        rewritten,
        flags=re.IGNORECASE,
    )

    # Replace "labeled X" → "with an unreadable label"
    rewritten = re.sub(
        r"\b(?:labeled|labelled|titled|marked|stamped)\s+[A-Za-z][\w\s]{0,30}",
        "with an unreadable label",
        rewritten,
        flags=re.IGNORECASE,
    )

    # Time strings: replace specific times with vague descriptors
    rewritten = re.sub(
        r"\b(?:1[0-2]|0?[1-9])(?::[0-5][0-9])?\s*(?:AM|PM|am|pm)\b",
        "(time of day, clock face illegible)",
        rewritten,
    )
    rewritten = re.sub(
        r"\b(?:[01]?[0-9]|2[0-3]):[0-5][0-9]\b",
        "(clock face illegible)",
        rewritten,
    )

    # Collapse double spaces from substitutions
    rewritten = re.sub(r"\s+", " ", rewritten).strip()

    return rewritten


# Phrases injected into the prompt for protagonist face treatment.
# Each is a short, prescriptive instruction designed to override Gemini's default
# editorial-style face-obscuring tendency.
FACE_TREATMENT_NAMED = (
    "The protagonist's face must be clearly visible with readable features "
    "and a specific expression — three-quarter or front angle, both eyes visible, "
    "stylized but recognizable as a specific person. Do not silhouette, hide, "
    "or turn the figure's face away from the viewer."
)

FACE_TREATMENT_GENERIC = (
    "Figures can be drawn with partial faces, three-quarter turns, or "
    "abstracted features — they represent a role rather than a specific person."
)

# Patterns suggesting the subject describes a specific identifiable person.
# Triggers: age markers, expression descriptions, role-as-person ("founder"),
# personal pronouns embedded in the subject.
_PROTAGONIST_PATTERNS = [
    re.compile(r"\b(?:founder|author|writer|engineer|designer|creator)\b", re.IGNORECASE),
    re.compile(r"\bmid-\d+s?\b|\b(?:early|late)-\d+s?\b|\bin (?:his|her|their) \d+s\b", re.IGNORECASE),
    re.compile(r"\b(?:expression|gaze|stare|focused|thoughtful|laughing|mid-thought|mid-laugh|mid-sentence)\b", re.IGNORECASE),
    re.compile(r"\bspecific (?:person|man|woman|individual)\b", re.IGNORECASE),
]

# Patterns suggesting the subject has no human figure at all.
# When triggered, no face treatment guidance is added.
_NO_FIGURE_PATTERNS = [
    re.compile(r"^[^.]*?\b(?:desk|table|drawer|shelf|wall|landscape|skyline|interface|dashboard|machine|tool|object|device)\b[^.]*$", re.IGNORECASE),
]


def resolve_protagonist_mode(subject: str, mode: str = "auto") -> str:
    """Resolve the protagonist mode for prompt assembly.

    Args:
        subject: The subject string.
        mode: Caller-specified mode. "auto" triggers heuristic detection.
              Other values ("named", "generic", "none") pass through.

    Returns the resolved mode: "named", "generic", or "none".
    """
    if mode in ("named", "generic", "none"):
        return mode
    if mode != "auto":
        return "generic"  # fail safe

    # Auto-detection.
    # First check: does the subject mention a person at all?
    person_words = re.compile(
        r"\b(?:person|man|woman|figure|founder|user|customer|worker|"
        r"marketer|developer|designer|engineer|writer|author|child|teenager|"
        r"someone|individual|she|he|they|her|his|their)\b",
        re.IGNORECASE,
    )
    if not person_words.search(subject):
        # Check the no-figure patterns as a secondary signal.
        if any(p.search(subject) for p in _NO_FIGURE_PATTERNS):
            return "none"
        # Default: no obvious person, assume none.
        return "none"

    # Check protagonist patterns
    for pat in _PROTAGONIST_PATTERNS:
        if pat.search(subject):
            return "named"

    # Person mentioned but no protagonist markers → generic.
    return "generic"


def build_prompt(
    *,
    platform_id: str,
    format_name: str,
    style: str,
    palette_id: str,
    composition: str,
    subject: str,
    engine_dir: Path,
    extra_lighting: str = "",
    custom_negatives: str = "",
    protagonist_mode: str = "auto",
    text_mode: str = "block",
) -> tuple[str, OutputFormat, dict[str, str | bool]]:
    """Build a complete Gemini prompt.

    Args:
        protagonist_mode: One of "named", "generic", "auto", or "none".
            - "named": subject is a specific identifiable person (the author, a
              profiled individual). Prompt asks for a clear, readable face.
            - "generic": subject is anyone/a worker/a user. Face can be obscured.
            - "none": the image has no human figure. No face guidance added.
            - "auto" (default): heuristic detection from the subject string.
        text_mode: One of "block" (default) or "allow".
            - "block": rendered text is unwanted. The label-risk detector
              activates and STRONG_TEXT_NEGATIVE is injected. Used by all
              illustration-platform skills.
            - "allow": rendered text IS the content. Label-risk detection is
              skipped (text in subject is now signal, not bug). No anti-text
              negatives. Used by the infographic skill, paired with the
              OpenAI provider.

    Returns (prompt_text, output_format, metadata) where metadata includes:
      - label_risk_detected: bool — whether the subject triggered label-risk detection
      - label_risk_reason: str — explanation when triggered
      - protagonist_mode_resolved: str — "named", "generic", "none" after auto-resolution
    """
    platform = get_platform(platform_id)
    output_format = get_format(platform_id, format_name)

    # Load style template
    template_body = load_style_template(style, engine_dir)
    style_lead = extract_lead_sentence(template_body)
    if not style_lead:
        style_lead = f"{style.replace('-', ' ').title()} illustration."

    # Load palette colors
    colors = load_palette_hex_codes(palette_id, engine_dir)
    palette_str = format_palette(colors)
    if not palette_str:
        palette_str = f"Palette: {palette_id}."

    # Composition phrasing
    composition_str = COMPOSITION_PHRASING.get(composition, composition.replace("-", " "))

    # Lighting
    lighting = extra_lighting or "Soft directional lighting, considered mood."

    # Aspect ratio + technical specs
    aspect = output_format.aspect_ratio
    if text_mode == "allow":
        # Infographic mode (gpt-image-2 backend). gpt-image-2 has strong text
        # rendering and instruction following. Emphasize:
        #   1. Text legibility — every word must be readable, spelled correctly
        #   2. Visual hierarchy — clear distinction between headline/body/data
        #   3. Layout structure — explicit grid/stack/section organization
        quality_tag = (
            "crisp typography with every word legible and correctly spelled, "
            "clear visual hierarchy with headline size 3-4x body text, "
            "professional infographic quality, structured layout"
        )
    else:
        quality_tag = "high detail, sharp focus, professional editorial quality"

    # Detect and mitigate label-shaped content that Gemini would render as text.
    # When text_mode == "allow" (infographic skill), this is skipped entirely:
    # text in the subject is now signal, not bug, and the rendered text IS the
    # content. The OpenAI provider handles text legibly so anti-text negatives
    # would be actively harmful.
    if text_mode == "allow":
        label_risk = False
        label_reason = ""
        effective_subject = subject
        subject_was_rewritten = False
    else:
        label_risk, label_reason = detect_label_risk(subject)
        effective_subject = subject
        subject_was_rewritten = False
        if label_risk and not custom_negatives:
            # Rewrite the subject to remove explicit textual cues. This is the
            # primary defense — text in the subject is a strong cue Gemini follows
            # despite negatives. The escalated negative is the secondary defense.
            effective_subject = rewrite_subject_to_remove_text_cues(subject)
            subject_was_rewritten = (effective_subject != subject)

    if custom_negatives:
        negatives = custom_negatives
    elif text_mode == "allow":
        # Infographics: no anti-text negatives. Use a permissive baseline
        # that only forbids the truly unwanted (watermarks, photographic
        # imitation when illustrative aesthetics are wanted).
        negatives = ("Avoid watermarks, signatures, AI-generated artifacts. "
                     "Text must be correctly spelled and legible.")
    else:
        negatives = platform_negatives(platform)
        if label_risk:
            # Prepend the strong anti-text negative for additional safety.
            negatives = STRONG_TEXT_NEGATIVE + " " + negatives

    # Resolve protagonist mode for face treatment guidance.
    resolved_mode = resolve_protagonist_mode(effective_subject, protagonist_mode)
    face_hint = ""
    if resolved_mode == "named":
        face_hint = FACE_TREATMENT_NAMED
    elif resolved_mode == "generic":
        face_hint = FACE_TREATMENT_GENERIC
    # "none" -> empty hint, no figure expected

    # Assemble
    parts = [
        f"{style_lead}",
        f"{effective_subject}.",
        f"{composition_str}.",
        palette_str,
        f"{lighting}",
        face_hint,
        f"{aspect} aspect ratio, {quality_tag}.",
        negatives,
    ]
    prompt = " ".join(p.strip() for p in parts if p and p.strip())

    # Light cleanup: collapse double spaces, ensure no trailing period+space issues
    prompt = " ".join(prompt.split())

    metadata: dict[str, str | bool] = {
        "label_risk_detected": label_risk,
        "label_risk_reason": label_reason,
        "subject_was_rewritten": subject_was_rewritten,
        "effective_subject": effective_subject if subject_was_rewritten else "",
        "protagonist_mode_resolved": resolved_mode,
    }
    return prompt, output_format, metadata
