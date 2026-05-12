# Style: infographic-classic

## Visual Fingerprint
Traditional infographic in the tradition of Edward Tufte, classic statistical posters, or Bauhaus-era data design. Serif display type. Restrained, principled chart design — every element earns its place. Numbers feel printed. Compositions have a typographic rigor. Color used sparingly, never decoratively.

## Reference Phrasing for OpenAI
Lead the prompt with one of:

- "A classic infographic in the Tufte tradition — principled chart design, serif typography, restrained color usage, every element earning its place."
- "A traditional statistical poster with serif display type, careful typographic hierarchy, and minimal but precise chart elements."
- "A Bauhaus-influenced data poster with restrained palette, serif headlines, and rigorous typographic grid."

## Subject Treatment
- Serif display type for the headline — substantial, typeset-feeling.
- Numbers rendered as figures, not display elements — they integrate with the text.
- Charts use the simplest possible form for the data: bars, lines, dots. No 3D, no shadows, no gradients on the data itself.
- Color appears only where it carries meaning — usually one or two accent colors maximum.
- Lots of horizontal rules and considered spacing — a print-design feel.

## Composition Notes
Best with `vertical-stack`, `print-grid`, `headline-and-body`.

This style favors composition that respects the page as a typographic object.

## Palette Pairings
Best with: `bone-and-rust`, `paper-and-pencil`, `velvet-financial`, `burnt-poster`.
Acceptable: any 2-3 color palette that includes one dark and one neutral.

## Things to Avoid in Prompts
- "Modern", "futuristic", "cutting-edge"
- Gradients, glows, glassmorphism
- Cartoonish icons
- More than 3 colors

## Example Prompt Skeleton

```
A classic infographic in the Tufte tradition. Serif headline at top: "[HEADLINE]". Statistical chart in the lower two-thirds: [CHART TYPE with data]. Numbers integrated into running text where appropriate. Restrained typography — serif display, sans-serif body. Horizontal rules separating sections. Palette: [PALETTE with hex codes]. 2:3 portrait aspect ratio, Pinterest pin format. Text must be legible and correctly spelled.
```

## Best For
- Academic / research summaries
- Long-form data essays
- Comparison of historical data
- Reports that need authority and gravitas

## Text Rendering Notes (gpt-image-2)

This style is designed for gpt-image-2, which has strong text rendering. To get the best results:
- Specify the exact text you want in quotes within the prompt.
- Use one or two clear typeface families. Mixing more than two breaks the design.
- Numbers and headlines should be larger than body copy by 2-4x — make this explicit in the prompt.
- For multi-section infographics, name each section's heading and body content explicitly. The model handles structured prompts better than vague layout descriptions.
- Avoid abbreviations or made-up symbols in headlines; the model renders standard English most reliably.
