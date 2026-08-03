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
CODEX_NPM_PREFIX="${CODEX_NPM_PREFIX:-$HOME/.local/share/octo-codex}"
CODEX_LAUNCHER_DIR="$HOME/.local/bin"
CODEX_STANDALONE_BIN="${CODEX_HOME:-$HOME/.codex}/packages/standalone/current/bin/codex"
LAST_INSTALL_CHANGED=0
CODEX_CONFIG_CHANGED=0
CODEX_HOOKS_CHANGED=0

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
    LAST_INSTALL_CHANGED=0
    mkdir -p "$(dirname "$dest")"
    if [ ! -f "$dest" ]; then
        printf '%s\n' "$content" > "$dest"
        LAST_INSTALL_CHANGED=1
        echo "  Installed $label (new)"
    elif [ "$content" = "$(cat "$dest")" ]; then
        echo "  $label unchanged"
    else
        printf '%s\n' "$content" > "$dest"
        LAST_INSTALL_CHANGED=1
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
    LAST_INSTALL_CHANGED=0
    [ -f "$src" ] || return 0
    shopt -u patsub_replacement 2>/dev/null || true
    content="$(cat "$src")"
    write_if_changed "${content//__HOME__/$HOME}" "$dest" "$label"
}

# Skills: same SKILL.md standard for both agents (agentskills.io open spec).
install_skills "$CLAUDE_DIR/skills"
install_skills "$CODEX_DIR/skills"

