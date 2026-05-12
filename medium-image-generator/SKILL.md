---
name: medium-image-generator
description: Generate hero and in-article images for Medium blog posts using Gemini Nano Banana Pro. Triggers on phrases like "make me a hero image for Medium", "generate Medium cover", "image for this Medium draft", "blog visuals for Medium", or whenever a user shares a Medium draft, file, URL, or title with bullets. Also triggers on iteration phrases like "make it darker", "redo the hero" when an image was previously generated. Part of the Content Image Suite, uses the shared visual-engine for rotation, palette, and prompt construction.
license: Proprietary. Contact author for redistribution terms.
compatibility: Designed for Claude Code or Hermes Agent. Requires Python 3.10+, fal.ai API key (FAL_KEY), optionally ANTHROPIC_API_KEY or OPENAI_API_KEY for the quality gate.
metadata:
  author: Raygency (Varun Tyagi)
  version: "1.0.0"
  hermes:
    tags: [creative, blogging, image-generation, medium]
    related_skills:
      - content-image-orchestrator
      - linkedin-image-generator
---

# Medium Image Generator (v2)

Generate Medium-specific images using the shared visual-engine. Aggressive rotation across styles and palettes (windows of 3 and 4 respectively) keeps your Medium profile grid visually varied.

## Output formats

- `hero`: 16:9 (1920×1080), the primary article cover
- `inline_1`, `inline_2`, `inline_3`: 4:3 (1600×1200), section dividers (optional)

## When this skill triggers vs the orchestrator

- **This skill** triggers when the user explicitly says "Medium" or just asks for blog images without naming other platforms.
- **The orchestrator** (content-image-orchestrator) triggers when the user wants images for multiple platforms in one go.

If the user says only "make me a hero image for this draft" without specifying platform, default to Medium and proceed normally.

## Workflow

### Step 1: Locate engine and manifest

The shared engine lives next to this skill in the suite. Find the engine CLI:

- Use this skill's own `scripts/engine` wrapper: `${HERMES_SKILL_DIR}/scripts/engine` in Hermes, or the absolute path to `scripts/engine` inside this skill's directory in Claude Code
- The path is also discoverable via `find ~/.claude/skills -name engine.py -path '*/visual-engine/*'`

The cross-platform manifest lives at: `<working-dir>/content-images/manifest.json` (default). If absent, the engine creates it automatically. Use `<working-dir>` of where Claude Code was launched.

For backward compatibility: if `<working-dir>/medium-images/manifest.json` exists (old v1 location), migrate it once via:

```
<engine>/migrate_v1_to_v2.py <working-dir>/medium-images/manifest.json --output <working-dir>/content-images/manifest.json
```

Then continue using the v2 path.

### Step 1.5: Verify the manifest location once per session

Before the first generation in this conversation, check the planned manifest path is sensible:

```bash
<engine> path-check \
  --manifest <working-dir>/content-images/manifest.json
```

If the response has `"suspicious": true`, the user is in a folder that probably isn't where they want long-term image history (the suite source folder, /tmp, $HOME root, or top of Downloads).

In that case, tell the user once:
> Saving images to `<full path>`. That's `<reason>`. Different location? Tell me a path, or say "ok" to use this one.

Wait for confirmation. If they give a new path, use it for the rest of the session. Don't ask again in this conversation.

If `"suspicious": false`, proceed silently: no need to confirm with the user.

### Step 2: Identify the input

The user gives a Medium draft in any of these forms:

| Form | How to detect | What to do |
|------|--------------|-----------|
| Pasted full draft | Long text in the message itself (>200 words) | Read inline. |
| Attached file (.md, .txt, .docx) | File appears in `/mnt/user-data/uploads/` | Read with appropriate tool. |
| URL (medium.com, substack.com) | Message contains a URL | Use `web_fetch` to get content. |
| Title + bullets / pre-write | Short message with title and 2-5 bullet points | Treat bullets as the spine; tell user "I'll work from the outline; the image will be conceptual rather than scene-specific." |
| Title only | One-line topic | Ask one short clarifying question: "What's the angle or thesis? One sentence is enough." |

### Step 3: Cross-session linking check

Before generating anything, check if this content already exists in the manifest:

```bash
<engine> manifest find \
  --manifest <working-dir>/content-images/manifest.json \
  --title "<the post title>" \
  --slug "<slugified title>" \
  --threshold 0.80
```

If `matched: true` and the piece already has a Medium output, ask the user: "Looks like you've generated Medium images for this before. Regenerate (replaces them) or pick up where you left off?"

If matched but Medium output is null, this means orchestrator or another platform skill registered the piece. Reuse the `shared_identity` from the matched piece: that's the locked style+palette.

### Step 4: Extract the subject

