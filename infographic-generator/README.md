# infographic-generator

Part of the content-image-suite. Generates infographics with legible text using OpenAI gpt-image-2.

## What's different

The other platform skills (medium, linkedin, twitter, instagram, meta) generate illustrated images via Gemini 3 Pro Image through fal.ai. Gemini is excellent at illustration but unreliable at text rendering.

Infographics need text to be the content, so this skill uses OpenAI gpt-image-2 instead — released April 21, 2026, designed for "complex visual tasks" with "improved text rendering".

## Formats

- `pinterest_pin` (default) — 1024x1536, 2:3 portrait
- `square_card` — 1024x1024, 1:1
- `landscape_poster` — 1536x1024, 3:2

## Requirements

- `OPENAI_API_KEY` environment variable
- OpenAI Organization Verification (one-time, in the developer console)
- `pip install 'openai>=1.50'`

## Cost

At medium quality, ~$0.041 per pin. A full three-format set is ~$0.12. The skill warns the user about cost when first invoked in a session.

## Triggers

Use this skill when the user says:
- "make an infographic"
- "Pinterest pin"
- "data poster"
- "stats graphic"
- "one-pager"
- "chart summarizing X"
- Any request where text IS the content of the image

## Architecture

Like the other platform skills, this one is a thin wrapper around `visual-engine`. It calls:
- `path-check` — confirm output location
- `manifest find` — link to parent post if any
- `rotate` — pick style/palette/composition
- `build-prompt` with `--text-mode allow` — assemble the structured prompt
- `generate` with `--provider openai-gpt-image` — produce the image
- `manifest add-output` — record the output

See `SKILL.md` for the full workflow.

## Files

- `SKILL.md` — the workflow Claude follows
- `README.md` — this file
- (Engine, style templates, references all live in the shared `visual-engine` skill)
