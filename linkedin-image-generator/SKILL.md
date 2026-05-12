---
name: linkedin-image-generator
description: Generate LinkedIn images — single covers (1.91:1) or multi-slide carousels (1:1, 5-10 slides). Triggers on "LinkedIn image", "LinkedIn carousel", "image for my LinkedIn post", "tutorial carousel from this article", or when a user shares a LinkedIn post draft. Maps post types — Tutorial/step-by-step → isometric carousel, Comparison/X vs Y → minimalist, Hot take → neon-tech or editorial. Mobile-thumbnail-aware. Uses the shared visual-engine.
---

# LinkedIn Image Generator

LinkedIn output: a single cover OR a multi-slide carousel. Both modes use the same shared engine.

## Formats

- `cover` — 1.91:1 (1200×627), default for single-image posts. The engine generates at 16:9 (closest supported by fal.ai) and the LinkedIn preview crops slightly.
- `carousel_slide` — 1:1 (1080×1080), one slide of a 5-10 slide carousel.

## Post-type → style defaults

Recommendations, not constraints. User preference wins.

| Post type | Default style |
|---|---|
| Tutorial / step-by-step | `isometric` |
| Comparison / X vs Y | `minimalist` |
| Hot take / opinion | `editorial` or `neon-tech` |
| Story / personal | `cinematic` or `editorial` |
| Data / metrics | `isometric` or `minimalist` |

`collage` is excluded by default (too busy at LinkedIn feed size). User can override.

## Engine path

`<engine>` = `~/.claude/skills/visual-engine/scripts/engine.py`

## Path check (once per session, before first generation)

```bash
python <engine> path-check --manifest <working-dir>/content-images/manifest.json
```

If response has `"suspicious": true`, tell the user once:
> Saving images to `<full path>`. That's `<reason>`. Different location? Tell me a path, or say "ok" to use this one.

Wait for confirmation. If `"suspicious": false`, proceed silently.

`<manifest>` = `<working-dir>/content-images/manifest.json`


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

### 1. Mode: cover or carousel?

If the user said "carousel" explicitly: carousel mode.
If they said "cover": cover mode.
Otherwise ask once: "Single cover (1.91:1) or carousel (5-10 slides)?"

For carousel mode, also ask: "How many slides?" (default 6).

### 2. Identify input

| Form | What to do |
|---|---|
| Pasted post text (300-1500 words) | Read inline |
| Article URL the post summarizes | `web_fetch`, treat as the source |
| Bulleted slide outline (carousel) | Use each bullet as one slide |
| Hot take / single thesis | Treat as the spine; you'll expand it visually |
| Topic only (carousel mode) | Ask user to outline the slides briefly first |

### 3. Cross-session linking

```bash
python <engine> manifest find --manifest <manifest> \
  --title "<title>" --slug "<slugified>" --threshold 0.80
```

If matched and `shared_identity` is set, that's your locked style+palette.

### 4. Extract subject

Apply `<engine_dir>/references/subject-extraction.md`. For carousels, the subject from this step anchors **slide 1**. Other slides depict different aspects of the same content.

### 5. Run rotation

```bash
python <engine> rotate --manifest <manifest> --platform linkedin \
  --post-type <tutorial|comparison|hot-take|personal|data> \
  [--locked-style ...] [--locked-palette ...]
```

Window 2 styles / 3 palettes. Moderate rotation.

### 6. Cover mode

a) Pick composition from `allowed_compositions[cover]`.

b) Build prompt:
```bash
python <engine> build-prompt --platform linkedin --format cover \
  --style <picked> --palette <picked> \
  --composition <comp> --subject "<subject>"
```

c) Generate:
```bash
python <engine> generate --prompt "<...>" --aspect 1.91:1 \
  --output <working-dir>/content-images/<slug>/linkedin_cover.png
```

**Handle three response statuses:**
- `"status": "ok"` → image generated, proceed to show + ask.
- `"status": "file_exists"` (exit 4) — output already exists. Ask:
  > Already generated this on `<modified_at>`. Use that one, or regenerate?

  Use existing → proceed to show + ask. Regenerate → re-run with `--overwrite`.
- `"status": "error"` → translate per the Error code translation section below.

The engine remaps 1.91:1 → 16:9 (LinkedIn previews crop). Mention casually if the user asks.