**Step 4a: First, detect the voice of the post.** This is THE most important decision in this workflow. It changes everything that follows.

Read the post text and answer ONE question: **Is this a first-person essay, OR is it a third-person/conceptual piece?**

A post is first-person if ANY of these are true:
- It uses "I" repeatedly in the opening paragraph ("I built X", "I spent years", "I noticed")
- It's a founder essay, a personal narrative, or a memoir of building something
- The author is the protagonist of the story being told
- It profiles a specific named individual ("How [Name] did Z"): the named person is the protagonist

A post is conceptual/third-person if:
- It's a how-to guide, a technical explainer, or an opinion piece without personal framing
- It uses "you" or "we" or impersonal voice
- The post is about an idea, system, or category: not about a person's experience

**Why this matters:** First-person posts need a *protagonist-centered subject*: a specific person with a face. Conceptual posts work fine with object-centered or scene-centered subjects.

Common failure mode to avoid: extracting a conceptual subject ("a marketing desk", "a workflow") for a first-person post. This produces faceless images that drain the emotional voice. If the post says "I built X because I got tired of Y", the image should center the *narrator*, not the workflow.

**Step 4b: Now run the three-question protocol** in `<engine>/references/subject-extraction.md`:

1. What is the post literally about? (one sentence)
2. What is the post emotionally about? (one sentence)
3. What is one concrete scene that holds both?

For first-person posts, question 3's answer MUST describe the narrator/protagonist with:
- An age range (mid-30s, early-40s, etc.)
- A specific expression or gaze (focused, mid-thought, tired-but-resolved)
- One identifying detail (glasses pushed up, sleeves rolled, holding a coffee mug)
- The action they're performing in the scene

Bad first-person subject: "A marketing desk split between chaos and order."
Good first-person subject: "A founder, mid-30s, focused expression, standing at the boundary between a chaotic five-screen workstation on the left and a single calm dashboard on the right."

For conceptual posts, the subject can be a scene, object, or generic figure: no protagonist requirement.

**Step 4c: Record the protagonist mode for Step 6.** If first-person, mode is `named`. If conceptual with no figure, mode is `none`. If conceptual with a generic figure, mode is `generic`. You'll pass this to `build-prompt` in Step 6.

### Step 5: Run rotation

```bash
<engine> rotate \
  --manifest <working-dir>/content-images/manifest.json \
  --platform medium \
  --post-type <inferred type>
  [--locked-style <style>]    # if cross-session linked
  [--locked-palette <palette>] # if cross-session linked
```

Returns: `recommended_style`, `recommended_palette`, `allowed_compositions[hero]`, `forbidden_themes`.

Pick the hero composition from `allowed_compositions["hero"]`. Prefer one that suits the subject.

### Step 6: Build the hero prompt

Use the protagonist mode you recorded in Step 4c.

```bash
<engine> build-prompt \
  --platform medium --format hero \
  --style <recommended_style> \
  --palette <recommended_palette> \
  --composition <picked_composition> \
  --subject "<extracted subject>" \
  --protagonist-mode <named|generic|none>
```

Returns `prompt`, `aspect_ratio`, `width`, `height`, `label_risk_detected`, `label_risk_reason`, `protagonist_mode_resolved`.

**If `protagonist_mode_resolved` is "named":** the prompt now includes a directive to render a clear, recognizable face. This counters editorial-illustration's default tendency to obscure faces.

**If `label_risk_detected` is true:** the subject contained label-shaped phrasing. The engine has already prepended an aggressive no-text negative. Mention this casually to the user once:

> Heads up: your subject has label-like phrasing, so I added a strong no-text negative. If text still leaks into the image, we can rephrase the subject: see `subject-extraction.md` for visual proxies.

Then proceed to generation normally.

### Step 7: Generate

If `FAL_KEY` is set:

```bash
<engine> generate \
  --prompt "<the prompt>" \
  --aspect 16:9 \
  --output <working-dir>/content-images/<slug>/hero.png
```

**Handle three possible response statuses:**

- `"status": "ok"` → image generated successfully, proceed to Step 8.
- `"status": "file_exists"` (exit code 4) → the output path already has an image from before. Surface this to the user:
  > I already generated `hero.png` for this post on `<modified_at date>`. Want me to use that one, or generate a fresh take?

  If user wants the existing one: skip to Step 8, using the existing path.
  If user wants a new one: re-run the same command with `--overwrite` appended.

- `"status": "error"` → translate the error per the Error code translation section below.

**Additionally, check the `text_detection` field in successful responses:**

The response includes `text_detection.passed` (bool) and `text_detection.words_found` (list). When `passed: false`, the OCR safety net found rendered text in the image. Surface this to the user:

