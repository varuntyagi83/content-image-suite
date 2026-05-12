# instagram-image-generator

Instagram image generation. Feed (1:1), Story/Reel cover (9:16), carousel (1:1, 2-10 slides). 

**Inverted rotation philosophy: this skill MAINTAINS visual identity rather than varying it.** After 3 posts with a coherent style+palette, the engine locks to that look. The grid is the brand.

See `SKILL.md` for the full workflow. Requires the `visual-engine` skill.

## What it generates

- Feed: 1080×1080 (1:1) — the default square post
- Story / Reel cover: 1080×1920 (9:16)
- Carousel: 2-10 slides at 1080×1080 each, generated one at a time

## Consistency mode

The unusual part. From the 3rd post onward, the engine looks at your Instagram history, finds the most-used style and palette, and locks subsequent posts to that combination. You get a coherent grid automatically.

If you want to break the lock for a one-off post, just say "different style for this one" — the skill will confirm and proceed.

## Avoided styles

`neon-tech` and `retro-print` are excluded by default — both clash with photographic feed norms on Instagram.

## When it triggers

- "make me an Instagram post"
- "Story for IG"
- "Reel cover for [topic]"
- "Instagram carousel about [topic]"
