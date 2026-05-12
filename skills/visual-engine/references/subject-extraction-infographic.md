# Infographic Subject Extraction

This reference is for the infographic skill specifically. The illustration-platform skills (Medium, LinkedIn, Twitter, Instagram, Meta) use `subject-extraction.md` and extract *scenes*. Infographics extract *data stories*.

## The core difference

Illustration subject: "A founder at a desk surrounded by chaotic monitors, mid-thought, focused expression."
Infographic subject: "Headline: 'The Five-Tool Trap'. Three sections, each showing one wasted hour of a marketer's morning."

The illustration subject describes what's visually in the frame. The infographic subject describes what's communicated by the frame.

## The three-question protocol for infographics

When the user gives you a topic, post, or data, answer these in order:

### 1. What is the headline?
One sentence, ideally 4-7 words. This is the largest text in the image. It should:
- Capture the post's thesis or the data's punchline
- Be confident and assertive, not hedged
- Avoid abbreviations or jargon the audience won't recognize

Bad: "Things to consider about marketing tool fragmentation"
Good: "The Five-Tool Trap"
Good: "Why Your Stack Is Slowing You Down"

### 2. What are the data points or sections?
Infographics work best with 3-5 sections. Each section needs:
- A label (1-3 words)
- A primary number, stat, or visual element
- A short body explanation (1-2 lines)

For a Voltic-style post, sections might be:
- Section 1: "Reports" — "2 hrs/day pulling from Supermetrics"
- Section 2: "Inspiration" — "847 saved screenshots, 0 acted on"
- Section 3: "Drafts" — "Copy in Jasper, then Canva, then Slack"

If the source content doesn't have explicit data, derive 3-5 *conceptual* sections that organize the argument:
- A how-to post: 3-5 steps
- A comparison: A vs B with 3-5 dimensions
- A trend piece: past / present / future
- A framework: 3-5 principles

### 3. What is the footer?
Optional, but useful for infographics meant to stand alone:
- The author/brand attribution ("by Varun Tyagi" or "voltic.ai")
- The data source if relevant ("Source: 2026 Marketing Stack Survey")
- The CTA if the infographic is promotional ("Try Voltic free at voltic.ai")

## The subject string format

Because gpt-image-2 handles structured prompts well, the subject string should be explicit and structured, not narrative. Use this template:

```
Headline: "[exact text]".
Section 1: title "[label]", number "[stat]", body "[1-line explanation]".
Section 2: title "[label]", number "[stat]", body "[1-line explanation]".
Section 3: title "[label]", number "[stat]", body "[1-line explanation]".
Footer: "[attribution]".
```

Example for the Voltic post:

```
Headline: "The Five-Tool Trap".
Section 1: title "Reports", number "2 HRS", body "pulling data from five tools every morning".
Section 2: title "Inspiration", number "847", body "screenshots saved, almost none used".
Section 3: title "Output", number "0%", body "of insights become ads in under a week".
Footer: "by Varun Tyagi · voltic.ai".
```

## When to use each composition

- `vertical-stack`: Default for Pinterest pins. Headline at top, sections stacked, footer at bottom.
- `grid-2x2`: For exactly 4 data points where each is roughly equal weight.
- `grid-3x1`: For 3 data points in a single column or row.
- `headline-and-body`: When there's one big stat or quote that dominates.
- `dashboard-layout`: For tech-style infographics with KPI cards.
- `headline-and-illustration`: For editorial-style infographics where one illustration anchors the data.
- `chart-with-callouts`: When the data is a single chart (bar, line, donut) with annotations.
- `print-grid`: For classic-style infographics with multiple small sections in a rigorous typographic layout.

## When the request is "summarize my Medium post as an infographic"

The infographic should NOT just be the post in image form. It should be the post's *thesis distilled to its essential numbers/comparisons/steps*. If you can't find numbers in the post, derive structural sections (steps, principles, comparisons).

If the user passes `--shared-identity` from a Medium post, use:
- The Medium post's locked style → mapped to the closest infographic-* style (editorial → infographic-editorial, neon-tech → infographic-tech, etc.)
- The Medium post's locked palette → reused as-is

## When the topic is standalone (no parent post)

Treat it as a topic-only request. The infographic stands alone. You have more freedom to pick style and palette. Confirm the headline and sections with the user before generating, since the data points are inferred rather than extracted.

## Bad vs good subject extraction

| Source content | Bad subject | Good subject |
|---|---|---|
| First-person founder essay about tool fragmentation | "A messy marketing workflow" | `Headline: "The Five-Tool Trap". Section 1: title "Reports", number "2 HRS"... [structured format]` |
| Tutorial on optimizing BigQuery costs | "BigQuery cost optimization tips" | `Headline: "Cut Your BigQuery Bill in Half". Section 1: title "Partition", number "60%"... [structured]` |
| Comparison of three AI models | "AI model comparison" | `Headline: "GPT-5 vs Claude Opus vs Gemini 3". Section 1: title "Coding", winner "Claude"... [structured]` |
