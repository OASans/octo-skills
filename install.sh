#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect target directory
case "$(uname -s)" in
    Darwin)
        CLAUDE_DIR="$HOME/.claude"
        ;;
    Linux)
        CLAUDE_DIR="$HOME/.claude"
        ;;
    MINGW*|MSYS*|CYGWIN*)
        CLAUDE_DIR="$APPDATA/Claude"
        ;;
    *)
        echo "Unsupported OS: $(uname -s)"
        exit 1
        ;;
esac

echo "Installing shared Claude config to: $CLAUDE_DIR"

# Ensure target directories exist
mkdir -p "$CLAUDE_DIR/skills"

# Copy skills (each skill is a directory with SKILL.md and optional supporting files)
for skill_dir in "$SCRIPT_DIR/skills"/*/; do
    skill_name="$(basename "$skill_dir")"
    target_dir="$CLAUDE_DIR/skills/$skill_name"

    # Remove old version
    rm -rf "$target_dir"

    # Copy new version
    cp -r "$skill_dir" "$target_dir"
    echo "  Installed skill: $skill_name"
done

# Merge settings: copy base-settings.json as settings.json if it doesn't exist,
# otherwise show a diff so the user can decide
if [ -f "$SCRIPT_DIR/base-settings.json" ]; then
    target_settings="$CLAUDE_DIR/settings.json"
    if [ ! -f "$target_settings" ]; then
        cp "$SCRIPT_DIR/base-settings.json" "$target_settings"
        echo "  Installed settings.json (new)"
    else
        if diff -q "$SCRIPT_DIR/base-settings.json" "$target_settings" > /dev/null 2>&1; then
            echo "  Settings unchanged"
        else
            cp "$SCRIPT_DIR/base-settings.json" "$target_settings"
            echo "  Updated settings.json"
        fi
    fi
fi

echo ""
echo "Done. Installed skills:"
ls -1 "$CLAUDE_DIR/skills/"
echo ""
echo "These skills are now available in ALL projects via user-level config."
echo "Project-specific skills go in <project>/.claude/skills/"
