# Style: infographic-editorial

## Visual Fingerprint
Magazine-style data illustration in the tradition of The Economist's chart packs, FT data journalism, or The New York Times graphics desk. Serif headlines paired with sans-serif body. Hand-feel illustration alongside data viz. Numbers feel typeset. Charts and illustrations coexist — the page has voice, not just data.

## Reference Phrasing for OpenAI
Lead the prompt with one of:

- "A magazine-style data infographic in the editorial tradition of The Economist or NYT graphics — serif headlines, illustrative elements alongside data visualization."
- "An editorial infographic with magazine typography (serif headlines, sans-serif body), stylized illustrations supporting the data, sophisticated color usage."
- "A data journalism infographic in newspaper graphics-desk style with serif display type, illustrative details, and confident chart design."

## Subject Treatment
- Serif headline at the top (large, typeset feel).
- Body text in clean sans-serif.
- One or two illustrated elements that support but don't dominate the data.
- Charts have an editorial polish: clean axes, deliberate labels, no chart-junk.
- Stylized illustrations are painterly but restrained, similar to editorial illustration but in service of the data.

## Composition Notes
Best with `vertical-stack`, `headline-and-illustration`, `chart-with-callouts`.

The illustration sits alongside the data, never replacing it.

## Palette Pairings
Best with: `bone-and-rust`, `velvet-financial`, `paper-and-pencil`, `burnt-poster`.
Acceptable: any sophisticated 3-4 color palette.

## Things to Avoid in Prompts
- "Cartoonish", "playful", "casual"
- All-sans-serif typography (lose the editorial voice)
- Multiple illustration styles competing
- Decorative chart junk

## Example Prompt Skeleton

```
A magazine-style editorial infographic in the tradition of The Economist or NYT graphics. Serif headline at top: "[HEADLINE]". One painterly illustration supporting the theme. Two data sections with chart elements: [DATA 1], [DATA 2]. Numbers rendered as typeset display type. Body text in clean sans-serif. Palette: [PALETTE with hex codes]. 2:3 portrait aspect ratio, Pinterest pin format. Text must be legible and correctly spelled.
```

## Best For
- Topic infographics tied to a Medium essay
- Editorial commentary with data
- Posts where voice matters as much as numbers
- Annual review / state-of-the-industry visualizations

## Text Rendering Notes (gpt-image-2)

This style is designed for gpt-image-2, which has strong text rendering. To get the best results:
- Specify the exact text you want in quotes within the prompt.
- Use one or two clear typeface families. Mixing more than two breaks the design.
- Numbers and headlines should be larger than body copy by 2-4x — make this explicit in the prompt.
- For multi-section infographics, name each section's heading and body content explicitly. The model handles structured prompts better than vague layout descriptions.
- Avoid abbreviations or made-up symbols in headlines; the model renders standard English most reliably.
