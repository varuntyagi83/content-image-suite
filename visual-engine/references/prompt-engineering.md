# Prompt Engineering for Gemini Nano Banana Pro

Gemini 3 Pro Image (codename Nano Banana Pro) responds best to prompts that combine: (1) a clear subject, (2) a named visual style, (3) explicit color palette with hex codes, (4) composition direction, (5) lighting and mood, (6) technical specs, (7) what to avoid.

## Skeleton

```
[STYLE DECLARATION]. [SUBJECT, with specifics]. [COMPOSITION]. [PALETTE with hex codes]. [LIGHTING & MOOD]. [TECHNICAL SPECS]. [NEGATIVES].
```

Aim for 80-150 words. Below 80 produces vague results; above 200 starts contradicting itself.

## Section-by-Section

### Style Declaration (open with this)
Use specific art-historical or industry references. Pull this from the relevant style template.

Good: "Editorial illustration in the style of contemporary New Yorker magazine art, painterly with bold flat shapes."
Bad: "Nice illustration."

### Subject (the most important part)
Be concrete. Gemini renders "a woman in her 40s sitting at a wooden desk reviewing financial documents, holding a red pen" much better than "a person thinking about money."

If the post is about a metaphor (e.g. "the death of attention"), don't draw the metaphor literally — draw a person experiencing it. A person staring at a phone surrounded by faded notification bubbles, not a literal grave.

### Composition
Use the named compositions from the rotation rules, with the Gemini phrasing column.

### Palette
Always include hex codes when available.

Good: "Palette restricted to: cobalt blue (#2C3DD7), coral pink (#FF6B7A), soft cream (#F5EBD9), deep ink (#14132A). No other colors."
Acceptable: "Palette: cobalt blue, coral pink, soft cream, deep ink."

### Lighting & Mood
One sentence. "Soft afternoon light from the left, long shadows, contemplative mood."

### Technical Specs
- Aspect ratio: explicit (16:9 hero, 4:3 inline)
- "High detail, sharp focus, professional editorial quality"

### Negatives
End with what to avoid. Common ones:
- "No text, no logos, no watermarks."
- "Avoid generic stock photo aesthetics."
- "No cliché AI imagery (glowing brains, blue circuit lines, robot hands typing)."

## Full Example

> Editorial illustration in the style of contemporary New Yorker magazine art, painterly with bold flat shapes and confident line work. A mid-30s woman sits at a vintage wooden desk reviewing a tall stack of paper invoices, expression skeptical, holding a red pen. The desk is cluttered with coffee cups and a brass lamp. Subject positioned in the left third of the frame, large negative space on the right showing a softly blurred office interior. Palette restricted to: bone white (#F0EAD8), rust orange (#B65A2E), forest green (#34503C), charcoal (#2A2823). Soft afternoon light from the upper-left, long shadows, contemplative mood. 16:9 aspect ratio, high detail, sharp focus, editorial magazine quality. No text, no logos, no watermarks, no generic stock photo aesthetics.

## Things Gemini Does Poorly

- **Text in images.** Letters get mangled. If text is required, ask for "a single hand-lettered word reading [WORD]" and accept retries.
- **Hands.** Improving but inconsistent. Obscure them or accept retries.
- **Brand logos.** Will not render recognizably; describe the brand category instead.
- **Specific real people.** Refuses or produces generic likenesses. Describe an archetype.
- **Charts with real data.** Invents the data. Use a real charting tool.

## Iteration Strategy

When a generation is off, the highest-impact single change is usually:
1. **Tighten the subject description** (more specific, more concrete)
2. **Add explicit hex codes** to the palette
3. **Add an art-historical reference** ("in the style of [named illustrator/movement]")

Do NOT add adjective stacking ("beautiful, stunning, masterpiece"). It makes Gemini output worse, not better.
