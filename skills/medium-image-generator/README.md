# medium-image-generator

Medium-specific image generation skill. Hero (16:9) + inline section images (4:3). Aggressive rotation across styles and palettes (windows 3 and 4 respectively).

See `SKILL.md` for the full workflow. Requires the `visual-engine` skill to be installed in the same `~/.claude/skills/` directory.

## What it generates

- One hero image at 1920×1080 (16:9) for the article cover
- Up to three inline images at 1600×1200 (4:3) for section breaks

## When it triggers

Any of:
- "make me a hero image for Medium"
- "generate a Medium cover for this post"
- "blog visuals for [topic]"
- User shares a Medium draft, file, or URL

## What it produces

Saves images to `<working-dir>/content-images/<slug>/` and records prompts, compositions, and image paths in the shared cross-platform manifest at `<working-dir>/content-images/manifest.json`.
