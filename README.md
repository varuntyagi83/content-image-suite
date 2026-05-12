# Content Image Suite

Generate platform-tuned, visually coordinated images for blog posts and social content using Gemini Nano Banana Pro (Gemini 3 Pro Image via fal.ai).

A bundle of seven Claude Code skills: one shared engine, one orchestrator, and five platform-specific generators (Medium, LinkedIn, Twitter, Instagram, Meta).

## What it does

You hand Claude a Medium draft, a LinkedIn post, a tweet, or just a topic. The suite:

1. Extracts a concrete visual subject from your content
2. Picks a style and palette that work for the target platform (or platforms)
3. Generates the image via fal.ai's Nano Banana Pro
4. Iterates with you in plain language ("make her older", "more punchy", "different composition")
5. Saves what it generated so the next post automatically picks something different

The result: a consistent personal visual identity that doesn't look like the same template AI carousel everyone else is shipping.

## Architecture

```
content-image-suite/
├── skills/                         All skill folders live here (Hermes tap layout, agentskills.io compatible)
│   ├── visual-engine/              Shared library (no SKILL.md, not a standalone skill)
│   │   ├── scripts/                Python modules + CLI
│   │   ├── references/             palettes.md, subject-extraction.md, etc.
│   │   ├── assets/style_templates/ Style templates (editorial, cinematic, etc.)
│   │   └── tests/                  Pytest tests
│   ├── content-image-orchestrator/ Optional top-level skill for multi-platform requests
│   ├── medium-image-generator/     Medium hero + inline (16:9 + 4:3)
│   ├── linkedin-image-generator/   LinkedIn cover (1.91:1) OR carousel (1:1, 5-10 slides)
│   ├── twitter-image-generator/    Tweet image (16:9) + thread card (1:1)
│   ├── instagram-image-generator/  Feed (1:1), Story/Reel (9:16), carousel
│   ├── meta-image-generator/       Feed image (1.91:1) + event cover
│   └── infographic-generator/      Pinterest pins, data posters (OpenAI gpt-image-2)
├── bin/                            suite.sh controller for /suite command
├── commands/                       Claude Code slash command definitions
├── install.sh                      Claude Code solo installer
├── install-team.sh                 Claude Code team installer (staged + symlink)
└── _templates/                     Shared templates (engine wrapper, etc.)
```

### Why this structure

Each platform has its own rotation philosophy, style biases, output formats, and norms. Trying to handle all five in one skill turned the skill prompt into a checklist nightmare. So:

- **Each platform is a first-class skill.** Use just LinkedIn if that's all you post on.
- **They share the visual-engine.** Rotation logic, palette parsing, prompt building, fal.ai integration — all in one place.
- **The orchestrator is optional.** Use it when you want one article imaged across 3+ platforms with coordinated style+palette. Skip it if you're working one platform at a time.

### The cross-platform manifest

A single JSON file (default: `<your-working-dir>/content-images/manifest.json`) tracks every image you've generated. Each entry is a "content piece" with:

- Canonical title and slug
- A `shared_identity` (one style + one palette)
- A `platform_outputs` block: one entry per platform you've imaged for, each with format, compositions, prompts, and file paths

This is why cross-session coherence works: you image a Medium hero today, come back three days later and ask for LinkedIn images of the same post, and the suite finds the existing entry (via fuzzy slug+title match) and uses the same style+palette automatically.

## Rotation philosophies (per platform)

| Platform | Philosophy | Style window | Palette window | Why |
|----------|-----------|--------------|----------------|-----|
| Medium | aggressive | 3 | 4 | Profile grid wants visible variety |
| LinkedIn | moderate | 2 | 3 | Feed moves fast; profile coherence matters less |
| Twitter | light | 1 | 2 | Twitter is ephemeral |
| Instagram | **consistency** | 0 | 0 | The grid IS the brand; lock to established look |
| Meta | light | 1 | 2 | Heterogeneous feed |

Instagram's "consistency mode" is the unusual one: after 3 posts using a similar style+palette, the engine locks to that look and stops rotating. Future posts get the same style+palette automatically.

## Install

