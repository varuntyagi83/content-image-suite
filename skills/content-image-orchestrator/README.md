# content-image-orchestrator

The OPTIONAL top-level skill for multi-platform image generation. When you want images for the same article across Medium + LinkedIn + Twitter + Instagram + Meta with coordinated visual identity, the orchestrator runs the planning once and delegates execution to each platform skill.

See `SKILL.md` for the full workflow. Requires the `visual-engine` skill. Works best alongside the five platform skills, but the orchestrator gracefully degrades — if you only have LinkedIn installed, it'll just generate the LinkedIn image.

## What it does

1. Reads your source content once (paste, file, URL, or outline)
2. Extracts the visual subject once
3. Picks one style + one palette that works for all chosen platforms (strong coordination)
4. Walks through each platform in sequence, generating and iterating
5. Saves everything to one shared cross-platform manifest

## When it triggers

Phrases that name 2+ platforms:
- "make images for this post on Medium and LinkedIn"
- "I need a hero and a Twitter card and an IG post for this article"
- "image set for all platforms"

## When to skip it

- Only one platform → use that platform's skill directly
- You want different styles per platform → use platform skills individually
- Iterating on an already-generated image → the platform skill handles iteration

## Cross-session linking

If you generate Medium images today and ask for LinkedIn images three days later for the same article, the orchestrator (or the LinkedIn skill alone) finds the existing piece in the manifest via fuzzy title+slug match and locks the LinkedIn images to the established style+palette.

This works even if you express the article slightly differently the second time. The fuzzy match threshold defaults to 0.80 (SequenceMatcher ratio).
