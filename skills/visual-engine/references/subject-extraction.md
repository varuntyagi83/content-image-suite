# Subject Extraction Protocol

Deriving a concrete, specific subject from a blog post is the single most important step. Bad subjects produce bad images regardless of style, palette, or composition. This document is a worked playbook.

## The Three-Question Protocol

For any post, answer these silently before doing anything else:

1. **What is the post literally about?** One sentence. No metaphor.
2. **What is the post emotionally about?** One sentence. The feeling.
3. **What is one concrete scene that holds both?** A specific moment, a person doing a specific thing, or an object in a specific state.

Question 3's answer becomes the subject. The first two are scaffolding to get there.

## What "Concrete" Means

A subject is concrete when you could describe it to a sketch artist and they could draw it without asking follow-up questions.

| Abstract (BAD) | Concrete (GOOD) |
|----------------|-----------------|
| "The concept of focus" | "A woman in her 40s with reading glasses bent over a single sheet of paper, surrounded by closed laptops" |
| "Information overload" | "A man in a kitchen, every surface covered in stacked open books and printouts, holding a coffee cup, exhausted expression" |
| "The death of attention" | "A teenager on a couch staring at a phone, faded notification bubbles drifting up from the screen like smoke" |
| "Building in public" | "A woodworker in a glass-walled workshop visible from the street, mid-cut on a wooden chair, passersby on the sidewalk watching" |
| "AI replacing developers" | "A vintage office chair with a coffee cup still steaming on the armrest, the desk monitor glowing with code that is writing itself line by line" |

The right column commits. The wrong column hedges.

## Worked Examples

### Example 1: Technical How-To

**Post:** "How to cut BigQuery costs by 47% in six weeks"

1. Literally about: a step-by-step process for reducing cloud database query costs.
2. Emotionally about: the satisfaction of taming runaway infrastructure spend.
3. Concrete scene: **A row of glowing server racks viewed from below, with a fuel gauge mounted on the side of the central rack, the needle moving from red toward green.**

Why this works: it's specific (server racks, fuel gauge, needle), the metaphor is doing real work (cost = fuel), and a Gemini prompt can render it precisely.

### Example 2: Personal Essay

**Post:** "What ten years of writing on the internet taught me about audience"

1. Literally about: lessons learned from a decade of online writing.
2. Emotionally about: humility, the strangeness of speaking into a void that sometimes responds.
3. Concrete scene: **A person at a kitchen table at night, single lamp on, typing on a laptop, with the soft blue glow of a window in the background showing distant city lights — many of which are also windows with people at them.**

Why this works: it's a portrait of the act, with the audience visualized literally.

### Example 3: Hot Take

**Post:** "Stop hiring senior engineers"

1. Literally about: an argument that companies over-prioritize senior engineering hires.
2. Emotionally about: provocation, contrarianism.
3. Concrete scene: **A LinkedIn-style résumé pinned to a wall, riddled with darts, with one dart that has missed entirely and stuck in the wall behind it.**

Why this works: provocative, visual, and specific. A safer scene would be "an engineer at a desk" — but the post doesn't deserve safe.

### Example 4: Listicle

**Post:** "10 books that changed how I think about money"

1. Literally about: book recommendations on personal finance and economics.
2. Emotionally about: the quiet thrill of intellectual recalibration.
3. Concrete scene: **A stack of ten books leaning slightly, with a coffee cup balanced on top, on a wooden surface; the spine of the bottom book is faintly cracked.**

Why this works: simple, evocative, the cracked spine adds interest, and it's perfect for risograph or hand-drawn treatment.

### Example 5: Pure Abstract (the Hard Case)

**Post:** "Why most strategy is just inertia in costume"

1. Literally about: an argument that corporate strategy documents often dress up the status quo as deliberate choice.
2. Emotionally about: cynicism, recognition, "I've seen this before."
3. Concrete scene: **A horse on a treadmill wearing a corporate ID badge, in a gleaming office hallway, motion-blurred to show fast running but no actual movement; framed strategy charts on the wall behind.**

Why this works: the metaphor is committed to. Resist the urge to be tasteful with abstract subjects — Gemini handles literal, slightly absurd renderings of metaphors better than vague evocations.

## The Fallback Hierarchy

If the three-question protocol doesn't yield a concrete scene, use this in order:

1. **Representative object in a specific state.** A single open notebook with a coffee ring. A hard hat on a stack of blueprints. A microphone on an empty stage. The object should appear in the post or be obviously connected to its topic.

