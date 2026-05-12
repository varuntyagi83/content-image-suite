# Iteration Vocabulary

How to interpret user feedback after generating an image. Each row maps a category of feedback to a specific prompt modification.

## The Core Principle

Iterations should change exactly what the user asked to change and **leave everything else alone**. If the user says "make her older," do not also change the lighting, composition, or palette. Surgical edits, not rewrites.

When modifying the prompt, keep the same skeleton (style declaration, palette, composition, technical specs, negatives) and only change the relevant section.

## Feedback Categories

### Approval / progression

The skill must distinguish three signals carefully. These are not synonyms.

**Approval-but-undecided** (user likes the current image but hasn't said what's next):
| User says |
|---|
| "looks good", "nice", "that works", "good", "yep", "yes" |
| "I like it", "this is good", "decent", "OK" |
| "great", "perfect", "love it" (when said in isolation, without "ship it") |

→ Action: ask one short disambiguation: "Continue with 3 inline section images, or call it done here?" Do NOT save yet. Do NOT generate the next image without confirmation.

**Continue** (user wants the next image in the sequence):
| User says |
|---|
| "keep going", "next", "next one", "let's do the rest" |
| "do the inline ones", "do the section images", "continue" |
| "yes, do the inline images" (in response to the disambiguation) |
| "yes continue" |

→ Action: generate the next inline image.

**Complete** (user is done with this content piece):
| User says |
|---|
| "we're done", "that's enough", "stop here" |
| "ship it", "let's ship" |
| "save it", "save", "we're done here" |
| "call it done", "done", "that's it" |
| "no more", "no inlines", "just the hero", "skip the inlines" |
| "yes done" (in response to the "done?" disambiguation) |

→ Action: write the manifest, give the closing line, end the session.

**Critical: the skill must NOT close without saving.** If user signals Complete at any point, the manifest write happens BEFORE the closing line. If user trails off without responding to the disambiguation, do NOT save — half-finished sessions stay unsaved by design (Q1 decision).

### Lighting tweaks
| User says | Interpretation | Action |
|-----------|---------------|--------|
| "darker" | Reduce lighting intensity | Add "low-key lighting, deep shadows" to prompt |
| "lighter", "brighter" | Increase lighting | Add "bright even lighting" |
| "warmer" | Shift toward warm tones | Add "warm color grade, golden tone" |
| "cooler" | Shift toward cool tones | Add "cool color grade, blue tone" |
| "more contrast" | Increase contrast | Add "high contrast, strong shadow definition" |
| "softer" | Reduce contrast | Add "soft diffused lighting, low contrast" |
| "more dramatic lighting" | Stronger directional light | Add "dramatic single-source lighting from [side]" |

### Subject tweaks (people)
| User says | Action |
|-----------|--------|
| "make her/him older" | Adjust age description by ~10 years upward |
| "younger" | Adjust by ~10 years downward |
| "more serious" | Add "serious expression, no smile" |
| "happier", "more relaxed" | Add "warm relaxed expression" |
| "different ethnicity" | Ask user to specify, or generalize ("of any background") |
| "more confident" | Adjust posture cue: "upright posture, direct gaze" |
| "less generic" | Add 1-2 specific details (a specific clothing item, an unusual prop) |

### Subject tweaks (objects/scenes)
| User says | Action |
|-----------|--------|
| "more cluttered" / "messier" | Add "cluttered surroundings, scattered objects" |
| "cleaner" / "more minimal" | Strip to fewer objects; add "minimal surroundings" |
| "different setting" | Ask user where, or pick a related-but-different environment |
| "more realistic" | Move toward photographic style (may require style change) |
| "more stylized" | Move toward illustration style |

### Composition tweaks
| User says | Action |
|-----------|--------|
| "different composition" | Re-pick from `allowed_compositions["hero"]`, exclude the current one |
| "zoom out" / "wider shot" | Add "wide shot, more environment visible" |
| "zoom in" / "closer" | Add "tight close-up, subject filling frame" |
| "different angle" | Switch to one of: `worms-eye-view`, `birds-eye-view`, `diagonal-motion` |
| "more centered" | Switch to `centered-subject` |
| "more off-center" | Switch to `rule-of-thirds-left/right` or `negative-space-dominant` |

### Style tweaks
| User says | Action |
|-----------|--------|
| "different style" | Re-pick from `allowed_styles`, ask user if they have a direction |
| "more painterly" | Switch to `editorial` or `hand-drawn` |
| "more photographic" | Switch to `cinematic` |
| "more graphic / flat" | Switch to `minimalist` or `retro-print` |
| "more retro" | Switch to `retro-print` or `collage` |
| "more techy" | Switch to `isometric` or `neon-tech` |

### Palette tweaks
| User says | Action |
|-----------|--------|
| "different colors" | Re-pick from `allowed_palettes` |
| "less colorful" / "more muted" | Switch to `monochrome-noir`, `cold-architecture`, or `paper-and-pencil` |
| "more colorful" | Switch to `tropical-ink`, `electric-dusk`, or `burnt-poster` |
| "more contrast in colors" | Switch to a high-contrast palette like `midnight-circuit` |
| Specific color request ("more blue", "less pink") | Adjust palette description to emphasize/de-emphasize the specified color |

### Subject re-extraction
| User says | Action |
|-----------|--------|
| "missing the point", "doesn't capture it" | Re-run subject extraction. Ask: "What's the part of this you want the image to land on?" |
| "different subject entirely" | Re-extract; consider switching from literal to metaphorical or vice versa |
| "more like the article's vibe" | Push subject toward emotional reading rather than literal |

### Reference-based feedback
| User says | Action |
|-----------|--------|
| "more like [named artist/movie/aesthetic]" | Add the reference to the prompt: "in the style of [reference]". Tell user this is a one-time override, not added to the rotation |
| "like the last post's hero" | Acknowledge but warn: "That would break the rotation. Want me to do it anyway as a one-off?" |

## Multi-Tweak Requests

If the user lists multiple changes in one message ("make her older AND darker AND different composition"), apply all of them in a single regeneration. Don't make the user wait three rounds for three changes.

## Ambiguous Feedback

When you're unsure what the user means, ask **one** short question:

- "Different *how*?" — for vague style or composition asks
- "What's the part you want it to land on?" — for "missing the point"
- "More toward [X] or [Y]?" — when there are two plausible directions

Never ask more than one clarifying question. If still unclear, make a guess and explicitly say so: "I'll try [X]; tell me if I went the wrong way."

## When to Stop Iterating

After 5 iterations on a single image without approval, stop and ask:

> "Five tweaks in. Want to start fresh with a different style or subject, or push for a 6th tweak?"

This breaks dead-end loops where small tweaks won't get to the user's actual destination.

## What NOT to Do

- Do not silently change things the user didn't ask about.
- Do not re-explain the rotation engine when iterating.
- Do not show the full prompt diff between iterations. Show the new image and a one-line summary of what changed.
- Do not write to the manifest after every iteration. Only after the user signals completion ("we're done").
