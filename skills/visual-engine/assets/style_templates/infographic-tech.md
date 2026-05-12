# Style: infographic-tech

## Visual Fingerprint
Dashboard-inspired infographic with a dark or light tech aesthetic — think Linear's brand graphics, Vercel's status pages, or a SaaS product launch announcement. Monospace or grotesque sans typography. Subtle gradients, soft glows on accent elements. Geometric precision throughout. Numbers feel like KPI cards.

## Reference Phrasing for OpenAI
Lead the prompt with one of:

- "A modern tech-product infographic in the style of Linear or Vercel — dashboard-inspired, monospace and grotesque typography, soft accent glows, geometric precision."
- "A SaaS product infographic with dashboard aesthetics, KPI-card layout, subtle gradients on accent elements, and clean technical typography."
- "A technical infographic styled like a developer-tool brand graphic: monospace numerics, grotesque sans display type, geometric icons, accent-color highlights."

## Subject Treatment
- Each stat is presented as a "KPI card" — number large, label small, often inside a subtle bordered or color-blocked box.
- Charts feel like dashboard widgets — line sparklines, bar comparisons, progress rings.
- Accent color appears 1-2 times for emphasis (a key stat, a positive trend, etc.).
- Icons are geometric and precise — no hand-drawn feel.
- Background is either deep dark (charcoal or navy) or clean off-white.

## Composition Notes
Best with `grid-2x2`, `grid-3x1`, `vertical-stack`, `dashboard-layout`.

## Palette Pairings
Best with: `cold-architecture`, `midnight-circuit`, `midnight-circuit`.
Light variant: pair with `paper-and-pencil` + one neon accent.
Dark variant: pair with `midnight-circuit` + cyan/green accent.

## Things to Avoid in Prompts
- "Painterly", "watercolor", "warm"
- Photographic elements
- Decorative ornaments
- Serif typography (kills the tech feel)

## Example Prompt Skeleton

```
A tech-product infographic in the style of Linear or Vercel brand graphics. Headline: "[HEADLINE]". Three KPI cards in a vertical stack: [CARD 1 with stat and trend], [CARD 2], [CARD 3]. Monospace numerics, grotesque sans display type. One accent color used 2-3 times for emphasis. Subtle glow on accent elements. Palette: [PALETTE with hex codes]. 2:3 portrait aspect ratio, Pinterest pin format. Text must be legible and correctly spelled.
```

## Best For
- Product launch announcements
- SaaS metric snapshots
- Developer-tool comparisons
- Technical announcements (release notes, changelog highlights)
- Startup metrics ("Year in review" / "Q3 wrap-up")

## Text Rendering Notes (gpt-image-2)

This style is designed for gpt-image-2, which has strong text rendering. To get the best results:
- Specify the exact text you want in quotes within the prompt.
- Use one or two clear typeface families. Mixing more than two breaks the design.
- Numbers and headlines should be larger than body copy by 2-4x — make this explicit in the prompt.
- For multi-section infographics, name each section's heading and body content explicitly. The model handles structured prompts better than vague layout descriptions.
- Avoid abbreviations or made-up symbols in headlines; the model renders standard English most reliably.
