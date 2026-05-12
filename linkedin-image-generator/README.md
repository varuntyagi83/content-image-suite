# linkedin-image-generator

LinkedIn-specific image generation skill. Two modes: single cover (1.91:1, 1200×627) or multi-slide carousel (1:1, 1080×1080, 5-10 slides). Moderate rotation.

See `SKILL.md` for the full workflow. Requires the `visual-engine` skill.

## What it generates

**Cover mode:** one image at 1200×627 (1.91:1).
**Carousel mode:** 5-10 slides at 1080×1080 (1:1) each, generated one at a time so you can iterate.

## Post-type to style mapping

| Post type | Default style |
|-----------|--------------|
| Tutorial / step-by-step | isometric |
| Comparison / X vs Y | minimalist |
| Hot take | neon-tech or editorial |
| Story / personal | cinematic or editorial |
| Data / metrics | isometric or minimalist |

These are recommendations. User can override.

## When it triggers

- "make me a LinkedIn image"
- "generate a LinkedIn carousel"
- "tutorial carousel for [topic]"
- User shares a LinkedIn post draft

## Mobile-thumbnail awareness

All prompts include a mobile-readability constraint via the engine's `platform_negatives()`. The engine knows LinkedIn is mobile-dominant.
