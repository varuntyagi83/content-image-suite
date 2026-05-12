---
name: infographic-generator
description: Use this skill when the user asks for an infographic, a Pinterest pin, a data poster, a stats graphic, a one-pager, or any "infographic-style" image with rendered text. Different from the other content-image-suite skills because it uses OpenAI gpt-image-2 (not Gemini) to get legible text rendering, and it produces vertical, square, or wide formats with real typography. Triggers on requests like "make an infographic of X", "Pinterest pin summarizing my post", "create a data graphic about Y", "one-pager for the announcement", or any image where text content is the point.
license: Proprietary. Contact author for redistribution terms.
compatibility: Designed for Claude Code or Hermes Agent. Requires Python 3.10+, fal.ai API key (FAL_KEY), optionally ANTHROPIC_API_KEY or OPENAI_API_KEY for the quality gate.
metadata:
  author: Raygency (Varun Tyagi)
  version: "1.0.0"
  hermes:
    tags: [creative, data-visualization, image-generation, openai-gpt-image]
    related_skills:
      - content-image-orchestrator
      - medium-image-generator
      - linkedin-image-generator
    requires_toolsets: [terminal, file]
---

# Infographic Generator

## What this skill does

Generates infographics with legible, correctly-spelled text. Uses OpenAI gpt-image-2 (released April 21, 2026) instead of the Gemini backend that the other content-image-suite skills use, because gpt-image-2 is significantly better at rendering text.

Three output formats are supported:
- `pinterest_pin`: 1024x1536 (2:3 portrait). Pinterest, content marketing, vertical share. Default.
- `square_card`: 1024x1024 (1:1). LinkedIn carousel slides, Instagram feed, single-stat callouts.
- `landscape_poster`: 1536x1024 (3:2). Blog post embeds, presentation slides, wide data visualization.

The skill plugs into the shared content-image-suite manifest (`<working-dir>/content-images/manifest.json`), so when an infographic is paired with a Medium post, the style and palette can lock to the Medium post's `shared_identity`. When the infographic stands alone, it uses its own rotation.

## Workflow

### Step 1: Find the visual engine

```bash
which python || echo "python not found"
test -x "${HERMES_SKILL_DIR:-$HOME/.claude/skills}/visual-engine/scripts/engine.py" 2>/dev/null || test -d ~/.claude/skills/visual-engine || echo "visual-engine skill not installed"
```

`<engine>` = this skill's own `scripts/engine` wrapper, which auto-detects the shared visual-engine across runtimes. Resolve it as `${HERMES_SKILL_DIR}/scripts/engine` in Hermes Agent, or the absolute path to `scripts/engine` inside this skill's directory in Claude Code. Invoke directly: do not prefix with `python`.

### Step 2: Confirm the working directory and manifest location

```bash
<engine> path-check \
  --manifest <working-dir>/content-images/manifest.json
```

If `status: "suspicious_location"`, announce the path to the user and ask whether to continue.

### Step 3: Confirm there's no parent post conflict

```bash
<engine> manifest find \
  --manifest <working-dir>/content-images/manifest.json \
  --title "<the post title or topic>" \
  --slug "<slugified title>" \
  --threshold 0.80
```

Three outcomes:
- `matched: false`: the infographic is standalone or new. Continue with fresh rotation.
- `matched: true` with an existing infographic output: ask: "You've generated an infographic for this before. Regenerate or pick up where you left off?"
- `matched: true` but no infographic output yet (only Medium/LinkedIn/etc): **reuse the shared_identity** so the infographic visually matches the parent piece.

### Step 4: Extract the subject (uses infographic-specific protocol)

Apply the protocol in `<engine>/references/subject-extraction-infographic.md`. The key difference from the illustration platforms: infographics extract a *data story*, not a scene.

Three questions:
1. **What is the headline?** One sentence, 4-7 words, confident and assertive.
2. **What are the 3-5 sections?** Each needs a label, a number/stat, and a 1-line body.
3. **What is the footer?** Author attribution, source, or CTA. Optional but recommended.

Assemble these into the structured subject format:

```
Headline: "[exact text]".
Section 1: title "[label]", number "[stat]", body "[1-line explanation]".
Section 2: title "[label]", number "[stat]", body "[1-line explanation]".
Section 3: title "[label]", number "[stat]", body "[1-line explanation]".
Footer: "[attribution]".
```

The structured format matters: gpt-image-2 follows explicit prompts better than narrative ones.

### Step 5: Run rotation

```bash
<engine> rotate \
  --manifest <working-dir>/content-images/manifest.json \
  --platform infographic \
  --post-type <inferred type>
  [--locked-style <style>]    # if reusing shared_identity from parent post
  [--locked-palette <palette>] # if reusing shared_identity
```

Returns: `recommended_style`, `recommended_palette`, `allowed_compositions[<format>]`, `forbidden_themes`.

The four infographic styles are:
- `infographic-modern`: clean sans-serif, geometric icons, whitespace-led. Default for product/tech topics.
- `infographic-editorial`: magazine-style with serif headlines, illustrative supporting elements. Best for essays.
- `infographic-tech`: dashboard-inspired, KPI cards, accent glows. Best for SaaS metrics, technical announcements.
- `infographic-classic`: Tufte-tradition, restrained, serif display. Best for research, academic, comparison data.

