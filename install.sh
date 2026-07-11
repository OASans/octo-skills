#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Detect target directories. Claude Code lives in ~/.claude (%APPDATA%\Claude on
# Windows); Codex CLI always uses ~/.codex (CODEX_HOME).
case "$(uname -s)" in
    Darwin|Linux)
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
CODEX_DIR="$HOME/.codex"

echo "Installing shared config to: $CLAUDE_DIR and $CODEX_DIR"

# install_skills <target-skills-dir>: mirror skills/* into the target EXACTLY —
# a skill removed from this package is removed there on install.
install_skills() {
    local target="$1" installed_dir name skill_dir
    mkdir -p "$target"
    for installed_dir in "$target"/*/; do
        [ -d "$installed_dir" ] || continue   # no-match glob; nothing installed yet
        name="$(basename "$installed_dir")"
        if [ ! -d "$SCRIPT_DIR/skills/$name" ]; then
            rm -rf "$installed_dir"
            echo "  Removed stale skill: $name ($target)"
        fi
    done
    for skill_dir in "$SCRIPT_DIR/skills"/*/; do
        [ -d "$skill_dir" ] || continue   # no-match glob; nothing to copy (don't wipe the target)
        name="$(basename "$skill_dir")"
        rm -rf "$target/$name"
        cp -r "$skill_dir" "$target/$name"
    done
    echo "  Installed skills -> $target"
}

# write_if_changed <content> <dest> <label>: install-or-overwrite, writing only
# when content differs from what's already there.
write_if_changed() {
    local content="$1" dest="$2" label="$3"
    mkdir -p "$(dirname "$dest")"
    if [ ! -f "$dest" ]; then
        printf '%s\n' "$content" > "$dest"
        echo "  Installed $label (new)"
    elif [ "$content" = "$(cat "$dest")" ]; then
        echo "  $label unchanged"
    else
        printf '%s\n' "$content" > "$dest"
        echo "  Updated $label"
    fi
}

# install_file <src> <dest> <label>: render src into dest, substituting the
# /__HOME__ path placeholder with the real home dir.
#
# Why the placeholder: Claude Code permission allow-rule paths are matched
# literally by picomatch and do NOT expand ~, and a single leading / is
# project-root-relative (not the filesystem root). So an out-of-tree allow path
# like the ~/.octo-memory memory store must be an absolute path with a // prefix
# (// => absolute, then Claude Code strips one slash). Sources keep it portable as
# /__HOME__/... — $HOME already starts with /, so the expansion yields the required
# //home/... double-slash form. patsub_replacement is disabled first so a literal &
# (or |, \) in $HOME is kept verbatim instead of meaning "the matched text" (bash
# 5.0+) — the sed equivalent would mis-expand & and break on a | delimiter. Files
# without the placeholder (CLAUDE.md, AGENTS.md) are copied unchanged.
install_file() {
    local src="$1" dest="$2" label="$3" content
    [ -f "$src" ] || return 0
    shopt -u patsub_replacement 2>/dev/null || true
    content="$(cat "$src")"
    write_if_changed "${content//__HOME__/$HOME}" "$dest" "$label"
}

# Skills: same SKILL.md standard for both agents (agentskills.io open spec).
install_skills "$CLAUDE_DIR/skills"
install_skills "$CODEX_DIR/skills"

# Global memory / prompt: one source (global-CLAUDE.md) -> Claude CLAUDE.md and
# Codex AGENTS.md (merged root-first by Codex, same as CLAUDE.md).
install_file "$SCRIPT_DIR/global-CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md"  "CLAUDE.md"
install_file "$SCRIPT_DIR/global-CLAUDE.md" "$CODEX_DIR/AGENTS.md"   "AGENTS.md"

# Settings. Claude Code settings.json is JSON; Codex config is TOML and does NOT
# port, so it is maintained separately (not by this script).
install_file "$SCRIPT_DIR/global-settings.json" "$CLAUDE_DIR/settings.json" "settings.json"

# Codex hooks: derived from the same global-settings.json (single source of truth)
# so the git-sync logic never drifts. Only the SessionStart hook ports — it's plain
# git/shell; Claude's other hooks depend on Claude-only env vars (OCTO_AGENT_ID/
# OCTO_HOOK_FILE) and the Agent/Task tool, which Codex does not set. Needs jq, which
# the hooks already require at runtime.
if command -v jq >/dev/null 2>&1; then
    write_if_changed \
        "$(jq '{hooks: {SessionStart: .hooks.SessionStart}}' "$SCRIPT_DIR/global-settings.json")" \
        "$CODEX_DIR/hooks.json" "hooks.json"
else
    echo "  WARNING: jq not found; skipped Codex hooks.json (rerun with jq installed)."
fi

