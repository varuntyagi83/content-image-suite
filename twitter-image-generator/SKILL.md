---
name: twitter-image-generator
description: Generate single tweet images and thread cards for Twitter/X using Gemini Nano Banana Pro. Triggers on phrases like "make me a tweet image", "Twitter card for this thread", "X image for this post", "image for my tweet thread", or whenever a user asks for visuals tied to Twitter or X. Single-image (16:9) and thread-anchor (1:1) supported. Mobile-thumbnail-critical: prompts optimized for small-screen readability. Light rotation (Twitter is ephemeral). Part of the Content Image Suite, uses the shared visual-engine.
---

# Twitter/X Image Generator

Twitter is ephemeral and mobile-first. The skill leans toward simple, high-contrast visuals that work at thumbnail size. Rotation is light (style window 1, palette 2, theme 1) — the Twitter feed forgets fast.

## Output formats

- `single` — 16:9 (1600×900), the default for a tweet with one image
- `thread_card` — 1:1 (1080×1080), the anchor image of a multi-tweet thread

## Style biases

LinkedIn-friendly styles often look bad at thumbnail size. Twitter prefers:

| Style | Why |
|-------|-----|
| `minimalist` ✓✓ | Reads at any size, perfect for Twitter |
| `retro-print` ✓ | Bold flat shapes, halftone visible |
| `editorial` ✓ | Painterly works if subject is large |
| `cinematic` ✗ | Loses on 200×112 thumbnail |
| `collage` ✗ | Too detailed for small size |
| `neon-tech` ✓ | Strong silhouettes, high contrast |
| `hand-drawn` ✓ | Loose lines hold up |
| `isometric` ✓ | Geometric clarity helps |

The engine excludes `cinematic` and `collage` by default for Twitter. User can override.


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

Twitter inputs are short by definition:

| Form | What to do |
|------|-----------|
| A single tweet (under 280 chars) | The tweet IS the entire input. Treat it as a thesis statement. |
| A thread outline (numbered points) | Use the first tweet as the hook; the image illustrates the hook. |
| A topic + intent ("a tweet about X") | Ask: "What's the actual line you'd tweet? One sentence." |
| Just a topic | Ask the same. Don't try to generate from a topic alone. |

The image always anchors the tweet/thread, never decorates it. Small inputs → simple subjects.

### Step 3: Cross-session linking

Same as other platforms — fuzzy match the manifest. If the user says "for the same thing as my Medium post," look up that Medium post and lock to its `shared_identity`.

### Step 4: Subject extraction

Same protocol as Medium. The constraint: the subject must be **renderable at thumbnail size**. If your extracted subject involves fine details ("a hand holding a magnifying glass to a small map"), simplify ("a magnifying glass over a map, large in frame").

### Step 5: Run rotation

```bash
python <engine>/engine.py rotate \
  --manifest <working-dir>/content-images/manifest.json \
  --platform twitter \
  --post-type <type>
  [--locked-style ...] [--locked-palette ...]
```

Twitter's `style_window=1` means only the most recent Twitter image is excluded — repetition over more posts is fine.

### Step 6: Mode

- Single image (default): `--format single` at 16:9.
- Thread card: `--format thread_card` at 1:1.

If unclear, ask: "Single image (16:9) or thread anchor card (1:1)?"

### Step 7: Build prompt

```bash
python <engine>/engine.py build-prompt \
  --platform twitter --format single \
  --style <picked> --palette <picked> \
  --composition <picked> \
  --subject "<extracted subject>"
```

The engine automatically adds Twitter's mobile-thumbnail-readability constraint to negatives.

### Step 8: Generate

```bash
python <engine>/engine.py generate \
  --prompt "<the prompt>" \
  --aspect <16:9 or 1:1> \
  --output <working-dir>/content-images/<slug>/twitter_<format>.png
```

**Handle three response statuses:**
- `"status": "ok"` → proceed to show + ask.
- `"status": "file_exists"` (exit 4) → ask user: "Already generated this on `<modified_at>`. Use it, or regenerate?" Regenerate = same command with `--overwrite`.
- `"status": "error"` → translate per the Error code translation section.

### Step 9: Show + ask

Show the image with one short summary line above it. Ask:
> "That works at thumbnail size? Or tweak it?"

### Step 10: Iteration

Same vocabulary as other platforms. Twitter-specific tweaks:

- *"Won't read at thumbnail"* / *"Too small/detailed"* → simplify subject, increase contrast, switch to `minimalist` or `retro-print` style if not already
- *"Too generic"* → add specificity to the subject (uncommon prop, distinct posture)
- *"More punchy"* → switch to high-contrast palette (`monochrome-noir`, `midnight-circuit`)

### Step 11: Save manifest

Single mode:

```bash
python <engine>/engine.py manifest add-output \
  --manifest <working-dir>/content-images/manifest.json \
  --slug "<slug>" --platform twitter --format single \
  --compositions "single=<comp>" \
  --prompts "single=<prompt>" \
  --image-paths "single=<path>"
```

End with: *"Saved. Ready to upload."*

## Multi-tweet thread special case

If the user says "make a card for the start of this thread, and one image per tweet," that's NOT what this skill is for. Tell them: "Twitter doesn't really support multi-image threads where each tweet has a different image — you can attach up to 4 images to a single tweet. Want me to do a thread card (1 image) plus a 4-image grid?"

If they confirm, generate one thread_card + up to 4 single-format images, varying compositions. Save them as `thread_card`, `tweet_1`, `tweet_2`, ... in the platform output.

## Invisible machinery

Same rules as Medium: never expose manifest, rotation, JSON, engine, or tracebacks.




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