2. **Person performing a specific action.** A woman tying her shoelaces before a run. A man sealing a cardboard box. A child reaching for a high shelf. The action should mirror the post's emotional arc.

3. **Environment that holds the mood.** An empty stadium at dusk. A morning kitchen with one place setting. A subway car with a single passenger. Use only for posts where mood is the entire payload.

4. **Last resort: the writer's perspective.** A back-of-shoulder view of someone reading the post on their phone, in a specific environment that fits the topic.

## What to Do When the Post is Vague

Some posts are intentionally vague — meditations, philosophical musings, koans. In these cases:

- Pick a single specific image from the writing, even if it's a brief metaphor in paragraph three. Use that.
- If there's nothing, ask the user one question: "What's one image, scene, or object that captures this for you?" One question, then build from the answer.
- Do not generate a vague image to match a vague post. The image should be a specific anchor for the reader.

## Subject Themes for the Manifest

After settling on the subject, extract 3-5 lowercase tag-style themes that describe what the image will literally show. These go into the manifest's `subject_themes` array and feed the rotation engine.

For "A row of glowing server racks viewed from below, with a fuel gauge…":
- `subject_themes`: `["server racks", "fuel gauge", "underglow lighting", "industrial interior"]`

For "A person at a kitchen table at night, single lamp on…":
- `subject_themes`: `["kitchen table", "night scene", "single lamp", "person typing", "window view"]`

These tags get checked against the last 3 posts. If "server racks" appears in the rotation history, you cannot use it again until 3 posts have passed.

## Common Failure Modes

- **Hedging.** "A figure that could be a person or might be a robot, in a setting that suggests an office but isn't quite." Pick one. Commit.
- **Listing.** "A laptop, a coffee cup, a notebook, and a phone, with some plants and maybe a window." Compose, don't list. Pick the focal element and put the others around it.
- **Adjective stacking.** "A beautiful, stunning, masterpiece scene of a thoughtful person." Cut every adjective that doesn't change what's literally drawn.
- **Mistaking specificity for detail.** "A 47-year-old senior software engineer named David at his Herman Miller chair…" — that's not specificity, it's noise. Specificity is "a woman in her 40s, glasses pushed up onto her head, mid-laugh." Concrete details, not factoids.

## Avoiding text leakage in images

Gemini 3 Pro renders text very well — so well that subjects which look like lists of labels get drawn as captions on the image. The engine detects this and escalates negative prompts automatically, but you can also avoid the trigger by phrasing subjects as continuous scenes rather than label lists.

### Patterns that cause text leakage

**Comma-separated capitalized phrases.** Gemini treats these as labeled entities and draws them as captions.
- BAD: "four data streams: campaign metrics, competitor intelligence, creative output, reporting"
- GOOD: "four ribbons of data flowing into a central dashboard from different directions, each ribbon a different color"

**Quoted text.** Anything in quotes will be rendered literally.
- BAD: 'a sign that reads "OPEN" hanging in a window'
- GOOD: "a hand-lettered sign hanging crooked in a shop window"

**Discrete UI categories.** Listing UI sections gives Gemini label hints.
- BAD: "a dashboard with sections for analytics, settings, and reports"
- GOOD: "a single glowing interface divided into three rough zones, each with different visual rhythm"

### Visual proxies for abstract concepts

When a section of your post is about an abstraction (competitor research, content workflows, reporting cadence), don't extract the abstraction as the subject. Find a visual proxy.

| Abstract concept (BAD as subject) | Visual proxy (GOOD as subject) |
|---|---|
| "Competitor ads" | "Small screen-rectangles with text fragments and brand logos partially visible, stacked in an uneven grid" |
| "Reporting workflow" | "A single sheet of paper with handwritten arrows and boxes, half-finished, coffee ring at the corner" |
| "Performance metrics" | "A line graph drawn in chalk on a slate surface, the line rising past a hand-drawn target marker" |
| "Brand voice" | "A typewriter mid-sentence, one specific phrase visible on the paper, pencil-marked edits in the margin" |
| "Customer feedback" | "A wall of sticky notes in three colors, some torn, one in the center circled in red marker" |

The proxy is concrete enough to draw but doesn't invite Gemini to caption it.

### When the engine detects label risk