Pick a composition from `allowed_compositions[pinterest_pin]` (or `square_card` / `landscape_poster`) that suits the data shape. Default is `vertical-stack` for pins.

### Step 6: Build the prompt

Important: pass `--text-mode allow` so the engine skips the anti-text safety net. Text IS the content here.

```bash
<engine> build-prompt \
  --platform infographic --format pinterest_pin \
  --style <recommended_style> \
  --palette <recommended_palette> \
  --composition <picked_composition> \
  --subject "<structured subject from Step 4>" \
  --text-mode allow
```

Protagonist mode is irrelevant here (no figures). The engine handles this automatically.

Returns `prompt`, `aspect_ratio`, `width`, `height`, and `text_mode: "allow"`.

### Step 7: Generate

Important: pass `--provider openai-gpt-image` so the engine uses gpt-image-2 instead of fal/Gemini. Set `--text-mode allow` so the OCR check reports words informationally rather than failing on them.

```bash
<engine> generate \
  --provider openai-gpt-image \
  --prompt "<from Step 6>" \
  --aspect 2:3 \
  --output <working-dir>/content-images/<slug>/infographic-pin.png \
  --text-mode allow \
  [--quality medium]            # default; high for client work, low for drafts
  [--output-format png]         # png default; jpeg for smaller files
  [--openai-model gpt-image-2]  # default
```

Quality cost reference (per OpenAI):
- `low` ~$0.005: fast drafts, thumbnails
- `medium` ~$0.041: default, good for most uses (Pinterest pin native size)
- `high` ~$0.165: client deliverables, premium output

Requirements:
- `OPENAI_API_KEY` must be set
- gpt-image-2 requires one-time OpenAI Organization Verification at platform.openai.com/settings/organization/general

If `OPENAI_API_KEY` is missing the engine returns `status: "missing_credentials"` with the verification URL. Tell the user clearly and wait for them to set it.

### Step 8: Verify the rendered text

The OCR check (when `text_mode: allow`) reports the words detected in the image. Compare them to the words you asked for in the headline and section labels.

If a critical word is missing or misspelled:
- Adjust the subject's structured format (e.g. quote the exact text more explicitly)
- Regenerate with `--overwrite`

If the visual layout is wrong (sections crammed, headline cut off):
- Try a different composition
- Or switch quality from medium to high (more compute = better layout)

### Step 9: Save to manifest

```bash
<engine> manifest add-output \
  --manifest <working-dir>/content-images/manifest.json \
  --slug "<slug>" \
  --platform infographic \
  --format pinterest_pin \
  --style <style> \
  --palette <palette> \
  --composition <composition> \
  --local-path "<full path to file>"
```

This locks the rotation state for this piece and makes future regenerations idempotent.

### Step 10: Present

Use `present_files` with the generated image. Brief description: style + palette + what the infographic communicates. Don't post-amble.

## Multi-format runs

If the user wants multiple formats (e.g. Pinterest pin AND square card AND landscape poster for the same data), reuse the same subject, style, and palette across all three. Just change `--format` in Steps 6-7. The composition should adapt:
- pinterest_pin: `vertical-stack` or `print-grid`
- square_card: `grid-2x2` or `headline-and-body`
- landscape_poster: `grid-3x1` or `dashboard-layout` or `chart-with-callouts`

## When to use this skill vs the others

- The user mentions "infographic", "Pinterest pin", "data poster", "stats graphic", "one-pager" → infographic-generator
- The user wants legible text rendered IN the image → infographic-generator
- The user wants a Medium hero image with illustrated chaos → medium-image-generator (uses Gemini, blocks text)
- The user wants a LinkedIn carousel with text overlay → linkedin-image-generator (uses Gemini, text added externally)
- The user wants both a Medium hero AND an infographic summarizing the post → orchestrator coordinates both, sharing identity

## Cost awareness

Per generation at medium quality: ~$0.041. A typical session (one pin + one square + one landscape) is ~$0.12. Mention this to the user once when they first use the skill so they're aware it's a paid backend, unlike fal.ai which they may already be using for Gemini.

## What to do when things go wrong

| Error | Cause | Action |
|---|---|---|
| `missing_credentials` | No `OPENAI_API_KEY` | Tell user to set the env var. Mention Organization Verification requirement. |
| `missing_dependency` | `openai` Python package not installed | Tell user to run `pip install 'openai>=1.50'` |
| `api_error` | Network, rate limit, or moderation block | Show the error message verbatim. If it's a moderation block, the prompt content needs to change. |
| `bad_args` (size) | Asked for a size that violates gpt-image-2 constraints | The engine clamps automatically, but if width/height were passed explicitly, suggest using `--aspect` instead. |
| OCR detects garbled text | gpt-image-2 misspelled a word | Regenerate with the exact word quoted more clearly in the subject. If repeated, switch to `--quality high`. |
| Layout looks wrong | Composition mismatch with the data shape | Pick a different composition from `allowed_compositions`. |
