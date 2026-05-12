#!/usr/bin/env bash
# install-team.sh
# Team-oriented installer for the Content Image Suite.
#
# Difference vs install.sh:
#   install.sh    copies skills directly into ~/.claude/skills/. Everything
#                 a user installed is active; uninstalling means deleting.
#   install-team.sh stages all skills into ~/.claude/skills-suite/ and then
#                 symlinks only the ones the user activates into
#                 ~/.claude/skills/. The `/suite` slash command toggles
#                 activation per-skill without reinstalling.
#
# Why this matters for teams:
#   - Frontmatter descriptions load at every session start. A team that posts
#     on three platforms shouldn't pay for the other four in token cost.
#   - Activations are per-machine, per-user. A shared install can serve
#     teammates with different active sets.
#   - "/suite enable medium" is faster to support than "rerun the installer."
#
# Usage:
#   ./install-team.sh                       # Stage all skills, activate the
#                                           # core (visual-engine +
#                                           # orchestrator). Use /suite to
#                                           # enable platform skills.
#   ./install-team.sh --activate all        # Stage + activate everything.
#   ./install-team.sh --activate "linkedin,medium"
#                                           # Stage + activate just those.
#   ./install-team.sh --dry-run             # Show actions, change nothing.
#   ./install-team.sh --target DIR          # Stage to DIR instead of
#                                           # ~/.claude/skills-suite/.

set -euo pipefail

RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
BLUE=$'\033[0;34m'
NC=$'\033[0m'

DRY_RUN=0
ACTIVATE="core"          # "core" | "all" | comma-separated platforms
CUSTOM_STAGE=""

while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run)         DRY_RUN=1; shift ;;
        --activate)        ACTIVATE="$2"; shift 2 ;;
        --target)          CUSTOM_STAGE="$2"; shift 2 ;;
        -h|--help)         head -n 30 "$0" | tail -n 29 | sed 's/^# //; s/^#//'; exit 0 ;;
        *)                 echo "Unknown argument: $1" >&2; exit 1 ;;
    esac
done

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# Skills under skills/ (current layout) or top-level (legacy flat layout)
if [ -d "$SCRIPT_DIR/skills" ]; then
    SKILLS_SRC="$SCRIPT_DIR/skills"
else
    SKILLS_SRC="$SCRIPT_DIR"
fi

if [ ! -d "$SKILLS_SRC/visual-engine" ]; then
    echo "${RED}ERROR: install-team.sh cannot find the skill folders at $SKILLS_SRC${NC}" >&2
    exit 1
fi

# ----- Paths -----
if [ -n "$CUSTOM_STAGE" ]; then
    STAGE_DIR="$CUSTOM_STAGE"
else
    STAGE_DIR="$HOME/.claude/skills-suite"
fi
ACTIVE_DIR="$HOME/.claude/skills"
COMMANDS_DIR="$HOME/.claude/commands"
BIN_DIR="$STAGE_DIR/bin"

echo "${BLUE}Staged install layout${NC}"
echo "  source:    $SCRIPT_DIR"
echo "  staging:   $STAGE_DIR"
echo "  active:    $ACTIVE_DIR  (symlinks)"
echo "  commands:  $COMMANDS_DIR"
echo "  activate:  $ACTIVATE"
if [ $DRY_RUN -eq 1 ]; then
    echo "${YELLOW}DRY RUN — nothing will be modified.${NC}"
fi

# ----- All skills in the suite -----
CORE_SKILLS="visual-engine content-image-orchestrator"
PLATFORM_SKILLS="medium-image-generator linkedin-image-generator \
                 twitter-image-generator instagram-image-generator \
                 meta-image-generator infographic-generator"
ALL_SKILLS="$CORE_SKILLS $PLATFORM_SKILLS"

# ----- Stage everything -----
echo ""
echo "${BLUE}Staging skills to $STAGE_DIR${NC}"
if [ $DRY_RUN -eq 0 ]; then
    mkdir -p "$STAGE_DIR" "$ACTIVE_DIR" "$COMMANDS_DIR" "$BIN_DIR"
fi

for skill in $ALL_SKILLS; do
    if [ ! -d "$SKILLS_SRC/$skill" ]; then
        echo "  ${YELLOW}WARN${NC} source missing: $skill (skipped)"
        continue
    fi
    if [ $DRY_RUN -eq 0 ]; then
        rm -rf "$STAGE_DIR/$skill"
        cp -R "$SKILLS_SRC/$skill" "$STAGE_DIR/$skill"
        find "$STAGE_DIR/$skill" -name "__pycache__" -type d 2>/dev/null | \
            while read d; do rm -rf "$d"; done
        find "$STAGE_DIR/$skill" -name "*.pyc" -type f -delete 2>/dev/null || true
        echo "  ${GREEN}staged${NC} $skill"
    else
        echo "  ${YELLOW}would stage${NC} $skill"
    fi
done

