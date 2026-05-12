#!/usr/bin/env bash
# suite.sh — runtime controller for the Content Image Suite.
# Called by the /suite slash command. Manages symlinks under
# ~/.claude/skills/ that point into ~/.claude/skills-suite/.
#
# Subcommands:
#   list             Show staged vs active skills + token cost estimate.
#   enable NAME      Symlink one skill into ~/.claude/skills/.
#   disable NAME     Remove the symlink.
#   enable-all       Activate every staged skill.
#   disable-all      Deactivate every platform skill (keeps core).
#   status           Same as list but JSON.
#
# Designed to be safe to run from inside Claude Code:
#   - All output goes to stdout
#   - Exits 0 on success, non-zero on real errors only
#   - Never touches files outside ~/.claude/

set -euo pipefail

STAGE_DIR="${SUITE_STAGE_DIR:-$HOME/.claude/skills-suite}"
ACTIVE_DIR="${SUITE_ACTIVE_DIR:-$HOME/.claude/skills}"

CORE_SKILLS="visual-engine content-image-orchestrator"
PLATFORM_SKILLS="medium-image-generator linkedin-image-generator twitter-image-generator instagram-image-generator meta-image-generator infographic-generator"
ALL_SKILLS="$CORE_SKILLS $PLATFORM_SKILLS"

# Normalise short names to canonical skill names.
normalise() {
    case "$1" in
        linkedin|linkedin-image-generator)         echo "linkedin-image-generator" ;;
        medium|medium-image-generator)             echo "medium-image-generator" ;;
        twitter|x|twitter-image-generator)         echo "twitter-image-generator" ;;
        instagram|ig|instagram-image-generator)    echo "instagram-image-generator" ;;
        meta|facebook|fb|meta-image-generator)     echo "meta-image-generator" ;;
        infographic|infographic-generator)         echo "infographic-generator" ;;
        visual-engine|engine)                      echo "visual-engine" ;;
        orchestrator|content-image-orchestrator)   echo "content-image-orchestrator" ;;
        *) echo "" ;;
    esac
}

# Is this skill currently active (symlinked into ~/.claude/skills/)?
is_active() {
    [ -L "$ACTIVE_DIR/$1" ] || [ -d "$ACTIVE_DIR/$1" ]
}

is_staged() {
    [ -d "$STAGE_DIR/$1" ]
}

