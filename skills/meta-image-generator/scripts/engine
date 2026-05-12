#!/usr/bin/env bash
# engine-wrapper.sh (canonical template, copied to each skill's scripts/engine)
#
# Locates the shared visual-engine Python CLI across runtimes and forwards
# all arguments to it. SKILL.md authors reference the engine through this
# wrapper instead of a hardcoded path so the same SKILL.md works in
# Claude Code (solo install), Claude Code (team install with the staged
# layout), and Hermes Agent.
#
# Search order, in priority:
#   1. Explicit override:           $VISUAL_ENGINE_PATH
#   2. Hermes skill-dir neighbours: $HERMES_SKILL_DIR/../visual-engine/
#                                   $HERMES_SKILL_DIR/../../visual-engine/
#   3. Hermes default install:      ~/.hermes/skills/visual-engine/
#   4. Claude Code solo install:    ~/.claude/skills/visual-engine/
#   5. Claude Code team install:    ~/.claude/skills-suite/visual-engine/
#   6. Sibling of this script:      ../../visual-engine/scripts/engine.py
#
# The first hit wins. To force a specific install, set VISUAL_ENGINE_PATH to
# the absolute path of engine.py in your shell environment.
#
# Exit codes are passed through unchanged from the underlying Python engine.

set -euo pipefail

if [ -n "${VISUAL_ENGINE_PATH:-}" ] && [ -f "$VISUAL_ENGINE_PATH" ]; then
    exec python3 "$VISUAL_ENGINE_PATH" "$@"
fi

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

candidates=(
    "${HERMES_SKILL_DIR:-}/../visual-engine/scripts/engine.py"
    "${HERMES_SKILL_DIR:-}/../../visual-engine/scripts/engine.py"
    "$HOME/.hermes/skills/visual-engine/scripts/engine.py"
    "$HOME/.claude/skills/visual-engine/scripts/engine.py"
    "$HOME/.claude/skills-suite/visual-engine/scripts/engine.py"
    "$SCRIPT_DIR/../../visual-engine/scripts/engine.py"
    "$SCRIPT_DIR/../../../visual-engine/scripts/engine.py"
)

for candidate in "${candidates[@]}"; do
    if [ -n "$candidate" ] && [ -f "$candidate" ]; then
        exec python3 "$candidate" "$@"
    fi
done

echo "ERROR: visual-engine not found. Searched:" >&2
for candidate in "${candidates[@]}"; do
    [ -n "$candidate" ] && echo "  - $candidate" >&2
done
echo "" >&2
echo "Fix: install the content-image-suite (run install.sh or install-team.sh)," >&2
echo "or set VISUAL_ENGINE_PATH to the absolute path of visual-engine/scripts/engine.py" >&2
exit 127