If `build-prompt` returns `"label_risk_detected": true`, the engine has already escalated the no-text negative. Two things happen:
1. The prompt now includes an aggressive zero-text directive at the start of the negatives section.
2. The skill should mention this to the user once: "Your subject has label-like phrasing — I added a strong no-text negative. If text still appears, we'll rephrase the subject."

This is preventive. The escalation succeeds most of the time. When it doesn't, the fix is on the subject side: replace the labels with a visual proxy and re-run.

## Protagonist Identity

When the post is in first person ("I built X", "I spent years doing Y", "Here's what I learned") OR profiles a specific named person, the subject extraction should treat the protagonist as a **specific identifiable figure**, not a generic worker.

### Detecting first-person / protagonist-driven posts

Signals the post has a protagonist whose identity matters:
- "I" pronouns throughout
- First-person founder voice ("I built", "I noticed", "I got tired of")
- Direct profile of a named person ("How [Name] built [thing]")
- Personal essay format ("My years on the data team")

When detected, the subject should anchor the protagonist's presence. Don't say "a marketer at a desk" when the post is "I built Voltic" — say "a founder, mid-30s, focused expression, mid-thought at a desk." The face is recognizable, the moment is specific to them.

### Why this matters

Editorial illustration conventions default to face-obscuring (back of head, three-quarter turn, silhouette). That's correct for *generic* figures — a "user," a "customer," a "worker." It's wrong for *named protagonists* because it drains the emotional register the post is trying to land.

If your reader thinks "this article is from someone with a perspective," the image needs to convey that someone exists. A clear face does that. A silhouette doesn't.

### Subject patterns

| Post type | BAD subject (anonymizing) | GOOD subject (identifying) |
|---|---|---|
| First-person founder essay | "A marketing professional at a cluttered desk" | "A founder, mid-30s, focused expression, building something on a laptop in a sunlit room" |
| Personal narrative | "A figure on a couch staring at a phone" | "A woman in her late 20s, eyes locked on her phone, room dim except for the screen glow on her face" |
| Profile of a named person | "A worker at a workshop bench" | "A woodworker, salt-and-pepper beard, mid-cut on a chair, sawdust on his apron, expression of concentration" |

The right column commits to a person. The wrong column hedges into archetype.

### Compositions that show faces vs hide them

| Shows face well | Tends to hide face |
|---|---|
| centered-subject | overhead-flat-lay |
| rule-of-thirds-left/right (with the figure facing camera) | back-of-head silhouette |
| frame-within-frame (figure in foreground) | worms-eye-view (looking up past figure) |
| split-frame (figure on one side, facing camera) | pattern-repetition |

When the post has a protagonist, prefer the left-column compositions. When the post is conceptual or doesn't center a person, either column is fine.

### Caveat

This guidance applies to images that include a person. Many post sections don't — a section about "the screenshot graveyard" works fine as just a wall of screenshots, no figure needed. Don't insert a protagonist where the natural subject is an object or scene.

## Worked failure: the Voltic case

This is a real failure pattern worth internalizing.

**The post:** "I spent years on the data team watching marketing teams drown in fragmented workflows... I built Voltic because..."

**The wrong subject extraction (mid-2026 run):**
"A marketing desk split between left side chaos and right side order."

**Why it failed:** The subject describes the scene, not the narrator. The post is first person — the author is the protagonist. With no person in the subject, Gemini either omitted the figure entirely or added incidental figures that defaulted to editorial face-obscuring conventions (silhouettes, backs to camera, faces in shadow). The resulting image illustrated the workflow but not the voice.

**The right subject extraction:**
"A founder, mid-30s, focused expression, standing at the boundary between a chaotic five-screen workstation on the left and a single calm dashboard on the right."

**What changed:**
- The protagonist is named first (a founder, mid-30s)
- An expression is specified (focused)
- The action is concrete (standing at the boundary)
- The scene is still there, but it surrounds the figure rather than replacing them

This is the difference between an image that illustrates the post's *idea* and an image that illustrates the post's *voice*. First-person posts need the second one.

**The decision rule:**
1. Does the post use "I" repeatedly in the opening? → first person → protagonist subject required.
2. Does the post profile a specific named person? → protagonist subject required.
3. Anything else → conceptual subject is fine.

When in doubt, ask: "If I removed the figure from this scene, would the post still make sense?" For first-person posts, the answer is no — removing the protagonist removes the voice. For conceptual posts, the answer is yes — the scene speaks on its own.
