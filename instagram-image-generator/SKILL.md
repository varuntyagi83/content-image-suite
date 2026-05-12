---
name: instagram-image-generator
description: Generate Instagram feed posts (1:1), Stories/Reels (9:16), and carousels using Gemini Nano Banana Pro. Triggers on phrases like "make me an Instagram image", "generate an Instagram post", "Story for IG", "carousel for Instagram", or whenever a user asks for visuals tied specifically to Instagram. Uses INVERTED rotation philosophy compared to other platforms — maintains visual consistency across the feed grid rather than varying each post. Once an established style+palette emerges, future posts lock to it. Part of the Content Image Suite, uses the shared visual-engine.
---

# Instagram Image Generator

**Instagram is unique: the grid IS the brand.** Other platforms reward variety; Instagram rewards consistency. Once you have an established visual identity (3+ posts in similar style/palette), the engine locks to that identity for future posts. Compositions and subjects vary, but the look stays coherent.

This is called "consistency mode" in the engine, opposite to the "aggressive rotation" of Medium.

## Output formats

- `feed` — 1:1 (1080×1080), the standard square feed post
- `story` — 9:16 (1080×1920), Stories or Reel cover
- `carousel_slide` — 1:1 (1080×1080), one slide of a multi-slide carousel (2-10 slides)

## Style biases

Instagram favors visually rich, polished images:

| Style | Why |
|-------|-----|
| `cinematic` ✓✓ | The default: photographic, mood-driven |
| `editorial` ✓✓ | Magazine aesthetic fits IG |
| `minimalist` ✓ | Strong on a coherent grid |
| `hand-drawn` ✓ | Works for personal brands |
| `isometric` ✓ | Tech accounts |
| `collage` ✓ | Niche but works |
| `neon-tech` ✗ | Avoided: too jarring for grid coherence |
| `retro-print` ✗ | Avoided: clashes with photographic feed norms |

## Consistency mode (the key difference)

When the manifest has 3+ Instagram posts using a similar style+palette, the engine "locks" to that identity. Subsequent posts get the same style+palette automatically — the user doesn't have to think about it.

The engine reports this in its rotation output as `consistency_locked: true`. When you see this:

1. Don't ask the user about style or palette — they've already established one.
2. Vary only composition and subject.
3. If the user says "I want a different style for this one," confirm: "That'll break your grid look. Sure?" If they confirm, treat as a one-time override and add to notes.

Before 3 posts, the engine operates normally (first-post logic for posts 1-2). Tell the user explicitly on post 1: "You're starting fresh on Instagram. From your 3rd post onward, I'll lock to whatever look you've established."


## First-person detection (do this BEFORE subject extraction)

If the post text uses "I", "my", or other first-person markers in the opening paragraph, OR profiles a specific named person, treat it as a **named protagonist** post.

For named protagonist posts:
- The extracted subject MUST describe the narrator/protagonist with age, expression, and identifying details (e.g. "a founder, mid-30s, focused expression at a desk"). Not "a marketer at a desk."
- Pass `--protagonist-mode named` to `build-prompt`.

For conceptual/third-person posts:
- Subject can be a scene, object, or generic figure.
- Pass `--protagonist-mode generic` if a person appears, or `--protagonist-mode none` if the image is pure object/scene. Or omit and let auto-detection decide.

This decision changes whether Gemini renders a recognizable face or defaults to editorial-style face-obscuring. Get it right or the figure will read as anonymous.


## Workflow

### Step 1: Engine

`<engine>` at `~/.claude/skills/visual-engine/scripts/engine.py`.

## Path check (once per session, before first generation)

```bash
python <engine> path-check --manifest <working-dir>/content-images/manifest.json
```

If response has `"suspicious": true`, tell the user once:
> Saving images to `<full path>`. That's `<reason>`. Different location? Tell me a path, or say "ok" to use this one.

Wait for confirmation. If `"suspicious": false`, proceed silently.


### Step 2: Identify input

Instagram inputs are often vague ("a vibe"), unlike Medium drafts:

| Form | What to do |
|------|-----------|
| A caption text | Use as the spine; extract subject from caption tone |
| A topic / vibe ("morning routines", "tech criticism") | Treat as topic-only mode; ask one clarifying question |
| A photo / mood reference | Ask user to describe what they want; don't try to imitate uploaded references unless explicitly asked |
| A long-form article URL | Fetch the article, treat like Medium but output 1:1 instead of 16:9 |

If unclear, ask: "What's the post about? One sentence." Don't proceed with vague subjects on Instagram — vague generates beige.

### Step 3: Cross-session linking + format mode

Two questions to resolve before generating:

**Mode**: feed, story, carousel?

If the user said "Instagram" without specifying, ask: "Feed (1:1), Story (9:16), or carousel?"

**Carousel slide count**: if carousel, ask "How many slides? (2-10)"

### Step 4: Run rotation

```bash
python <engine>/engine.py rotate \
  --manifest <working-dir>/content-images/manifest.json \
  --platform instagram \
  --post-type <type>
```

Look at the response:
- `consistency_locked: true` → engine has found an established identity. Use `recommended_style` + `recommended_palette` without asking.
- `consistency_locked: false` AND `notes` mentions "First post" → first post; pick freely from biased styles.
- `consistency_locked: false` AND there are 1-2 posts → second-or-third post phase. Pick something coherent with what exists.

### Step 5: Subject extraction

For Instagram, subjects should be visually rich and concrete. The protocol from `subject-extraction.md` applies, but lean toward:
- Specific scenes with environmental detail
- People doing something specific (not just standing)
- Strong sensory cues (lighting, weather, time of day)

Avoid: abstract metaphors that worked on Medium will look weak on Instagram.

### Step 6a: Feed mode workflow

**For every generation in this skill (feed, story, or carousel slide), handle three response statuses from `python <engine> generate`:**
- `"status": "ok"` → proceed to show + ask.
- `"status": "file_exists"` (exit 4) → ask user: "Already generated this on `<modified_at>`. Use it, or regenerate?" Regenerate = same command with `--overwrite`.
- `"status": "error"` → translate per the Error code translation section.

This applies equally to feed, story, and each carousel slide.

1. Pick composition from `allowed_compositions["feed"]`.
2. Build prompt: `--platform instagram --format feed`.
3. Generate at 1:1.
4. Show + ask: "Fits your feed? Or tweak it?"
5. Iterate.
6. Save to manifest with `format: feed`.

### Step 6b: Story mode workflow

1. Pick composition that works in tall 9:16 (favor `centered-subject`, `negative-space-dominant`, `worms-eye-view`).
2. Build prompt: `--platform instagram --format story`.
3. Generate at 9:16.
4. Show + ask.
5. Save with `format: story`.

Stories often have text overlays the user adds later in Instagram's editor. Tell the user: "I'll leave the top and bottom of the frame less busy so you can add text later."

### Step 6c: Carousel mode workflow

Like LinkedIn carousels but Instagram-specific:

1. **Pick ONE style + ONE palette** for all slides (visual coherence is even more important on IG than LinkedIn).
2. **Plan slide structure** — but unlike LinkedIn, IG carousels often have less didactic structure. Common pattern: hook → 3-7 elaborations → payoff.
3. **Vary compositions** but more subtly than LinkedIn (the grid context wants flow, not contrast).
4. **Generate one slide at a time** with feedback in between.

### Step 7: Show output

Show one short summary line, the image, and one feedback question. For consistency-locked generation, the summary line can mention coherence:
> "Maintaining your established cinematic + monochrome-noir look. Slide 1 ready."

This is the only place the skill mentions the consistency mechanic — it's a positive signal to the user that their grid is staying coherent.

### Step 8: Iteration

Standard vocabulary plus IG-specific:

- *"Doesn't fit my grid"* → re-run rotation; the engine should already be locking, but if not, consult `<engine>/references/iteration-vocabulary.md` and ask "Want to break the grid look or stay coherent?"
- *"Too clean"* / *"Too messy"* → texture/clutter tweak
- *"Different palette for this one only"* → user override, add to notes, generate
- *"Make the next 3 posts use this same style"* → normal IG behavior, no special action needed (the engine will lock automatically)

