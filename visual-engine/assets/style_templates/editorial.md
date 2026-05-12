# Style: editorial

## Visual Fingerprint
Magazine illustration in the tradition of The New Yorker, The Atlantic, and The New York Times Magazine. Painterly but graphic. Bold flat shapes with confident line work. Stylized human figures, often slightly elongated. The illustration interprets the article rather than depicting it literally.

## Reference Phrasing for Gemini
Lead the prompt with one of:

- "Editorial illustration in the style of contemporary New Yorker magazine art, painterly with bold flat shapes and confident line work."
- "Editorial magazine illustration, gouache-painted aesthetic, stylized figures, sophisticated color blocking."
- "Op-ed style illustration with hand-drawn texture, bold compositional choices, conceptual rather than literal."

## Subject Treatment
- Use stylized figures, not photorealistic ones.
- **Face treatment depends on the subject's role:**
  - If the subject is a **named protagonist** (the post's author, "I", a founder, a specific person being profiled), give the figure a clear face with visible features and a readable expression. Stylized, not photorealistic, but recognizable as a person. The face anchors the personal voice.
  - If the subject is a **generic figure** (a worker, a user, anyone, a crowd, a person playing a role), faces can be partial, abstracted, obscured, or turned away. This is editorial convention and works well.
  - If unsure, default to **partial face** — three-quarter angle, one eye visible, expression readable. Avoid pure silhouette unless the post is explicitly about anonymity.
- Objects rendered with slight stylization (perspective bent for emphasis).
- Conceptual metaphors work well IF they are visually concrete (e.g. a person climbing a staircase made of laptops, not "the abstract idea of progress").

## Composition Notes
Editorial illustration loves negative space and asymmetry. Pair this style with `rule-of-thirds-left/right`, `negative-space-dominant`, `split-frame`, or `frame-within-frame`.

Avoid `centered-subject` — it works against the editorial feel.

## Palette Pairings
Best with: `bone-and-rust`, `paper-and-pencil`, `burnt-poster`, `velvet-financial`.
Acceptable with: any palette except the very high-saturation ones (`tropical-ink`, `midnight-circuit`).

## Things to Avoid in Prompts
- "Photorealistic" (contradicts the style)
- "Highly detailed" (editorial illos are intentionally restrained)
- Cliché editorial tropes: a chess piece tipping over, a maze, a lightbulb, gears

## Example Prompt Skeleton

```
Editorial illustration in the style of contemporary New Yorker magazine art, painterly with bold flat shapes. [SUBJECT with one specific human action and one specific object]. [COMPOSITION]. Palette: [PALETTE with hex codes]. Soft directional lighting, contemplative mood. 16:9 aspect ratio, magazine cover quality. No text, no logos, no clichéd metaphors.
```

## Best For
- Opinion pieces and essays
- Cultural commentary
- Personal narratives with a thesis
- Posts that argue a position