d) Show one summary line + image + ask:
> Cover ready. Tweak, or call it done?

e) On approval, save:
```bash
python <engine> manifest add-output --manifest <manifest> \
  --slug <slug> --platform linkedin --format cover \
  --compositions "cover=<comp>" \
  --prompts "cover=<full prompt>" \
  --image-paths "cover=<path>"
```

### 7. Carousel mode

a) Pick ONE style + ONE palette for the entire carousel (visual coherence matters more here than for single covers).

b) Plan the slide structure internally — don't narrate it to the user:
- Slide 1: hook / question / promise
- Slide 2: setup / context
- Slides 3 through N-1: the content (steps, comparison points, argument beats)
- Slide N: payoff / takeaway / CTA

c) For each slide, pick a different composition. Order suggestion:
- Slide 1: `centered-subject` or `negative-space-dominant` (stopping power)
- Slide 2: `rule-of-thirds-left` or `split-frame`
- Middle slides: vary across remaining compositions
- Last slide: `centered-subject` (anchor the takeaway)

d) For each slide, pick a different subject focus — that slide's specific content, not a repeat of slide 1.

e) Generate slides ONE AT A TIME, not in a batch. After each slide:
> Slide 1/6 ready: <one-line summary>. Continue, tweak this slide, or stop?

This is intentional — carousels are expensive to regenerate if you only spot the issue after slide 10.

f) Iteration vocabulary additions for carousels:
- "More variation" → re-pick compositions to maximize differences between slides
- "Add a slide between 3 and 4" → insert, renumber
- "Remove slide 5" → drop, renumber
- "Reorder them" → ask which order
- "All slides need to be more [adjective]" → apply globally; regenerate every slide

g) On all-slides-approved, save:
```bash
python <engine> manifest add-output --manifest <manifest> \
  --slug <slug> --platform linkedin --format carousel_slide \
  --compositions "slide_1=...|||slide_2=...|||..." \
  --prompts "slide_1=...|||slide_2=...|||..." \
  --image-paths "slide_1=...|||slide_2=...|||..."
```

End with: "Carousel complete: <N> slides saved to `content-images/<slug>/`."

## Avoiding the "AI carousel" look

LinkedIn is flooded with templated AI carousels (gradient backgrounds, generic illustrations, oversized numbers). The skill avoids these by:

- Defaulting to `editorial`, `minimalist`, or `isometric` rather than `neon-tech`
- Pairing styles with palettes that aren't on-trend (`bone-and-rust` rather than `electric-dusk`)
- Forbidding "blue gradient backgrounds" and "generic AI illustration" via the engine's negatives

If the user explicitly asks for the trendy look, override: "Use neon-tech with electric-dusk."

## Mobile-thumbnail readability

The engine automatically adds a mobile-readability constraint to LinkedIn prompts (the platform is mostly mobile). You don't need to add this manually.

If the user says "won't read at small size", simplify the subject and/or switch to `minimalist` style with a high-contrast palette.

## Invisible machinery

User never sees: "manifest", "rotation", "shared_identity", "JSON", "schema", Python tracebacks, slot names like `slide_1`.

User sees: one-line plan, the image (or each slide), one feedback question after each. That's it.


## Protagonist mode (build-prompt)

When building prompts, pass `--protagonist-mode` based on the source post:
- `named` — first-person posts, named profiles, personal essays where the author/subject is central. Triggers the engine to add face-clarity guidance.
- `generic` — posts featuring "a user," "a customer," "workers" without a specific identity. Faces can be obscured by editorial convention.
- `none` — pure object/scene images with no human figure.
- `auto` (default) — heuristic detection from the subject string.

For named-protagonist posts, also write the subject explicitly: include age range, expression, and an identifying gesture ("a founder, mid-30s, focused expression" not "a marketer"). The face-guidance directive in the prompt depends on the subject naming a person.

The build-prompt response includes `protagonist_mode_resolved` — if it shows "named", the prompt now requests a clear visible face.

## Errors

Translate engine error codes:
- `policy_violation` → "Gemini rejected the prompt. Want to rephrase the subject?"
- `auth` / `fal_key_missing` → "fal.ai isn't accepting the key — check `FAL_KEY`"
- `rate_limit` → "fal.ai is busy, retrying in 5 seconds"
- `network` → "Couldn't reach fal.ai — check your connection"
- anything else → quote briefly, offer retry
