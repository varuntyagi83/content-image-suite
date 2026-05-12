---
name: meta-image-generator
description: Generate images for Meta/Facebook posts, ads, and event covers using Gemini Nano Banana Pro. Triggers on phrases like "make me a Facebook image", "Meta post image", "FB cover", "ad creative for Meta", "event cover for Facebook", or whenever a user asks for visuals tied specifically to Facebook or Meta. Two formats: feed (1.91:1) for posts and ads, event cover (1.91:1, larger) for FB events. Light rotation. Tolerates text-overlay-friendly compositions. Part of the Content Image Suite, uses the shared visual-engine.
---

# Meta/Facebook Image Generator

Meta is mostly Twitter-but-bigger: heterogeneous feeds, less profile coherence, more tolerance for conventional aesthetics. The skill produces feed images and event covers. Light rotation. Often used for ads/promos, so text-overlay-friendly compositions are favored.

## Output formats

- `feed` — 1.91:1 (1200×630), the standard Facebook feed image (matches Open Graph spec for link previews)
- `event_cover` — 1.91:1 (1920×1005), Facebook event cover image (larger format)

## Style biases

| Style | Why |
|-------|-----|
| `minimalist` ✓✓ | Default for posts/ads — clean, professional |
| `editorial` ✓ | Works for organic content |
| `cinematic` ✓ | Works for event covers (mood-driven) |
| `isometric` ✓ | Works for tutorial/educational content |
| Other styles | Fine, no strong avoidance |

## When this skill is most used

Meta is rarely the primary platform anymore. Most usage falls into:

1. **Open Graph link previews** — when sharing a Medium article or other URL on Facebook, the linked image becomes the preview. The user might want a specific Meta-friendly version.
2. **Event covers** — Facebook events still need cover images.
3. **Ad creative** — paid promotional images.
4. **Cross-posting** from another platform — the user has a Medium hero and wants a Meta-sized variant.

For case 4, prefer to coordinate with the Medium image (same style+palette) — same as the orchestrator would do.


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


### Step 2: Identify input + mode

Inputs are usually one of:

| Form | Mode | What to do |
|------|------|-----------|
| Post text or article URL | feed | Treat like Twitter input |
| Event description | event_cover | Pull date, location, theme from description |
| Ad copy + product/service | feed | Stronger pull toward `minimalist` and text-overlay-friendly compositions |

If unclear, ask: "Feed image or event cover?"

### Step 3: Cross-session linking

Same as other platforms.

If the user says "the Facebook version of my Medium post," explicitly look up the Medium piece in the manifest and lock to its `shared_identity`.

### Step 4: Subject extraction

Standard protocol. For ad/event covers, the subject often needs to leave space for text overlays. Add this constraint to the prompt:
- For event covers: prefer `negative-space-dominant` or `rule-of-thirds-left/right` so the user can overlay event title/date.
- For ads: similar — keep one half of the frame relatively clean.

### Step 5: Run rotation

```bash
python <engine>/engine.py rotate \
  --manifest <working-dir>/content-images/manifest.json \
  --platform meta \
  --post-type <type>
```

Light rotation (windows of 1-2). Mostly avoids exact-repeat with the previous Meta post.

### Step 6: Build prompt

```bash
python <engine>/engine.py build-prompt \
  --platform meta --format <feed|event_cover> \
  --style <picked> --palette <picked> \
  --composition <picked> \
  --subject "<extracted subject>" \
  --negatives "Standard negatives. Leave one third of frame visually clear for text overlay."
```

The custom negatives are the Meta-specific addition.

### Step 7: Generate

```bash
python <engine>/engine.py generate \
  --prompt "<...>" \
  --aspect 1.91:1 \
  --output <working-dir>/content-images/<slug>/meta_<format>.png
```

**Handle three response statuses:**
- `"status": "ok"` → proceed to show + ask.
- `"status": "file_exists"` (exit 4) → ask user: "Already generated this on `<modified_at>`. Use it, or regenerate?" Regenerate = same command with `--overwrite`.
- `"status": "error"` → translate per the Error code translation section.

### Step 8: Show + ask

Standard one-line summary + image + feedback question. For event covers, include a hint:
> "Event cover ready. Left third is clear for your event title and date."

### Step 9: Iteration

Standard vocabulary. Meta-specific tweaks:
- *"Need more space for text"* → switch to `negative-space-dominant` composition or simplify subject
- *"Looks like an ad"* → user wants organic feel; switch from `minimalist` to `editorial` or `cinematic`
- *"Doesn't look like an ad enough"* → switch toward `minimalist` with high contrast palette

### Step 10: Save manifest

```bash
python <engine>/engine.py manifest add-output \
  --manifest <working-dir>/content-images/manifest.json \
  --slug "<slug>" --platform meta --format <feed|event_cover> \
  --compositions "<format>=<comp>" \
  --prompts "<format>=<prompt>" \
  --image-paths "<format>=<path>"
```

End with: *"Saved."*

## Invisible machinery

Same rules as all other platform skills.




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