# ----- Install the /suite bin script -----
SUITE_BIN="$BIN_DIR/suite.sh"
if [ $DRY_RUN -eq 0 ]; then
    cp "$SCRIPT_DIR/bin/suite.sh" "$SUITE_BIN"
    chmod +x "$SUITE_BIN"
    echo "  ${GREEN}installed${NC} $SUITE_BIN"
else
    echo "  ${YELLOW}would install${NC} $SUITE_BIN"
fi

# ----- Install the /suite slash command -----
SUITE_CMD="$COMMANDS_DIR/suite.md"
if [ $DRY_RUN -eq 0 ]; then
    cp "$SCRIPT_DIR/commands/suite.md" "$SUITE_CMD"
    echo "  ${GREEN}installed${NC} $SUITE_CMD"
else
    echo "  ${YELLOW}would install${NC} $SUITE_CMD"
fi

# ----- Decide which skills to activate -----
case "$ACTIVATE" in
    core)
        TO_ACTIVATE="$CORE_SKILLS"
        ;;
    all)
        TO_ACTIVATE="$ALL_SKILLS"
        ;;
    *)
        # Comma-separated platform list. Always include core.
        REQUESTED=$(echo "$ACTIVATE" | tr ',' ' ')
        TO_ACTIVATE="$CORE_SKILLS"
        for r in $REQUESTED; do
            r_trimmed=$(echo "$r" | xargs)
            # Accept short names (linkedin) or full names (linkedin-image-generator).
            case "$r_trimmed" in
                linkedin|linkedin-image-generator)   TO_ACTIVATE="$TO_ACTIVATE linkedin-image-generator" ;;
                medium|medium-image-generator)       TO_ACTIVATE="$TO_ACTIVATE medium-image-generator" ;;
                twitter|x|twitter-image-generator)   TO_ACTIVATE="$TO_ACTIVATE twitter-image-generator" ;;
                instagram|ig|instagram-image-generator) TO_ACTIVATE="$TO_ACTIVATE instagram-image-generator" ;;
                meta|facebook|fb|meta-image-generator) TO_ACTIVATE="$TO_ACTIVATE meta-image-generator" ;;
                infographic|infographic-generator)   TO_ACTIVATE="$TO_ACTIVATE infographic-generator" ;;
                *) echo "  ${YELLOW}WARN${NC} unknown skill: $r_trimmed (skipped)" ;;
            esac
        done
        ;;
esac

# ----- Activate via symlinks -----
echo ""
echo "${BLUE}Activating skills (symlinks)${NC}"
for skill in $TO_ACTIVATE; do
    target="$STAGE_DIR/$skill"
    link="$ACTIVE_DIR/$skill"
    if [ ! -d "$target" ]; then
        echo "  ${YELLOW}skip${NC} $skill (not staged)"
        continue
    fi
    if [ $DRY_RUN -eq 0 ]; then
        # If something is there already, back it up rather than clobber.
        if [ -e "$link" ] && [ ! -L "$link" ]; then
            mv "$link" "${link}.backup.$(date +%Y%m%dT%H%M%S)"
        fi
        ln -sfn "$target" "$link"
        echo "  ${GREEN}active${NC}  $skill -> $target"
    else
        echo "  ${YELLOW}would link${NC} $skill -> $target"
    fi
done

# ----- Dependency checks -----
echo ""
echo "${BLUE}Dependency check${NC}"

if ! command -v python3 >/dev/null 2>&1; then
    echo "  ${RED}MISSING${NC} python3 (need 3.10+)"
else
    PY=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    echo "  ${GREEN}OK${NC} python3 $PY"
fi

for pkg in fal_client anthropic openai pytesseract; do
    if python3 -c "import $pkg" >/dev/null 2>&1; then
        echo "  ${GREEN}OK${NC} $pkg"
    else
        echo "  ${YELLOW}optional${NC} $pkg not installed"
    fi
done

for var in FAL_KEY ANTHROPIC_API_KEY OPENAI_API_KEY; do
    if [ -n "${!var:-}" ]; then
        echo "  ${GREEN}OK${NC} $var set"
    else
        echo "  ${YELLOW}optional${NC} $var not set"
    fi
done

# ----- Done -----
echo ""
echo "${GREEN}====================================${NC}"
if [ $DRY_RUN -eq 0 ]; then
    echo "${GREEN}Content Image Suite installed (team mode).${NC}"
    echo "${GREEN}====================================${NC}"
    echo ""
    echo "Active skills:"
    for s in $TO_ACTIVATE; do echo "  - $s"; done
    echo ""
    echo "Staged but not active (use /suite enable <name>):"
    for s in $ALL_SKILLS; do
        case " $TO_ACTIVATE " in *" $s "*) continue ;; esac
        echo "  - $s"
    done
    echo ""
    echo "Next steps:"
    echo "  1. Restart Claude Code (or refresh skills)."
    echo "  2. Try /suite list to confirm activation."
    echo "  3. Toggle skills with /suite enable <name> or /suite disable <name>."
else
    echo "${YELLOW}Dry run complete.${NC}"
    echo "${GREEN}====================================${NC}"
fi
echo ""
