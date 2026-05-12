#!/usr/bin/env bash
# install.sh
# One-command installer for the Content Image Suite.
# Copies all eight skill folders into ~/.claude/skills/, backing up any
# existing installations to a timestamped folder.
#
# Tested against:
#   - macOS (Bash 3.2 default, or Bash 5 from Homebrew)
#   - Linux (Bash 4+)
#
# Usage:
#   ./install.sh                  # Install to ~/.claude/skills/
#   ./install.sh --dry-run        # Show what would happen, change nothing
#   ./install.sh --target DIR     # Install to a custom skills directory

set -euo pipefail

# ----- Colors (use literal escape sequences for Bash 3.2 compatibility) -----
RED=$'\033[0;31m'
GREEN=$'\033[0;32m'
YELLOW=$'\033[1;33m'
BLUE=$'\033[0;34m'
NC=$'\033[0m'

# ----- Args -----
DRY_RUN=0
CUSTOM_TARGET=""
while [ $# -gt 0 ]; do
    case "$1" in
        --dry-run)
            DRY_RUN=1
            shift
            ;;
        --target)
            CUSTOM_TARGET="$2"
            shift 2
            ;;
        -h|--help)
            head -n 13 "$0" | tail -n 12 | sed 's/^# //; s/^#//'
            exit 0
            ;;
        *)
            echo "Unknown argument: $1" >&2
            echo "Run with --help for usage." >&2
            exit 1
            ;;
    esac
done

# ----- Script directory -----
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

# ----- Detect a double-nested folder (common zip extraction mistake) -----
# If the user extracted the zip such that this script sits inside an extra
# folder layer, all skill folders will be missing here. Detect and explain.
if [ ! -d "$SCRIPT_DIR/visual-engine" ]; then
    echo "${RED}ERROR: install.sh is not in the same folder as the skills.${NC}" >&2
    echo "" >&2
    echo "Expected to find these folders next to install.sh:" >&2
    echo "  visual-engine/, content-image-orchestrator/," >&2
    echo "  medium-image-generator/, linkedin-image-generator/," >&2
    echo "  twitter-image-generator/, instagram-image-generator/," >&2
    echo "  meta-image-generator/" >&2
    echo "" >&2
    echo "If you extracted the zip into a nested folder, cd one level deeper." >&2
    echo "Current directory: $SCRIPT_DIR" >&2
    exit 1
fi

# ----- Pick install target -----
if [ -n "$CUSTOM_TARGET" ]; then
    INSTALL_DIR="$CUSTOM_TARGET"
    echo "${BLUE}Installing to custom target: $INSTALL_DIR${NC}"
else
    INSTALL_DIR="$HOME/.claude/skills"
    echo "${BLUE}Installing to: $INSTALL_DIR${NC}"
fi

if [ $DRY_RUN -eq 1 ]; then
    echo "${YELLOW}DRY RUN MODE — nothing will be modified.${NC}"
fi

if [ ! -d "$INSTALL_DIR" ]; then
    if [ $DRY_RUN -eq 0 ]; then
        mkdir -p "$INSTALL_DIR"
        echo "${YELLOW}Created: $INSTALL_DIR${NC}"
    else
        echo "${YELLOW}Would create: $INSTALL_DIR${NC}"
    fi
fi

# ----- Skills to install (use indexed array, Bash 3.2 compatible) -----
SKILLS="visual-engine \
        content-image-orchestrator \
        medium-image-generator \
        linkedin-image-generator \
        twitter-image-generator \
        instagram-image-generator \
        meta-image-generator \
        infographic-generator"

# ----- Verify all source skills exist -----
echo ""
echo "${BLUE}Verifying source skills...${NC}"
MISSING=""
for skill in $SKILLS; do
    if [ ! -d "$SCRIPT_DIR/$skill" ]; then
        MISSING="$MISSING $skill"
    fi
done
if [ -n "$MISSING" ]; then
    echo "${RED}ERROR: Missing source folders:${NC}" >&2
    for m in $MISSING; do
        echo "  - $m" >&2
    done
    exit 1
fi
echo "${GREEN}All 7 source skills present.${NC}"

# ----- Backup existing installations -----
TIMESTAMP=$(date +%Y%m%dT%H%M%S)
BACKUP_DIR="$INSTALL_DIR/_backup_$TIMESTAMP"
TO_BACKUP=""

for skill in $SKILLS; do
    if [ -d "$INSTALL_DIR/$skill" ]; then
        TO_BACKUP="$TO_BACKUP $skill"
    fi
done