### Step 9: Save manifest

Mirror the Medium pattern but with format-specific slot names:

Feed:
```bash
--compositions "feed=<comp>" --prompts "feed=<prompt>" --image-paths "feed=<path>"
```

Story:
```bash
--compositions "story=<comp>" --prompts "story=<prompt>" --image-paths "story=<path>"
```

Carousel:
```bash
--compositions "slide_1=...|||slide_2=...|||..." \
--prompts "slide_1=...|||slide_2=...|||..." \
--image-paths "slide_1=...|||slide_2=...|||..."
```

End with: *"Saved. Your feed will stay coherent."* (Or just "Saved." if not consistency-locked yet.)

## Reels covers

When the user says "Reel" they usually mean the cover image — the visual frame Instagram shows when the Reel isn't playing. Treat this exactly like a Story (9:16) with one extra rule: the subject should be readable as a single still image even though the actual content is video.

If the user is asking for *Reel content* (animated video frames), this skill can't do that. Tell them: "I generate still images. For animated Reels you'd need a video tool. Want me to do the Reel cover instead?"

## Invisible machinery

Same rules as Medium. The user never sees "consistency_locked", "schema", or any technical term. When the engine locks to an established identity, surface it as: "Sticking with your usual cinematic + monochrome look so your grid stays coherent."




## Protagonist mode (build-prompt)

When building prompts, pass `--protagonist-mode` based on the source post:
- `named` — first-person posts, named profiles, personal essays where the author/subject is central. Triggers the engine to add face-clarity guidance.
- `generic` — posts featuring "a user," "a customer," "workers" without a specific identity. Faces can be obscured by editorial convention.
- `none` — pure object/scene images with no human figure.
- `auto` (default) — heuristic detection from the subject string.

For named-protagonist posts, also write the subject explicitly: include age range, expression, and an identifying gesture ("a founder, mid-30s, focused expression" not "a marketer"). The face-guidance directive in the prompt depends on the subject naming a person.

The build-prompt response includes `protagonist_mode_resolved` — if it shows "named", the prompt now requests a clear visible face.

## Label-risk handling (applies to every build-prompt call)

`build-prompt` returns two fields: `label_risk_detected` (bool) and `label_risk_reason` (str).

When `label_risk_detected: true` — the subject has label-shaped phrasing (comma-separated capitalized phrases, quoted text, or multiple short label-like segments) that Gemini will likely render as visible text. The engine has already prepended an aggressive no-text negative.

Mention this casually to the user once per session:
> Heads up: your subject has label-like phrasing, so I added a strong no-text negative. If text leaks anyway, we can rephrase — see the visual proxies section in `subject-extraction.md`.

Then proceed. If text still appears in the generated image, the fix is on the subject side: rephrase the labels as a continuous scene or use visual proxies.


## Text detection (post-generation safety net)

Every successful `generate` response includes a `text_detection` field with:
- `passed` (bool) — true if OCR found no rendered text
- `words_found` (list) — what words OCR detected, if any
- `status` — "ok", "text_detected", or "ocr_unavailable"

When `passed: false`, the image likely has rendered text (a clock face, a folder label, a sign). Surface to the user:
> OCR detected text in this image: `<words>`. Want me to regenerate with a stronger no-text directive?

If user agrees, re-run `generate` with `--overwrite`. The engine will apply more aggressive subject rewriting on the retry.

When `status: ocr_unavailable`, the user does not have tesseract installed. Do not flag this — proceed silently. Only mention if user explicitly asks why text was not caught:
> The OCR safety net needs tesseract. `brew install tesseract && pip install pytesseract pillow` enables it.

## Error code translation

The engine returns structured errors. Translate them for the user:
- `rate_limit` → "fal.ai is busy, retrying in 5 seconds"
- `policy_violation` → "Gemini rejected the prompt. Want to rephrase the subject?"
- `auth` / `fal_key_missing` → "fal.ai isn't accepting the key — check `FAL_KEY`"
- `network` → "Couldn't reach fal.ai — check your connection"
- `download_failed` → "Generated, but the download failed. Retry?"
- anything else → quote briefly, offer retry
