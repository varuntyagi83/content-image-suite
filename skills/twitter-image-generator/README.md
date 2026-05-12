# twitter-image-generator

Twitter/X image generation. Single tweet image (16:9) or thread anchor card (1:1). Light rotation. Mobile-thumbnail-critical (the engine adjusts negatives accordingly).

See `SKILL.md` for the full workflow. Requires the `visual-engine` skill.

## What it generates

- Single image: 1600×900 (16:9), the default for a tweet with one image
- Thread card: 1080×1080 (1:1), the anchor of a multi-tweet thread

## When it triggers

- "make me a tweet image"
- "Twitter card for [topic]"
- "X image for this thread"

## Avoided styles

`cinematic` and `collage` are excluded by default — both lose at thumbnail size on Twitter. User can override.

## What you get

A single image (or a thread card + up to 4 grid images for a multi-image tweet). Saved to `<working-dir>/content-images/<slug>/twitter_<format>.png`.
