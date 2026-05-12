# Palette Catalog

Twelve named palettes. Each has a stable `palette_id` used in the manifest. Hex codes are explicit so Gemini gets precise color guidance.

When writing a prompt, include the palette like:
> "Palette: warm clay (#C97B4A), bone white (#F0EAD8), deep navy (#1E2B4D), faded sage (#9CAA8C)."

## 1. electric-dusk
**Mood:** Modern tech, optimistic, slightly futuristic
- Cobalt #2C3DD7
- Coral pink #FF6B7A
- Soft cream #F5EBD9
- Deep ink #14132A

## 2. bone-and-rust
**Mood:** Earthy, grounded, editorial
- Bone white #F0EAD8
- Rust orange #B65A2E
- Forest #34503C
- Charcoal #2A2823

## 3. midnight-circuit
**Mood:** Cyberpunk, AI, after-hours
- Midnight blue #0A1428
- Neon magenta #FF1F8F
- Electric cyan #00E0FF
- Off-black #050810

## 4. sunwashed
**Mood:** California, breezy, lifestyle
- Peach #F4B89A
- Sky blue #A8D5E5
- Mustard #D4A847
- Off-white #FBF6EE

## 5. monochrome-noir
**Mood:** Serious, journalistic, restrained
- Pure white #FFFFFF
- Charcoal #2B2B2B
- Mid-grey #8A8A8A
- Single accent: blood red #B82A2A

## 6. tropical-ink
**Mood:** Bold, playful, illustrative
- Jungle green #1F5C3D
- Tangerine #F58A3D
- Hot pink #E83F7C
- Deep navy #122448

## 7. paper-and-pencil
**Mood:** Hand-drawn, intimate, sketchbook
- Cream paper #F8F1E2
- Graphite #4A4742
- Faded red #C04E47
- Indigo wash #4A5B7A

## 8. terminal-green
**Mood:** Hacker, retro-tech, command line
- Black #000000
- Phosphor green #33FF33
- Amber #FFB000
- Off-white #E8E8E8

## 9. soft-laboratory
**Mood:** Scientific, calm, clinical-but-warm
- Lab white #F4F6F2
- Mint #A4D4B4
- Slate #5C7080
- Soft coral #E89B8C

## 10. burnt-poster
**Mood:** Risograph, retro-print, listicle
- Cream #F2EAD3
- Burnt orange #D85B30
- Cobalt #2A4FB0
- Ink black #1A1A1A

## 11. velvet-financial
**Mood:** Premium, business, money
- Bottle green #1B4332
- Champagne #E8C99B
- Deep burgundy #5A1F2A
- Off-white #F4EFE6

## 12. cold-architecture
**Mood:** Minimalist, technical, brutalist
- Concrete grey #A8A8A0
- Steel blue #5C7A8C
- Off-white #EEEEE8
- Black #1A1A1A

## Style Pairing (Used as Tiebreaker)

| Style | Top palettes |
|-------|--------------|
| editorial | bone-and-rust, paper-and-pencil, burnt-poster, velvet-financial |
| cinematic | monochrome-noir, electric-dusk, velvet-financial, bone-and-rust |
| isometric | cold-architecture, electric-dusk, soft-laboratory, terminal-green |
| collage | burnt-poster, tropical-ink, sunwashed, paper-and-pencil |
| neon-tech | midnight-circuit, terminal-green, electric-dusk |
| hand-drawn | paper-and-pencil, sunwashed, bone-and-rust |
| minimalist | cold-architecture, monochrome-noir, soft-laboratory |
| retro-print | burnt-poster, tropical-ink, terminal-green |

These are tiebreakers; cross-pairings are fine and often interesting.

## Adding New Palettes

To add a palette, append a new section here using the heading format `## N. palette-id`. The validator picks it up automatically.
