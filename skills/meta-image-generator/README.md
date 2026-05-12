# meta-image-generator

Meta/Facebook image generation. Feed posts (1.91:1, 1200×630) and event covers (1.91:1, 1920×1005). Light rotation. Text-overlay-friendly compositions favored (Meta tolerates ads/promos better than other platforms).

See `SKILL.md` for the full workflow. Requires the `visual-engine` skill.

## What it generates

- Feed: 1200×630 (1.91:1) — matches Open Graph spec for FB link previews
- Event cover: 1920×1005 (1.91:1) — Facebook event cover spec

## When it triggers

- "make me a Facebook image"
- "Meta post image"
- "FB cover"
- "event cover for [event]"
- "ad creative for Meta"

## Use cases

Most common:
1. **Open Graph previews** when sharing a Medium article on Facebook
2. **Event covers** for Facebook events
3. **Ad creative** for paid Meta campaigns
4. **Cross-posting** with a Meta-sized variant of a Medium hero

For case 4, the skill coordinates with existing Medium imagery via the shared manifest (same style+palette).