if [ -n "$TO_BACKUP" ]; then
    echo ""
    echo "${YELLOW}Existing installations found:${NC}"
    for s in $TO_BACKUP; do
        echo "  - $s"
    done
    echo ""
    if [ $DRY_RUN -eq 0 ]; then
        echo "${BLUE}Backing up to: $BACKUP_DIR${NC}"
        mkdir -p "$BACKUP_DIR"
        for s in $TO_BACKUP; do
            mv "$INSTALL_DIR/$s" "$BACKUP_DIR/$s"
        done
    else
        echo "${BLUE}Would back up to: $BACKUP_DIR${NC}"
    fi
fi

# ----- Copy each skill -----
echo ""
echo "${BLUE}Installing skills...${NC}"
for skill in $SKILLS; do
    if [ $DRY_RUN -eq 0 ]; then
        cp -R "$SCRIPT_DIR/$skill" "$INSTALL_DIR/$skill"
        # Clean any pyc/cache files that came along.
        find "$INSTALL_DIR/$skill" -name "__pycache__" -type d 2>/dev/null | \
            while read d; do rm -rf "$d"; done
        find "$INSTALL_DIR/$skill" -name "*.pyc" -type f -delete 2>/dev/null || true
        echo "  ${GREEN}OK${NC} $skill"
    else
        echo "  ${YELLOW}would install${NC} $skill"
    fi
done

# ----- Make engine scripts executable -----
if [ $DRY_RUN -eq 0 ]; then
    chmod +x "$INSTALL_DIR/visual-engine/scripts/engine.py" 2>/dev/null || true
    chmod +x "$INSTALL_DIR/visual-engine/scripts/migrate_v1_to_v2.py" 2>/dev/null || true
fi

# ----- Check dependencies -----
echo ""
echo "${BLUE}Checking dependencies...${NC}"

# Python — need 3.10+ for `X | Y` type unions and PEP 604.
if ! command -v python3 >/dev/null 2>&1; then
    echo "  ${RED}MISSING${NC} python3 not found. Install Python 3.10 or later." >&2
else
    PY_VERSION_FULL=$(python3 --version 2>&1)
    # Extract MAJOR.MINOR
    PY_VERSION=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    PY_MAJOR=$(echo "$PY_VERSION" | cut -d. -f1)
    PY_MINOR=$(echo "$PY_VERSION" | cut -d. -f2)
    if [ "$PY_MAJOR" -lt 3 ] || { [ "$PY_MAJOR" -eq 3 ] && [ "$PY_MINOR" -lt 10 ]; }; then
        echo "  ${YELLOW}WARN${NC} $PY_VERSION_FULL — engine requires Python 3.10+"
    else
        echo "  ${GREEN}OK${NC} $PY_VERSION_FULL"
    fi
fi

# fal-client
if python3 -c "import fal_client" >/dev/null 2>&1; then
    echo "  ${GREEN}OK${NC} fal-client installed"
else
    echo "  ${YELLOW}MISSING${NC} fal-client"
    # On macOS 14+ with Python 3.13, pip needs --break-system-packages or a venv.
    case "$(uname)" in
        Darwin)
            echo "     Install with one of:"
            echo "       pip install fal-client --break-system-packages"
            echo "       OR: python3 -m venv ~/.claude-venv && source ~/.claude-venv/bin/activate && pip install fal-client"
            ;;
        *)
            echo "     Install with: pip install fal-client"
            ;;
    esac
fi

# tesseract + pytesseract (optional: enables OCR-based text-leak detection)
TESSERACT_OK=0
PYTESSERACT_OK=0
if command -v tesseract >/dev/null 2>&1; then
    TESSERACT_OK=1
fi
if python3 -c "import pytesseract, PIL" >/dev/null 2>&1; then
    PYTESSERACT_OK=1
fi
if [ $TESSERACT_OK -eq 1 ] && [ $PYTESSERACT_OK -eq 1 ]; then
    echo "  ${GREEN}OK${NC} tesseract + pytesseract installed (text-detection safety net enabled)"
elif [ $TESSERACT_OK -eq 1 ] && [ $PYTESSERACT_OK -eq 0 ]; then
    echo "  ${YELLOW}OPTIONAL${NC} pytesseract not installed (text-detection safety net disabled)"
    echo "     Enable with: pip install pytesseract pillow"