> Heads up: text rendering detected in this image: the OCR found words like `<list>`. Want me to regenerate? (I'll add a stronger no-text directive.)

If user wants to regenerate: rebuild the prompt with the subject pre-rewritten (strip the textual cues you saw in the OCR output), then `generate --overwrite`.

If `text_detection.status` is `"ocr_unavailable"`, OCR isn't installed on the user's machine: don't surface this as an error, just proceed silently. Tell the user once per session, only when they ask why text wasn't caught:
> The OCR safety net needs tesseract. Install with `brew install tesseract` and `pip install pytesseract pillow` if you want automatic text detection.

If `FAL_KEY` is not set: fall back. Tell the user once "I'll show the prompt to paste into fal.ai or AI Studio," show the prompt formatted for copy, and treat it like generation succeeded for the conversation flow.

### Step 8: Show + ask

Show the image inline. Display the prompt below it as a collapsed/secondary block (e.g. quoted block prefixed with "Prompt (for re-running later):").

**Show one short summary line above the image:**
> "Editorial illustration, bone-and-rust palette, woman at desk reviewing invoices."

**Ask one feedback question:**
> "Want me to keep going with 3 inline images, tweak this one, or call it done?"

### Step 9: Handle feedback

Use `<engine>/references/iteration-vocabulary.md` for the full mapping. Key shortcuts:

- "looks good", "keep going" → next inline image
- "darker", "lighter", "warmer", "cooler" → lighting tweak (regenerate)
- "make her older", "younger", "more serious" → subject tweak (regenerate)
- "different composition" → re-pick from `allowed_compositions[hero]`, regenerate
- "different style" → re-pick from `allowed_styles`, regenerate from scratch
- "missing the point" → re-extract subject; ask one clarifying question if needed
- "we're done" → save manifest and close

Iteration limit: after 5 tweaks on a single image, ask the user explicitly: "Five tweaks in. Want to start fresh or push for a 6th?"

### Step 10: Inline images (only if requested)

When user says "keep going":

1. Reuse `style` and `palette` from the hero (visual continuity).
2. Pick a different composition from `allowed_compositions["inline_1"]` (must differ from hero AND from any inline already done).
3. Pick a different subject focus: a key concept, counterargument, transition moment.
4. Build prompt with `--format inline_1` (4:3, 1600×1200).
5. Generate, show, ask.

Repeat for `inline_2`, `inline_3` if user keeps saying "keep going."

### Step 11: Save manifest

Once user signals completion ("we're done"), call:

```bash
# First, upsert the content piece (or just confirm if cross-session linked)
<engine> manifest upsert \
  --manifest <working-dir>/content-images/manifest.json \
  --title "<post title>" \
  --slug "<slug>" \
  --style <style> \
  --palette <palette> \
  --themes "<comma-separated themes>" \
  --date <YYYY-MM-DD>

# Then add the medium output
<engine> manifest add-output \
  --manifest <working-dir>/content-images/manifest.json \
  --slug "<slug>" \
  --platform medium \
  --format hero \
  --compositions "hero=<comp>|||inline_1=<comp>|||..." \
  --prompts "hero=<prompt>|||inline_1=<prompt>|||..." \
  --image-paths "hero=<path>|||inline_1=<path>|||..."
```

End with: *"Saved. The next post will use a different style and palette automatically."*

If user closes the conversation before saying "done," do NOT save. Half-finished sessions shouldn't constrain future ones.

## Invisible-machinery rules

The user must NEVER see:
- The word "manifest" (use "image history" or just nothing)
- The word "rotation" (use "different style than last time" if needed)
- "JSON", "schema", "engine", or any tool/script name
- The forbidden_themes list
- Python tracebacks

## Error code translation

The engine returns structured errors. Translate them:
- `rate_limit` → "fal.ai is busy, retrying in 5 seconds"
- `policy_violation` → "Gemini rejected that prompt. Want to rephrase the subject?"
- `auth` / `fal_key_missing` → "fal.ai isn't accepting the key: check `FAL_KEY`"
- `network` → "Couldn't reach fal.ai: check your connection"
- `download_failed` → "Generated, but the download failed. Retry?"
- anything else → quote the message briefly and offer retry

## Edge cases

- **fal.ai retry exhausted** → fall back to prompt-only mode: show the prompt, tell the user "fal.ai isn't responding; here's the prompt to paste into AI Studio."
- **Empty manifest** → first post; pick freely.
- **Corrupt manifest** → engine auto-backs it up; tell the user "Image-history file was damaged so I started fresh. Your past posts won't be considered for rotation today."
- **Subject extraction fails on a vague post** → ask one question: "What's one image, scene, or object that captures this for you?"
- **Multi-part series** → user says "this is part 2"; engine detects this in notes and locks style+palette to the previous part.