The suite is authored to the [agentskills.io](https://agentskills.io/specification) open standard. The same SKILL.md files run unchanged in Claude Code, Hermes Agent, Codex CLI, Gemini CLI, and Cursor.

### Recommended: one-question setup

```bash
cd /path/to/content-image-suite
./setup.sh
```

`setup.sh` auto-detects which agent runtime is installed (Claude Code, Hermes Agent, or both), asks one question if ambiguous, persists the choice to `~/.content-image-suite/config`, and dispatches to the right installer. Re-runs are no-ops unless you pass `--reconfigure`. Bypass detection with `./setup.sh --force claude`, `--force hermes`, or `--force both`.

The three install paths below run automatically based on the choice. They are also callable directly if you prefer.

### Claude Code, solo install

```bash
cd /path/to/content-image-suite
./install.sh
```

Copies every skill folder from `skills/` into `~/.claude/skills/`, backing up any existing installations to a timestamped folder.

### Claude Code, team install (staged + selectable activation)

```bash
cd /path/to/content-image-suite
./install-team.sh                                # stage everything, activate core only
./install-team.sh --activate all                 # stage + activate everything
./install-team.sh --activate "linkedin,medium"   # stage + activate those two
```

Stages every skill into `~/.claude/skills-suite/` and symlinks only the active ones into `~/.claude/skills/`. Session-start token cost scales with what's symlinked, not what's staged. Toggle later without reinstalling:

```
/suite list                # show staged vs active + token cost
/suite enable linkedin     # activate a platform
/suite disable twitter     # deactivate a platform
/suite enable-all          # activate every staged skill
```

### Hermes Agent

The repo is structured as a Hermes "tap" — a curated GitHub-hosted skill collection. Add it once and Hermes treats the contents of `skills/` as installable skills:

```
hermes skills tap add varuntyagi83/content-image-suite
hermes skills install varuntyagi83/visual-engine
hermes skills install varuntyagi83/linkedin-image-generator
# ...etc, install whichever platforms you actually use
```

Hermes lazy-loads skill bodies on demand (its built-in progressive disclosure), so the equivalent of the `/suite` activation control isn't needed. The runtime already pays only the metadata cost for skills it doesn't invoke.

### Compatibility matrix

| Capability | Claude Code | Hermes Agent | Codex / Gemini / Cursor |
|---|---|---|---|
| Platform image generation (LinkedIn, Medium, Twitter, Instagram, Meta) | yes | yes | yes (via skill) |
| Infographic generation (OpenAI gpt-image-2) | yes | yes | yes |
| Quality gate (Anthropic Haiku or OpenAI gpt-4o-mini) | yes | yes | yes |
| Manifest concurrency: fcntl file lock | yes | yes | yes |
| Manifest concurrency: SQLite (WAL + BEGIN IMMEDIATE) | yes | yes | yes |
| `/suite` per-skill activation toggle | yes | n/a (runtime lazy-loads) | varies by host |
| `metadata.hermes.requires_toolsets` conditional loading | n/a | yes | n/a |

Engine resolution is runtime-aware via the `scripts/engine` wrapper inside each skill: it auto-detects whether the visual-engine sits under `~/.claude/skills/`, `~/.claude/skills-suite/`, `~/.hermes/skills/`, or alongside it via `$HERMES_SKILL_DIR`.

### Manifest backends

Two storage modes for the cross-platform manifest:

- **JSON** (default): human-readable, single file. Concurrent writers serialise via an `fcntl.flock` sidecar lockfile on POSIX. Fine for solo and small-team use.
- **SQLite**: pass a manifest path ending in `.db`, `.sqlite`, or `.sqlite3` and the engine routes through SQLite with WAL mode and `BEGIN IMMEDIATE` transactions. Use this for larger teams or when running on Windows (where the JSON lock is a no-op).

Both backends expose the same API. Switch by changing only the manifest path.

### Manual install

```bash
cp -r skills/visual-engine ~/.claude/skills/
cp -r skills/content-image-orchestrator ~/.claude/skills/
cp -r skills/medium-image-generator ~/.claude/skills/
cp -r skills/linkedin-image-generator ~/.claude/skills/
cp -r skills/twitter-image-generator ~/.claude/skills/
cp -r skills/instagram-image-generator ~/.claude/skills/
cp -r skills/meta-image-generator ~/.claude/skills/
cp -r skills/infographic-generator ~/.claude/skills/
```

### Setup

1. Install Python dependencies:
   ```bash
   pip install fal-client
   ```

2. Set your fal.ai API key:
   ```bash
   export FAL_KEY=your-fal-key-here
   ```
   Add this to your `~/.zshrc` or `~/.bashrc` to make it persist.

3. (Optional) Verify the engine works:
   ```bash
   python3 ~/.claude/skills/visual-engine/scripts/engine.py platforms
   ```

### Selective install

Want only LinkedIn and Twitter? Skip the others:

```bash
cp -r visual-engine ~/.claude/skills/
cp -r linkedin-image-generator ~/.claude/skills/
cp -r twitter-image-generator ~/.claude/skills/
```

The orchestrator and other platform skills are independent. The `visual-engine` is required for any of them.

## Usage

### Single platform

Just ask Claude:

> "Make me a Medium hero for this post: [paste draft]"

Claude triggers `medium-image-generator`, walks through subject extraction, runs rotation, generates the image, and iterates with you.

### Multi-platform

> "I want images for this article on Medium, LinkedIn, and Twitter."

Claude triggers `content-image-orchestrator`, picks one shared style+palette across the three platforms, then generates each in sequence with feedback in between.

### LinkedIn carousel

> "Make me a tutorial carousel for LinkedIn from this article. 7 slides."

Triggers `linkedin-image-generator` in carousel mode. Generates one slide at a time so you can iterate without wasting fal.ai credits.

### Cross-session continuity

Image a Medium post today. Three days later:

> "Make me the LinkedIn version of my BigQuery cost optimization post."

Claude finds the existing piece in the manifest (fuzzy match on "BigQuery cost optimization"), pulls the locked style+palette (`isometric` + `electric-dusk`), and generates LinkedIn images using the same identity.

### Iteration

After every image, Claude asks a single short feedback question. You can:

- Approve: "Looks good" → moves on
- Tweak the subject: "Make her older", "Different metaphor"
- Tweak the visual: "Darker", "More punchy", "Different composition"
- Change style: "Use minimalist instead"
- Stop: "We're done"

See `visual-engine/references/iteration-vocabulary.md` for the full mapping.

## Migrating from v1

If you used the original single-platform Medium image generator, your manifest is in v1 schema. Migrate it once:

```bash
python3 ~/.claude/skills/visual-engine/scripts/migrate_v1_to_v2.py \
  /path/to/your/medium-images/manifest.json \
  --output /path/to/your/content-images/manifest.json
```

By default, the migration:
- Reads from the v1 manifest path you provide
- Writes the v2 manifest to the output path (or in-place if `--output` omitted)
- Keeps a backup of the v1 file at `<path>.v1.backup` (unless `--no-backup` is passed)

Each v1 entry becomes a v2 content piece with the Medium platform output populated. Other platforms start as `null`.

## What's in the box

**For end users:**
- 7 SKILL.md files, one per skill
- The visual-engine Python library + CLI
- 4 reference docs (palettes, subject extraction, iteration vocab, prompt engineering)
- 8 style templates

**For development:**
- 157 tests (`cd visual-engine && python3 -m pytest tests/`)
- A migration script for v1 manifests
- A clean modular architecture so adding a 6th platform is one PlatformConfig and one SKILL.md

## Configuration

### Where the manifest lives

Default: `<working-dir>/content-images/manifest.json`.

`<working-dir>` is wherever Claude Code was launched. Want a different path? Tell Claude: "Use `~/projects/blog/manifest.json` as the image history."

### What's in the manifest

A flat list of content pieces. Each piece is one source article/post. Within each piece, `platform_outputs` is a map of platform → output (or null if not yet generated).

```json
{
  "schema_version": 2,
  "blog_owner": "@your-handle",
  "content_pieces": [
    {
      "content_id": "...",
      "canonical_title": "How We Cut BigQuery Costs by 47%",
      "canonical_slug": "bigquery-cost-optimization",
      "first_seen_date": "2026-05-08",
      "subject_themes": ["server racks", "fuel gauge"],
      "shared_identity": {"style": "isometric", "palette_id": "electric-dusk"},
      "platform_outputs": {
        "medium": { ... },
        "linkedin": { ... },
        "twitter": null,
        "instagram": null,
        "meta": null
      }
    }
  ]
}
```

## Troubleshooting

**"FAL_KEY environment variable is not set"** → `export FAL_KEY=...` in your shell.

**"fal-client package not installed"** → `pip install fal-client` (or `pip install fal-client --break-system-packages` on macOS with Python 3.13+).

**Rate-limited** → wait 5 seconds, retry. The engine handles this automatically (one retry).

**Policy violation** → Gemini rejected the prompt. Switch to a less suggestive subject.

**Manifest corrupt** → the engine auto-backs it up to `manifest.corrupt.<timestamp>.json` and starts fresh. Your existing posts won't be considered for rotation; that's the tradeoff for not crashing on you.

**Style template not found** → make sure `visual-engine/assets/style_templates/` is in place. Run `ls ~/.claude/skills/visual-engine/assets/style_templates/` — you should see 8 `.md` files.

## Costs

Each image costs roughly $0.04-$0.06 on fal.ai's Gemini 3 Pro Image endpoint. A typical Medium post (hero + 3 inline) is ~$0.20. A LinkedIn carousel (6 slides) is ~$0.30. Track your fal.ai usage at `fal.ai/dashboard`.

## License

Bundle ships as-is. Adapt freely.