elif [ $TESSERACT_OK -eq 0 ] && [ $PYTESSERACT_OK -eq 1 ]; then
    echo "  ${YELLOW}OPTIONAL${NC} tesseract binary missing (text-detection safety net disabled)"
    case "$(uname)" in
        Darwin) echo "     Install with: brew install tesseract" ;;
        *)      echo "     Install with: sudo apt install tesseract-ocr  (Debian/Ubuntu)" ;;
    esac
else
    echo "  ${YELLOW}OPTIONAL${NC} text-detection safety net disabled"
    echo "     This catches images where Gemini renders text despite negatives."
    echo "     Enable with:"
    case "$(uname)" in
        Darwin) echo "       brew install tesseract && pip install pytesseract pillow" ;;
        *)      echo "       sudo apt install tesseract-ocr && pip install pytesseract pillow" ;;
    esac
fi

# FAL_KEY (needed for Gemini illustration via fal.ai)
if [ -n "${FAL_KEY:-}" ]; then
    echo "  ${GREEN}OK${NC} FAL_KEY environment variable set"
else
    echo "  ${YELLOW}MISSING${NC} FAL_KEY not set"
    echo "     Needed for: Medium, LinkedIn, Twitter, Instagram, Meta skills"
    echo "     Set with: export FAL_KEY=your-key-here"
    echo "     Add to ~/.zshrc or ~/.bashrc to persist."
fi

# OPENAI_API_KEY (needed for infographic skill via gpt-image-2)
if [ -n "${OPENAI_API_KEY:-}" ]; then
    echo "  ${GREEN}OK${NC} OPENAI_API_KEY environment variable set"
else
    echo "  ${YELLOW}MISSING${NC} OPENAI_API_KEY not set"
    echo "     Needed for: infographic skill (gpt-image-2)"
    echo "     Set with: export OPENAI_API_KEY=sk-..."
    echo "     Also requires Organization Verification (one-time):"
    echo "     https://platform.openai.com/settings/organization/general"
fi

# openai Python package (for infographic skill)
if python3 -c "import openai" >/dev/null 2>&1; then
    OPENAI_VERSION=$(python3 -c "import openai; print(openai.__version__)" 2>/dev/null)
    echo "  ${GREEN}OK${NC} openai Python package installed (${OPENAI_VERSION})"
else
    echo "  ${YELLOW}MISSING${NC} openai Python package not installed"
    echo "     Needed for: infographic skill"
    echo "     Install with: pip install 'openai>=1.50'"
fi

# ----- Run engine smoke test -----
if [ $DRY_RUN -eq 0 ]; then
    echo ""
    echo "${BLUE}Running engine smoke test...${NC}"
    SMOKE_OUT="$(python3 "$INSTALL_DIR/visual-engine/scripts/engine.py" platforms 2>&1 || true)"
    if echo "$SMOKE_OUT" | python3 -c '
import json, sys
try:
    data = json.loads(sys.stdin.read())
    platforms = data.get("platforms", [])
    if len(platforms) != 6:
        sys.exit(1)
    print(f"  OK Engine works. {len(platforms)} platforms registered.")
except Exception:
    sys.exit(2)
' >/dev/null 2>&1; then
        echo "  ${GREEN}OK${NC} Engine works. 6 platforms registered."
    else
        echo "  ${RED}FAILED${NC} Engine smoke test failed." >&2
        echo "     Check: python3 $INSTALL_DIR/visual-engine/scripts/engine.py platforms" >&2
        echo "     Output was: $SMOKE_OUT" >&2
        exit 2
    fi
fi

# ----- Done -----
echo ""
echo "${GREEN}====================================${NC}"
if [ $DRY_RUN -eq 0 ]; then
    echo "${GREEN}Content Image Suite installed.${NC}"
else
    echo "${YELLOW}Dry run complete. Re-run without --dry-run to install.${NC}"
fi
echo "${GREEN}====================================${NC}"
echo ""
echo "Installed skills:"
for s in $SKILLS; do
    echo "  - $s"
done
echo ""
if [ -n "$TO_BACKUP" ] && [ $DRY_RUN -eq 0 ]; then
    echo "Old versions backed up to:"
    echo "  $BACKUP_DIR"
    echo ""
fi
if [ $DRY_RUN -eq 0 ]; then
    echo "Next steps:"
    echo "  1. Make sure FAL_KEY is set in your shell."
    echo "  2. Restart Claude Code (or refresh your skill list)."
    echo "  3. Try: 'Make me a Medium hero image for [some content]'"
    echo ""
    echo "Documentation: $INSTALL_DIR/README.md (this folder)"
    echo "Or per-skill: $INSTALL_DIR/<skill-name>/SKILL.md"
fi
echo ""