# Install Codex CLI (npm i -g @openai/codex) — the `claude` equivalent binary.
install_codex_cli() {
    if command -v codex >/dev/null 2>&1; then
        echo "  Codex CLI already installed: $(command -v codex)"
        return
    fi
    if ! command -v npm >/dev/null 2>&1; then
        echo "  WARNING: npm not found. Install Node.js, then: npm i -g @openai/codex"
        return
    fi
    echo "  Installing Codex CLI (npm i -g @openai/codex)..."
    # Try unprivileged first (works when npm's global prefix is user-owned, e.g.
    # macOS/brew). On a root-owned prefix (e.g. apt's /usr/local) npm fails EACCES;
    # retry once with sudo.
    if out="$(npm i -g @openai/codex 2>&1)"; then
        echo "  Installed Codex CLI: $(command -v codex)"
    elif printf '%s' "$out" | grep -q EACCES && command -v sudo >/dev/null 2>&1; then
        echo "  npm global prefix needs root; retrying with sudo..."
        if out="$(sudo npm i -g @openai/codex 2>&1)"; then
            echo "  Installed Codex CLI: $(command -v codex)"
        else
            echo "  WARNING: codex install failed; rerun: sudo npm i -g @openai/codex"
            printf '%s\n' "$out" | sed 's/^/    /'
        fi
    else
        echo "  WARNING: codex install failed; rerun: npm i -g @openai/codex"
        printf '%s\n' "$out" | sed 's/^/    /'
    fi
}

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

# Install Node.js + npm — the runtime for the Codex CLI and Playwright MCP.
# brew on macOS, the system package manager on Linux (sudo). A failed install is
# a warning, not fatal — the consumers below degrade to their own warnings.
install_node() {
    if command -v node >/dev/null 2>&1; then
        echo "  Node.js already installed: $(command -v node) ($(node --version))"
        return
    fi
    local pm=""
    case "$(uname -s)" in
        Darwin)
            if command -v brew >/dev/null 2>&1; then
                echo "  Installing Node.js via Homebrew..."
                brew install node || echo "  WARNING: brew install node failed."
            else
                echo "  WARNING: node not found and Homebrew unavailable. Install from https://nodejs.org/"
            fi
            return
            ;;
        Linux)
            if   command -v apt-get >/dev/null 2>&1; then pm="sudo apt-get install -y nodejs npm"
            elif command -v dnf     >/dev/null 2>&1; then pm="sudo dnf install -y nodejs npm"
            elif command -v pacman  >/dev/null 2>&1; then pm="sudo pacman -S --noconfirm nodejs npm"
            elif command -v zypper  >/dev/null 2>&1; then pm="sudo zypper install -y nodejs npm"
            elif command -v apk     >/dev/null 2>&1; then pm="sudo apk add nodejs npm"
            fi
            if [ -n "$pm" ]; then
                echo "  Installing Node.js ($pm)..."
                $pm || echo "  WARNING: node install failed; install Node.js from https://nodejs.org/"
            else
                echo "  WARNING: node not found and no known package manager. Install from https://nodejs.org/"
            fi
            ;;
        *)
            echo "  WARNING: node not found. Install Node.js from https://nodejs.org/"
            ;;
    esac
}

# Pre-cache Playwright MCP + Chromium so the first project use is fast.
# Used by project-scoped Playwright MCP servers (e.g. octo-family-doc/.mcp.json).
# This only warms the cache; it does NOT register the MCP server globally — each
# project opts in via its own .mcp.json. Requires node/npm from install_node.
install_playwright() {
    if ! command -v npx >/dev/null 2>&1; then
        echo "  WARNING: npx not found; skipped Playwright MCP pre-cache."
        return
    fi
    # Truly one-time: skip once Chromium is downloaded. Without this guard the
    # npx ...@latest calls re-resolve from the registry on every install run.
    local pw_cache="$HOME/.cache/ms-playwright"
    [ "$(uname -s)" = Darwin ] && pw_cache="$HOME/Library/Caches/ms-playwright"
    [ -n "${PLAYWRIGHT_BROWSERS_PATH:-}" ] && pw_cache="$PLAYWRIGHT_BROWSERS_PATH"
    if compgen -G "$pw_cache/chromium-*" >/dev/null 2>&1; then
        echo "  Playwright Chromium already cached"
        return
    fi
    echo "  Pre-caching Playwright MCP + Chromium (one-time)..."
    npx -y @playwright/mcp@latest --help >/dev/null 2>&1 || true
    npx -y playwright@latest install chromium >/dev/null 2>&1 || true
}

install_swift_lsp
install_node          # node + npm, needed by the two steps below
install_codex_cli     # npm i -g @openai/codex
install_playwright    # warms the Playwright MCP cache

echo ""
echo "Done. Installed skills:"
ls -1 "$CLAUDE_DIR/skills/"
echo ""
echo "Skills are available in ALL projects for both Claude Code (~/.claude) and Codex (~/.codex)."
echo "Project-specific skills go in <project>/.claude/skills/ (or <project>/.codex/skills/)."
