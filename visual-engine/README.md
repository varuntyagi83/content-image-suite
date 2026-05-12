# visual-engine

The shared library for the Content Image Suite. Not a standalone skill (no `SKILL.md`). Used by the orchestrator and all five platform image generators.

## What lives here

```
visual-engine/
├── scripts/
│   ├── constants.py              Style/palette/composition catalogs
│   ├── platforms.py              PlatformConfig registry (5 platforms)
│   ├── rotation.py               Rotation engine (parameterized per platform)
│   ├── manifest_io.py            v2 manifest read/write + fuzzy match
│   ├── prompt_builder.py         Build Gemini prompts from structured inputs
│   ├── fal_client_wrapper.py     fal.ai integration
│   ├── engine.py                 CLI entry point
│   ├── migrate_v1_to_v2.py       Migration script for legacy manifests
│   └── __init__.py
├── references/
│   ├── palettes.md               12 color palettes with hex codes
│   ├── subject-extraction.md     3-question protocol
│   ├── iteration-vocabulary.md   User-language → engine-action mapping
│   └── prompt-engineering.md     Style and prompt-building principles
├── assets/style_templates/
│   ├── editorial.md
│   ├── cinematic.md
│   ├── isometric.md
│   ├── collage.md
│   ├── neon-tech.md
│   ├── hand-drawn.md
│   ├── minimalist.md
│   └── retro-print.md
└── tests/
    └── 157 pytest tests across rotation, manifest, prompt builder, CLI, migration
```

## CLI reference

The `engine.py` CLI is the surface that platform skills invoke. All commands output JSON to stdout.

```bash
# List registered platforms
python engine.py platforms

# Run rotation for a platform
python engine.py rotate \
    --manifest path/to/manifest.json \
    --platform medium \
    [--post-type technical] \
    [--locked-style isometric] \
    [--locked-palette electric-dusk]

# Compute shared identity across multiple platforms
python engine.py shared-identity \
    --manifest path/to/manifest.json \
    --platforms medium,linkedin,twitter \
    [--post-type technical]

# Build a Gemini prompt
python engine.py build-prompt \
    --platform medium --format hero \
    --style editorial --palette bone-and-rust \
    --composition centered-subject \
    --subject "A woman at a wooden desk reviewing invoices"

# Generate an image via fal.ai (requires FAL_KEY)
python engine.py generate \
    --prompt "..." --aspect 16:9 --output /path/to/image.png

# Manifest operations
python engine.py manifest get --manifest path.json [--summary]
python engine.py manifest find --manifest path.json --title "..." [--threshold 0.80]
python engine.py manifest upsert --manifest path.json --title "..." --style ... --palette ...
python engine.py manifest add-output --manifest path.json --slug ... --platform ... \
    --format ... --compositions "slot=name|||..." --prompts "slot=text|||..."
python engine.py manifest validate --manifest path.json
```

## Tests

```bash
cd visual-engine
python3 -m pytest tests/ -v
```

157 tests covering platforms, rotation, manifest IO, prompt builder, migration, and CLI.

## Adding a new platform

1. Add a `PlatformConfig` instance in `scripts/platforms.py` and register it in `REGISTRY`.
2. Decide rotation philosophy and windows.
3. Decide preferred/avoided styles.
4. Add output formats with their aspect ratios.
5. Write a new `SKILL.md` in a sibling folder (e.g. `tiktok-image-generator/SKILL.md`) that delegates to the engine just like the other platform skills do.

No engine code needs to change.

## Adding a new style

1. Create `assets/style_templates/<name>.md` following the pattern of the existing ones (must include a `## Reference Phrasing for Gemini` section).
2. Add the style name to `ALL_STYLES` in `constants.py`.
3. Add it to `STYLE_PALETTE_AFFINITY` (recommend 2-4 palettes).
4. Update platform `preferred_styles` / `avoided_styles` as needed.
5. Add a test in `test_prompt_builder.py::TestLoadStyleTemplate::test_loads_all_*_styles`.

## Adding a new palette

1. Add a section to `references/palettes.md` following the pattern:
   ```
   ## <name>: <one-sentence description>
   - Color Name #HEXCODE
   - Color Name #HEXCODE
   ```
2. Add the palette ID to `ALL_PALETTES` in `constants.py`.
3. Optionally add it to `STYLE_PALETTE_AFFINITY` entries.

## License

Bundle ships as-is.