# Estimate the description-token cost of a skill from its SKILL.md frontmatter.
# Rough estimate: 1 token per 4 characters. Matches what Claude Code loads
# at session start — only the description, not the body.
description_tokens() {
    local skill="$1"
    local path="$STAGE_DIR/$skill/SKILL.md"
    if [ ! -f "$path" ]; then
        echo 0
        return
    fi
    # Extract the `description:` line from the YAML frontmatter.
    local desc
    desc=$(awk '/^---$/{ if(seen){exit} else {seen=1; next} } seen && /^description:/{ sub(/^description:[ \t]*/, ""); print; exit }' "$path")
    local chars=${#desc}
    echo $(( (chars + 3) / 4 ))
}

cmd_list() {
    echo "Content Image Suite — activation status"
    echo "  staging: $STAGE_DIR"
    echo "  active : $ACTIVE_DIR"
    echo ""
    printf "  %-32s %-10s %-10s  %s\n" "SKILL" "STAGED" "ACTIVE" "~TOKENS"
    printf "  %-32s %-10s %-10s  %s\n" "-----" "------" "------" "-------"
    local total_tokens=0
    for s in $ALL_SKILLS; do
        local staged="no"; is_staged "$s" && staged="yes"
        local active="no"; is_active "$s" && active="yes"
        local tokens; tokens=$(description_tokens "$s")
        if [ "$active" = "yes" ]; then
            total_tokens=$(( total_tokens + tokens ))
        fi
        printf "  %-32s %-10s %-10s  %s\n" "$s" "$staged" "$active" "$tokens"
    done
    echo ""
    echo "Active session-start cost: ~$total_tokens tokens (description frontmatter only)."
    echo "Skill bodies load lazily on first use."
}

cmd_enable() {
    local raw="${1:-}"
    if [ -z "$raw" ]; then
        echo "ERROR: /suite enable <skill-name>" >&2
        return 2
    fi
    local skill; skill=$(normalise "$raw")
    if [ -z "$skill" ]; then
        echo "ERROR: unknown skill: $raw" >&2
        echo "Known: $ALL_SKILLS" >&2
        return 2
    fi
    if ! is_staged "$skill"; then
        echo "ERROR: $skill is not staged. Reinstall the suite." >&2
        return 2
    fi
    mkdir -p "$ACTIVE_DIR"
    local link="$ACTIVE_DIR/$skill"
    if [ -e "$link" ] && [ ! -L "$link" ]; then
        mv "$link" "${link}.backup.$(date +%Y%m%dT%H%M%S)"
    fi
    ln -sfn "$STAGE_DIR/$skill" "$link"
    echo "Activated: $skill"
    echo "Restart Claude Code (or refresh skills) for the change to take effect."
}

cmd_disable() {
    local raw="${1:-}"
    if [ -z "$raw" ]; then
        echo "ERROR: /suite disable <skill-name>" >&2
        return 2
    fi
    local skill; skill=$(normalise "$raw")
    if [ -z "$skill" ]; then
        echo "ERROR: unknown skill: $raw" >&2
        return 2
    fi
    # Refuse to disable core skills via this path.
    case " $CORE_SKILLS " in
        *" $skill "*)
            echo "ERROR: $skill is a core skill and cannot be disabled." >&2
            echo "If you really want to remove it, delete $ACTIVE_DIR/$skill manually." >&2
            return 2
            ;;
    esac
    local link="$ACTIVE_DIR/$skill"
    if [ -L "$link" ]; then
        rm -f "$link"
        echo "Deactivated: $skill"
    elif [ -d "$link" ]; then
        echo "ERROR: $link is a real directory, not a symlink." >&2
        echo "This looks like a legacy install. Move it aside manually." >&2
        return 2
    else
        echo "$skill is already inactive."
    fi
}

cmd_enable_all() {
    for s in $ALL_SKILLS; do
        is_staged "$s" && cmd_enable "$s" >/dev/null
    done
    echo "All staged skills activated."
    cmd_list
}

cmd_disable_all() {
    for s in $PLATFORM_SKILLS; do
        local link="$ACTIVE_DIR/$s"
        [ -L "$link" ] && rm -f "$link"
    done
    echo "All platform skills deactivated. Core remains active."
    cmd_list
}

cmd_status_json() {
    local entries=""
    for s in $ALL_SKILLS; do
        local staged="false"; is_staged "$s" && staged="true"
        local active="false"; is_active "$s" && active="true"
        local tokens; tokens=$(description_tokens "$s")
        local entry
        entry=$(printf '{"name":"%s","staged":%s,"active":%s,"tokens":%s}' \
            "$s" "$staged" "$active" "$tokens")
        if [ -z "$entries" ]; then entries="$entry"; else entries="$entries,$entry"; fi
    done
    printf '{"stage_dir":"%s","active_dir":"%s","skills":[%s]}\n' \
        "$STAGE_DIR" "$ACTIVE_DIR" "$entries"
}

# ----- Dispatch -----
cmd="${1:-list}"
shift || true
case "$cmd" in
    list)        cmd_list ;;
    enable)      cmd_enable "${1:-}" ;;
    disable)     cmd_disable "${1:-}" ;;
    enable-all)  cmd_enable_all ;;
    disable-all) cmd_disable_all ;;
    status)      cmd_status_json ;;
    -h|--help)
        cat <<USAGE
suite.sh — Content Image Suite activation controller

Usage:
  suite.sh list                Show staged vs active + token cost
  suite.sh enable <skill>      Symlink a staged skill into ~/.claude/skills/
  suite.sh disable <skill>     Remove the symlink
  suite.sh enable-all          Activate every staged skill
  suite.sh disable-all         Deactivate platform skills, keep core
  suite.sh status              Same as list, JSON output

Skill names accept short aliases: linkedin, medium, twitter, instagram,
meta, infographic.
USAGE
        ;;
    *)
        echo "Unknown command: $cmd" >&2
        echo "Try /suite --help" >&2
        exit 2
        ;;
esac
