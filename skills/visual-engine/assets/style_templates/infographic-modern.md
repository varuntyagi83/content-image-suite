# Style: infographic-modern

## Visual Fingerprint
Clean, contemporary infographic in the style of contemporary editorial data design — think Information Is Beautiful, Apple's annual report, or a refined Stripe Press chart. Sans-serif typography (geometric, slightly humanist). Generous whitespace. Flat color blocks. Geometric icons with consistent stroke weight. Numbers and stats are large and confident. Hierarchy is obvious at a glance.

## Reference Phrasing for OpenAI
Lead the prompt with one of:

- "A clean, modern infographic in contemporary editorial data-design style — sans-serif typography, generous whitespace, flat color blocks, geometric icons."
- "A minimal modern infographic with bold sans-serif headlines, large numbers, geometric icons, and clear visual hierarchy."
- "A contemporary data infographic with clean typography, whitespace-led layout, and confident use of color blocks for emphasis."

## Subject Treatment
- Lead with a clear headline at the top.
- Each data point gets its own block — number first (large), label second (small).
- Icons are simple, geometric, consistent stroke weight throughout.
- No photographic elements. No painterly textures. No 3D rendering.
- Charts (bars, donuts, lines) are simplified to their essence — no ticks, minimal axis labels.

## Composition Notes
Best with `vertical-stack` (sections stacked top to bottom), `grid-2x2`, or `grid-3x1`.

Avoid `centered-subject`, `split-frame`, `diagonal-motion` — these are illustration compositions, not data compositions.

## Palette Pairings
Best with: `cold-architecture`, `bone-and-rust`, `velvet-financial`, `paper-and-pencil`.
Acceptable: any 2-3 color palette with one clear accent color.

## Things to Avoid in Prompts
- "Painterly", "watercolor", "sketchy"
- "Illustrated figures", "characters"
- Decorative borders, frames, ornaments
- Multiple icon styles in one infographic

## Example Prompt Skeleton

```
A clean modern infographic in contemporary editorial data-design style. Headline at top: "[HEADLINE]". Three data sections, each with: [STAT 1: "[number]" labeled "[label]"], [STAT 2], [STAT 3]. Bottom footer: "[FOOTER]". Sans-serif typography throughout. Flat color blocks. Geometric icons with consistent 2px stroke weight. Generous whitespace. Palette: [PALETTE with hex codes]. 2:3 portrait aspect ratio, Pinterest pin format. Text must be legible and correctly spelled.
```

## Best For
- Pinterest pins (the default)
- LinkedIn carousel slides
- Standalone shareable stats
- Step-by-step process visualizations
- Comparison tables

## Text Rendering Notes (gpt-image-2)

This style is designed for gpt-image-2, which has strong text rendering. To get the best results:
- Specify the exact text you want in quotes within the prompt.
- Use one or two clear typeface families. Mixing more than two breaks the design.
- Numbers and headlines should be larger than body copy by 2-4x — make this explicit in the prompt.
- For multi-section infographics, name each section's heading and body content explicitly. The model handles structured prompts better than vague layout descriptions.
- Avoid abbreviations or made-up symbols in headlines; the model renders standard English most reliably.
