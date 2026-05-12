---
name: content-image-orchestrator
description: Generate coordinated images across multiple platforms (Medium, LinkedIn, Twitter, Instagram, Meta) from a single piece of source content. Triggers when the user names 2+ platforms ("Medium and LinkedIn", "all platforms", "everywhere"), wants a coordinated image set for an article, or says they're cross-posting. Reads source once, extracts subject once, picks one style+palette for all chosen platforms, generates each in sequence with iteration in between. OPTIONAL: every platform skill works without this.
license: Proprietary. Contact author for redistribution terms.
compatibility: Designed for Claude Code or Hermes Agent. Requires Python 3.10+, fal.ai API key (FAL_KEY), optionally ANTHROPIC_API_KEY or OPENAI_API_KEY for the quality gate.
metadata:
  author: Raygency (Varun Tyagi)
  version: "1.0.0"
  hermes:
    tags: [creative, social-media, image-generation, orchestration]
    related_skills:
      - medium-image-generator
      - linkedin-image-generator
      - twitter-image-generator
      - instagram-image-generator
      - meta-image-generator
      - infographic-generator
---

# Content Image Orchestrator

Multi-platform coordination. Use when the user names 2+ platforms. Otherwise defer to the single platform's skill.

The whole job is: one subject + one style + one palette → N images, one per platform, each shaped for that platform's format.

## Engine path

`<engine>` = this skill's own `scripts/engine` wrapper, which auto-detects the shared visual-engine across runtimes. Resolve it as `${HERMES_SKILL_DIR}/scripts/engine` in Hermes Agent, or the absolute path to `scripts/engine` inside this skill's directory in Claude Code. Invoke directly: do not prefix with `python`.

`<manifest>` = `<working-dir>/content-images/manifest.json` (auto-created if missing).

## Path check (once per session, before first generation)

```bash
<engine> path-check --manifest <manifest>
```

If response has `"suspicious": true`, tell the user once:
> Saving images to `<full path>`. That's `<reason>`. Different location? Tell me a path, or say "ok" to use this one.

Wait for confirmation. If `"suspicious": false`, proceed silently.


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

### 1. Read the source once

| User gave you | Action |
|---|---|
| Pasted draft (>200 words) | Read inline |
| File path | Use the right read tool |
| URL | `web_fetch` |
| Title + bullets | Use bullets as the spine |
| Title only | Ask one question: "What's the angle? One sentence." |

### 2. Resolve the platform list

If the user named the platforms explicitly, use that list. If they said "all" or "everywhere", use all 5. If ambiguous, ask once:
> Which platforms: Medium, LinkedIn, Twitter, Instagram, Meta? You can pick any combination.

Then lock the list.

### 3. Cross-session linking

```bash
<engine> manifest find --manifest <manifest> \
  --title "<title>" --slug "<slugified-title>" --threshold 0.80
```

If `matched: true`:
- Existing `shared_identity` → that's your locked style+palette for all platforms.
- Some platforms already have outputs → ask: "Already have Medium + LinkedIn images. Generate just the missing platforms, or redo everything?"

If no match: new content, continue.

### 4. Extract the subject once

Apply `<engine_dir>/references/subject-extraction.md`: the 3-question protocol. This subject anchors EVERY platform's primary image. Variety per platform comes from composition and format, not subject.

### 5. Compute shared identity

```bash
<engine> shared-identity --manifest <manifest> \
  --platforms <comma-separated> --post-type <type>
```

Returns `style`, `palette`, and `per_platform_rotations`. Lock these.

If Instagram is in the platform list and the engine reports `consistency_locked: true` on its rotation, surface that to the user once: "Your Instagram has an established cinematic + monochrome look. Using that across all platforms so the IG grid stays coherent."

### 6. Register the content piece

```bash
<engine> manifest upsert --manifest <manifest> \
  --title "<title>" --slug "<slug>" \
  --style <style> --palette <palette> \
  --themes "<comma,separated,themes>"
```

### 7. Announce the plan (one line, then proceed)

> Editorial illustration, bone-and-rust palette, woman reviewing invoices as the metaphor. Starting with the Medium hero.

No itemized per-platform breakdown. One line, then generate.

### 8. Generate each platform in sequence

Order: Medium → LinkedIn → Twitter → Instagram → Meta (only the ones in the list).

For each platform `pid`:

a) Rotation with locks:
```bash
<engine> rotate --manifest <manifest> --platform <pid> \
  --post-type <type> --locked-style <style> --locked-palette <palette>
```

b) For multi-format platforms, decide format:
- **LinkedIn**: "Cover (1.91:1) or carousel (1:1, 5-10 slides)?"
- **Instagram**: "Feed (1:1), Story (9:16), or carousel?"
- Other platforms: use the platform's `is_primary: true` format from `engine platforms`.

c) Pick composition from `allowed_compositions[format-name]`.

d) Build prompt:
```bash
<engine> build-prompt --platform <pid> --format <format> \
  --style <style> --palette <palette> \
  --composition <comp> --subject "<subject>"
```

e) Generate:
```bash
<engine> generate \
  --prompt "<prompt>" --aspect <ratio> \
  --output <working-dir>/content-images/<slug>/<pid>_<format>.png
```

**Handle three response statuses:**
- `"status": "ok"` → image generated, proceed to (f).
- `"status": "file_exists"` (exit 4): output exists from a previous session. Ask:
  > Already have a `<pid>` image for this from `<modified_at>`. Use that, or generate fresh?

  Use existing → proceed to (f) using the existing path. Generate fresh → re-run with `--overwrite`.
