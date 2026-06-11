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

# Prune skills that are no longer in this package, so the global skills dir
# mirrors this package EXACTLY: a skill removed here is removed there on install.
for installed_dir in "$CLAUDE_DIR/skills"/*/; do
    [ -d "$installed_dir" ] || continue   # no-match glob; nothing installed yet
    installed_name="$(basename "$installed_dir")"
    if [ ! -d "$SCRIPT_DIR/skills/$installed_name" ]; then
        rm -rf "$installed_dir"
        echo "  Removed stale skill: $installed_name"
    fi
done

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

# Merge settings: install global-settings.json as settings.json, substituting the
# /__HOME__ path placeholder with the real home dir (same install-or-overwrite
# behavior as the global-CLAUDE.md block below).
#
# Why the placeholder: Claude Code permission allow-rule paths are matched
# literally by picomatch and do NOT expand ~, and a single leading / is
# project-root-relative (not the filesystem root). So an out-of-tree allow path
# like the ~/.octo-memory memory store must be an absolute path with a // prefix
# (// => absolute, then Claude Code strips one slash). global-settings.json keeps
# it portable as /__HOME__/... — $HOME already starts with /, so the expansion
# yields the required //home/... double-slash form. The substitution uses bash
# parameter expansion; patsub_replacement is disabled first so a literal & (or |,
# \) in $HOME is kept verbatim instead of meaning "the matched text" (bash 5.0+) —
# the sed equivalent would mis-expand & and break on a | delimiter.
if [ -f "$SCRIPT_DIR/global-settings.json" ]; then
    target_settings="$CLAUDE_DIR/settings.json"
    settings_src="$(cat "$SCRIPT_DIR/global-settings.json")"
    shopt -u patsub_replacement 2>/dev/null || true
    rendered_settings="${settings_src//__HOME__/$HOME}"
    if [ ! -f "$target_settings" ]; then
        printf '%s\n' "$rendered_settings" > "$target_settings"
        echo "  Installed settings.json (new)"
    else
        if [ "$rendered_settings" = "$(cat "$target_settings")" ]; then
            echo "  Settings unchanged"
        else
            printf '%s\n' "$rendered_settings" > "$target_settings"
            echo "  Updated settings.json"
        fi
    fi
fi

# Merge global memory: copy global-CLAUDE.md as CLAUDE.md if it doesn't exist,
# otherwise overwrite when changed (same always-override behavior as settings).
if [ -f "$SCRIPT_DIR/global-CLAUDE.md" ]; then
    target_memory="$CLAUDE_DIR/CLAUDE.md"
    if [ ! -f "$target_memory" ]; then
        cp "$SCRIPT_DIR/global-CLAUDE.md" "$target_memory"
        echo "  Installed CLAUDE.md (new)"
    else
        if diff -q "$SCRIPT_DIR/global-CLAUDE.md" "$target_memory" > /dev/null 2>&1; then
            echo "  CLAUDE.md unchanged"
        else
            cp "$SCRIPT_DIR/global-CLAUDE.md" "$target_memory"
            echo "  Updated CLAUDE.md"
        fi
    fi
fi

# Install Swift LSP (sourcekit-lsp) — required by swift-lsp plugin
install_swift_lsp() {
    if command -v sourcekit-lsp >/dev/null 2>&1; then
        echo "  Swift LSP already installed: $(command -v sourcekit-lsp)"
        return
    fi

    case "$(uname -s)" in
        Darwin)
            if xcode-select -p >/dev/null 2>&1 && command -v sourcekit-lsp >/dev/null 2>&1; then
                echo "  Swift LSP available via Xcode"
                return
            fi
            if command -v brew >/dev/null 2>&1; then
                echo "  Installing Swift via Homebrew (provides sourcekit-lsp)..."
                brew install swift
            else
                echo "  WARNING: sourcekit-lsp not found. Install Xcode from the App Store"
                echo "           or install Homebrew and run: brew install swift"
            fi
            ;;
        Linux)
            echo "  WARNING: sourcekit-lsp not found. Install the Swift toolchain from"
            echo "           https://www.swift.org/download/ to enable the swift-lsp plugin."
            ;;
        *)
            echo "  WARNING: sourcekit-lsp not found. Install Swift to enable the swift-lsp plugin."
            ;;
    esac
}

install_swift_lsp

# Install Node.js + pre-cache Playwright MCP & Chromium.
# Used by project-scoped Playwright MCP servers (e.g. octo-family-doc/.mcp.json).
# This only provides the system dependency; it does NOT register the MCP server
# globally — each project opts in via its own .mcp.json.
install_node_playwright() {
    if command -v node >/dev/null 2>&1; then
        echo "  Node.js already installed: $(command -v node) ($(node --version))"
    else
        case "$(uname -s)" in
            Darwin)
                if command -v brew >/dev/null 2>&1; then
                    echo "  Installing Node.js via Homebrew..."
                    brew install node
                else
                    echo "  WARNING: node not found and Homebrew unavailable."
                    echo "           Install Node.js from https://nodejs.org/ to enable Playwright MCP."
                    return
                fi
                ;;
            Linux)
                echo "  WARNING: node not found. Install Node.js (https://nodejs.org/) to enable Playwright MCP."
                return
                ;;
            *)
                echo "  WARNING: node not found. Install Node.js to enable Playwright MCP."
                return
                ;;
        esac
    fi

    # Pre-cache the MCP package + Chromium so the first project use is fast.
    if command -v npx >/dev/null 2>&1; then
        echo "  Pre-caching Playwright MCP + Chromium (one-time)..."
        npx -y @playwright/mcp@latest --help >/dev/null 2>&1 || true
        npx -y playwright@latest install chromium >/dev/null 2>&1 || true
    fi
}

install_node_playwright

echo ""
echo "Done. Installed skills:"
ls -1 "$CLAUDE_DIR/skills/"
echo ""
echo "These skills are now available in ALL projects via user-level config."
echo "Project-specific skills go in <project>/.claude/skills/"