# Reusable Codex agents. Preserve unrelated personal agents in the target.
for agent_file in "$SCRIPT_DIR/codex-agents"/*.toml; do
    [ -f "$agent_file" ] || continue
    install_file "$agent_file" "$CODEX_DIR/agents/$(basename "$agent_file")" \
        "Codex agent $(basename "$agent_file" .toml)"
done

# Global memory / prompt: one source (global-CLAUDE.md) -> Claude CLAUDE.md and
# Codex AGENTS.md (merged root-first by Codex, same as CLAUDE.md).
install_file "$SCRIPT_DIR/global-CLAUDE.md" "$CLAUDE_DIR/CLAUDE.md"  "CLAUDE.md"
install_file "$SCRIPT_DIR/global-CLAUDE.md" "$CODEX_DIR/AGENTS.md"   "AGENTS.md"

# Settings. Claude Code uses JSON; Codex uses TOML.
install_file "$SCRIPT_DIR/global-settings.json" "$CLAUDE_DIR/settings.json" "settings.json"
install_file "$SCRIPT_DIR/global-codex-config.toml" "$CODEX_DIR/config.toml" "config.toml"
CODEX_CONFIG_CHANGED="$LAST_INSTALL_CHANGED"
install_file "$SCRIPT_DIR/global-codex-rules.rules" "$CODEX_DIR/rules/default.rules" "Codex default.rules"

# Codex hooks.json is derived entirely from global-settings.json (single source of
# truth). OctoCode exports OCTO_AGENT_ID/OCTO_HOOK_FILE onto the agent pane, so the
# canonical git-sync + agent-activity hooks run verbatim in Codex. We port the events
# Codex shares and drop the Claude-only extras (the Agent/Task model gate, the
# AskUserQuestion/ExitPlanMode matcher, the Skill usage logger) by taking only the
# first (no-matcher) group of PreToolUse/PostToolUse. Needs jq (hooks require it too).
if command -v jq >/dev/null 2>&1; then
    write_if_changed \
        "$(jq '{hooks: {
            SessionStart:      .hooks.SessionStart,
            UserPromptSubmit:  .hooks.UserPromptSubmit,
            PreToolUse:        [.hooks.PreToolUse[0]],
            PostToolUse:       [.hooks.PostToolUse[0]],
            PermissionRequest: .hooks.PermissionRequest,
            Stop:              .hooks.Stop
        }}' "$SCRIPT_DIR/global-settings.json")" \
        "$CODEX_DIR/hooks.json" "hooks.json"
    CODEX_HOOKS_CHANGED="$LAST_INSTALL_CHANGED"
else
    echo "  WARNING: jq not found; skipped Codex hooks.json (rerun with jq installed)."
fi

# Install Codex into the user-owned prefix used by the auto-updating launcher.
install_codex_cli() {
    if ! command -v npm >/dev/null 2>&1; then
        echo "  WARNING: npm not found. Install Node.js, then: npm i -g @openai/codex"
        return
    fi
    local codex_root codex_js out
    if ! codex_root="$(npm root --global --prefix "$CODEX_NPM_PREFIX" 2>/dev/null)"; then
        echo "  WARNING: could not resolve the Codex npm prefix."
        return
    fi
    codex_js="$codex_root/@openai/codex/bin/codex.js"
    if [ -f "$codex_js" ] && node "$codex_js" --version >/dev/null 2>&1; then
        echo "  Codex CLI already installed: $codex_js"
        return
    fi

    echo "  Installing Codex CLI into $CODEX_NPM_PREFIX..."
    if out="$(npm install --global --prefix "$CODEX_NPM_PREFIX" @openai/codex@latest 2>&1)"; then
        echo "  Installed Codex CLI: $codex_js"
    else
        echo "  WARNING: codex install failed; rerun: npm install --global --prefix '$CODEX_NPM_PREFIX' @openai/codex@latest"
        printf '%s\n' "$out" | sed 's/^/    /'
    fi
}

# Run a command in its own process group and terminate that entire group after
# the deadline. This bounds both the official installer and its child downloads.
run_with_timeout() {
    local timeout_seconds="$1"
    shift
    local command_pid timeout_pid status
    set -m
    "$@" &
    command_pid=$!
    (
        sleep "$timeout_seconds"
        kill -TERM -- "-$command_pid" 2>/dev/null || true
    ) &
    timeout_pid=$!
    set +m

    status=0
    wait "$command_pid" || status=$?
    kill -TERM -- "-$timeout_pid" 2>/dev/null || true
    wait "$timeout_pid" 2>/dev/null || true
    return "$status"
}

# Refresh a running app-server's user config without restarting it. Replacing
# config.toml on disk is not enough: a durable daemon can retain its old project
# trust map until it exits, causing trusted project .codex/ layers to warn and
# stay disabled. An empty batch write preserves the managed file byte-for-byte;
# reloadUserConfig updates every loaded thread in place.
reload_codex_user_config() {
    local socket="$CODEX_DIR/app-server-control/app-server-control.sock"
    [ -e "$socket" ] || return 0

    local codex_bin="$CODEX_STANDALONE_BIN"
    if [ ! -x "$codex_bin" ]; then
        codex_bin="$(command -v codex 2>/dev/null || true)"
    fi
    if [ -z "$codex_bin" ]; then
        echo "  WARNING: config.toml installed, but Codex is unavailable for a live config reload."
        return
    fi

    local response
    if response="$(
        (
            printf '%s\n' \
                '{"id":1,"method":"initialize","params":{"clientInfo":{"name":"octo-skills-installer","version":"1"}}}' \
                '{"method":"initialized","params":{}}' \
                "{\"id\":2,\"method\":\"config/batchWrite\",\"params\":{\"edits\":[],\"filePath\":\"$CODEX_DIR/config.toml\",\"reloadUserConfig\":true}}"
            sleep 1
        ) |
            run_with_timeout 5 "$codex_bin" app-server proxy --sock "$socket" 2>/dev/null
    )" &&
        printf '%s\n' "$response" | grep -q '"id":2.*"status":"ok"'; then
        echo "  Reloaded config.toml in the running Codex app-server"
    else
        echo "  WARNING: config.toml installed, but the running Codex app-server did not reload it."
        echo "           New sessions will use it after the app-server next starts."
    fi
}

# Install OpenAI's standalone Codex package alongside the npm-managed package.
# The official installer places a symlink in CODEX_LAUNCHER_DIR; the launcher
# step below replaces that symlink while leaving the standalone package intact.
install_codex_standalone() {
    case "$(uname -s)" in
        Darwin|Linux) ;;
        *)
            echo "  WARNING: skipped standalone Codex CLI; the official shell installer supports macOS and Linux."
            return
            ;;
    esac
    if ! command -v curl >/dev/null 2>&1; then
        echo "  WARNING: curl not found; skipped the standalone Codex CLI install."
        return
    fi
    if [ -x "$CODEX_STANDALONE_BIN" ] && "$CODEX_STANDALONE_BIN" --version >/dev/null 2>&1; then
        echo "  Standalone Codex CLI already installed: $CODEX_STANDALONE_BIN"
        return
    fi
    local out timeout_seconds="${OCTO_CODEX_INSTALL_TIMEOUT_SECONDS:-300}"
    case "$timeout_seconds" in
        ''|*[!0-9]*)
            echo "  WARNING: OCTO_CODEX_INSTALL_TIMEOUT_SECONDS must be a positive integer."
            return
            ;;
    esac
    if [ "$timeout_seconds" -lt 1 ]; then
        echo "  WARNING: OCTO_CODEX_INSTALL_TIMEOUT_SECONDS must be a positive integer."
        return
    fi
    echo "  Installing official standalone Codex CLI..."
    if out="$(run_with_timeout "$timeout_seconds" sh -c '
        curl -fsSL https://chatgpt.com/codex/install.sh | \
            CODEX_NON_INTERACTIVE=1 CODEX_INSTALL_DIR="$1" sh
    ' sh "$CODEX_LAUNCHER_DIR" 2>&1)"; then
        echo "  Installed official standalone Codex CLI."
    else
        echo "  WARNING: standalone Codex install failed; rerun this repository's ./install.sh."
        printf '%s\n' "$out" | sed 's/^/    /'
    fi
}

install_codex_wrapper() {
    local dest="$CODEX_LAUNCHER_DIR/codex"
    [ ! -L "$dest" ] || rm -f "$dest"
    install_file "$SCRIPT_DIR/global-codex-wrapper.sh" "$dest" "Codex launcher"
    chmod +x "$dest"
}

# Keep Remote Control outside transient SSH session scopes. systemd supervises
# the foreground process, while CODEX_HOME keeps the installed config and trusted
# hook state authoritative for every remote session.
install_codex_remote_control_service() {
    [ "$(uname -s)" = Linux ] || return
    if ! command -v systemctl >/dev/null 2>&1; then
        echo "  WARNING: systemctl not found; skipped Codex Remote Control service."
        return
    fi

    local unit="octo-codex-remote-control.service"
    local unit_dest="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/$unit"
    local node_bin npm_bin node_dir npm_dir runtime_path service_content
    node_bin="$(command -v node 2>/dev/null || true)"
    npm_bin="$(command -v npm 2>/dev/null || true)"
    if [[ "$node_bin" != /* || "$npm_bin" != /* ]]; then
        echo "  WARNING: node/npm have no stable absolute path; skipped Codex Remote Control service."
        return
    fi
    node_dir="${node_bin%/*}"
    npm_dir="${npm_bin%/*}"
    runtime_path="$node_dir"
    [ "$npm_dir" = "$node_dir" ] || runtime_path="$runtime_path:$npm_dir"

    shopt -u patsub_replacement 2>/dev/null || true
    service_content="$(cat "$SCRIPT_DIR/global-codex-remote-control.service")"
    service_content="${service_content//__HOME__/$HOME}"
    service_content="${service_content//__NODE_NPM_PATH__/$runtime_path}"
    write_if_changed "$service_content" "$unit_dest" "Codex Remote Control service"
    local unit_changed="$LAST_INSTALL_CHANGED"

    if ! systemctl --user daemon-reload >/dev/null 2>&1; then
        echo "  WARNING: systemd user services are unavailable; installed but did not enable $unit."
        return
    fi

    local user_name linger
    user_name="$(id -un)"
    linger="$(loginctl show-user "$user_name" -p Linger --value 2>/dev/null || true)"
    if [ "$linger" != yes ] && ! loginctl enable-linger "$user_name" >/dev/null 2>&1; then
        echo "  WARNING: skipped persistent Codex Remote Control startup. Run:"
        echo "           sudo loginctl enable-linger '$user_name', then rerun ./install.sh"
        return
    fi

    if ! systemctl --user enable "$unit" >/dev/null 2>&1; then
        echo "  WARNING: could not enable $unit."
        return
    fi

    if [ -f "$CODEX_DIR/app-server-daemon/app-server.pid" ] &&
        ! "$CODEX_LAUNCHER_DIR/codex" remote-control stop --json >/dev/null 2>&1; then
        echo "  WARNING: could not stop the old Codex Remote daemon; skipped service startup."
        return
    fi

    if systemctl --user is-active --quiet "$unit"; then
        if [ "$unit_changed" -eq 1 ] || [ "$CODEX_CONFIG_CHANGED" -eq 1 ] ||
            [ "$CODEX_HOOKS_CHANGED" -eq 1 ]; then
            if systemctl --user restart "$unit" >/dev/null 2>&1; then
                echo "  Restarted Codex Remote Control service"
            else
                echo "  WARNING: could not restart $unit."
            fi
        else
            echo "  Codex Remote Control service already running"
        fi
    elif systemctl --user start "$unit" >/dev/null 2>&1; then
        echo "  Started Codex Remote Control service"
    else
        echo "  WARNING: could not start $unit."
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
install_node          # node + npm, needed by npm Codex and Playwright
install_codex_cli     # user-owned npm prefix; launcher updates it on every start
install_codex_standalone # official standalone package; launcher remains the PATH entry
install_codex_wrapper # launcher: auto-update, hook trust comes from config.toml hashes
reload_codex_user_config # refresh project trust without interrupting running tasks
install_codex_remote_control_service # supervised, boot-persistent Remote Control on Linux
install_playwright    # warms the Playwright MCP cache

echo ""
echo "Done. Installed skills:"
ls -1 "$CLAUDE_DIR/skills/"
echo ""
echo "Skills are available in ALL projects for both Claude Code (~/.claude) and Codex (~/.codex)."
echo "Codex review agents are available in ALL projects from ~/.codex/agents/."
echo "Project-specific skills go in <project>/.claude/skills/ (or <project>/.codex/skills/)."