- `"status": "error"` → translate per the Error code translation table at the bottom.

The engine remaps unsupported ratios (e.g. LinkedIn's 1.91:1 → 16:9). The `generate` response includes `aspect_ratio_was_remapped: true` in those cases: mention it casually: "LinkedIn doesn't take 1.91:1 exactly, generated at 16:9: works fine for the LinkedIn preview."

f) Show one summary line + image + one question:
> LinkedIn cover ready. Continue to Twitter, tweak this, or stop here?

g) On approval, save:
```bash
<engine> manifest add-output --manifest <manifest> \
  --slug <slug> --platform <pid> --format <format> \
  --compositions "<slot>=<comp>" \
  --prompts "<slot>=<full prompt>" \
  --image-paths "<slot>=<path>"
```

h) Move to next platform.

### 9. Multi-slide modes (carousels)

For LinkedIn or Instagram carousel mode:
- Pick the slide count (or ask: "How many slides?": default 6).
- Plan briefly (internally, don't narrate): hook → 3-7 elaborations → payoff.
- For each slide pick a different composition AND a different subject focus.
- Generate slides one at a time, with feedback after each.
- After all slides done, save them as `slide_1`, `slide_2`, ..., `slide_N` under the same platform output.

### 10. Per-platform iteration

If the user tweaks a single platform's image, iterate just that one. Iteration vocabulary at `<engine_dir>/references/iteration-vocabulary.md`.

If a tweak would break shared identity ("different style for LinkedIn only"), confirm:
> That breaks the shared look. Apply to all platforms or just LinkedIn?

LinkedIn-only goes into notes; all-platforms means regenerate everything.

### 11. Closing

When all platforms done:
> Done. <N> images saved across <list>. Next post rotates automatically.

If Instagram was in the list, append: " IG will stay coherent with this look."

## When to ask (and when not to)

Ask one short question for these only:
- Platform list is genuinely ambiguous
- LinkedIn or Instagram format mode (cover vs carousel, feed vs story)
- Carousel slide count (default 6 if user doesn't care)
- Subject extraction yields nothing concrete
- Cross-session match in the 0.80-0.95 range (confirm: "Same as your earlier post X?")

Don't ask:
- If the user named specific platforms: use that list
- If only one platform: defer to that platform's skill instead
- About style or palette unless they ask
- About cross-session links above 0.95 confidence (just use it)

## Invisible machinery

User never sees: "manifest", "rotation", "shared_identity", "JSON", "schema", Python tracebacks.

User does see:
- One-line plan announcement at the start
- Each image with a one-line summary above
- One feedback question after each
- One closing line at the end

That's the whole UX surface. The orchestrator is coordination, not narration.



## Protagonist mode (build-prompt)

When building prompts, pass `--protagonist-mode` based on the source post:
- `named`: first-person posts, named profiles, personal essays where the author/subject is central. Triggers the engine to add face-clarity guidance.
- `generic`: posts featuring "a user," "a customer," "workers" without a specific identity. Faces can be obscured by editorial convention.
- `none`: pure object/scene images with no human figure.
- `auto` (default): heuristic detection from the subject string.

For named-protagonist posts, also write the subject explicitly: include age range, expression, and an identifying gesture ("a founder, mid-30s, focused expression" not "a marketer"). The face-guidance directive in the prompt depends on the subject naming a person.

The build-prompt response includes `protagonist_mode_resolved`: if it shows "named", the prompt now requests a clear visible face.

## Label-risk handling (applies to every build-prompt call)

`build-prompt` returns two fields: `label_risk_detected` (bool) and `label_risk_reason` (str).

When `label_risk_detected: true`: the subject has label-shaped phrasing (comma-separated capitalized phrases, quoted text, or multiple short label-like segments) that Gemini will likely render as visible text. The engine has already prepended an aggressive no-text negative.

Mention this casually to the user once per session:
> Heads up: your subject has label-like phrasing, so I added a strong no-text negative. If text leaks anyway, we can rephrase: see the visual proxies section in `subject-extraction.md`.

Then proceed. If text still appears in the generated image, the fix is on the subject side: rephrase the labels as a continuous scene or use visual proxies.


## Text detection (post-generation safety net)

Every successful `generate` response includes a `text_detection` field with:
- `passed` (bool): true if OCR found no rendered text
- `words_found` (list): what words OCR detected, if any
- `status`: "ok", "text_detected", or "ocr_unavailable"

When `passed: false`, the image likely has rendered text (a clock face, a folder label, a sign). Surface to the user:
> OCR detected text in this image: `<words>`. Want me to regenerate with a stronger no-text directive?

If user agrees, re-run `generate` with `--overwrite`. The engine will apply more aggressive subject rewriting on the retry.

When `status: ocr_unavailable`, the user does not have tesseract installed. Do not flag this: proceed silently. Only mention if user explicitly asks why text was not caught:
> The OCR safety net needs tesseract. `brew install tesseract && pip install pytesseract pillow` enables it.

## Errors

The engine returns structured errors. Translate them:
- `rate_limit` → "fal.ai is busy, retrying in 5 seconds"
- `policy_violation` → "Gemini rejected that prompt as borderline. Want to rephrase the subject?"
- `auth` → "fal.ai isn't accepting the key: check `FAL_KEY` is set"
- `fal_key_missing` → same
- `network` → "Couldn't reach fal.ai: check your connection"
- `download_failed` → "Image generated but couldn't download. Try once more?"
- anything else → quote the message briefly and offer to retry
