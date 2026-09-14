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
CODEX_DIR="${CODEX_HOME:-$HOME/.codex}"
CODEX_LAUNCHER_DIR="$HOME/.local/bin"
CODEX_STANDALONE_BIN="${CODEX_HOME:-$HOME/.codex}/packages/standalone/current/bin/codex"
RESTART_CODEX_APP_SERVER=0

usage() {
    echo "Usage: $0 [--restart]"
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --restart)
            RESTART_CODEX_APP_SERVER=1
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
    shift
done

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
codex_config="$(python3 "$SCRIPT_DIR/scripts/render_codex_config.py" \
    "$SCRIPT_DIR/global-codex-config.toml" "$CODEX_DIR/config.toml")"
write_if_changed "$codex_config" "$CODEX_DIR/config.toml" "config.toml"
install_file "$SCRIPT_DIR/global-codex-rules.rules" "$CODEX_DIR/rules/default.rules" "Codex default.rules"

# Codex status comes from its App Server, so only the shared Git Sync hook is
# installed. OctoCode activity hooks remain Claude-only. Needs jq because the
# retained hook uses it.
if command -v jq >/dev/null 2>&1; then
    write_if_changed \
        "$(jq '{hooks: {
            SessionStart: .hooks.SessionStart
        }}' "$SCRIPT_DIR/global-settings.json")" \
        "$CODEX_DIR/hooks.json" "hooks.json"
else
    echo "  WARNING: jq not found; skipped Codex hooks.json (rerun with jq installed)."
fi

# Run a command in its own process group and terminate that entire group after
# the deadline. This bounds both the official installer and its child downloads.
run_with_timeout() {
    local timeout_seconds="$1"
    shift
    local command_pid timeout_pid status
    set -m
    "$@" <&0 &
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

# Install OpenAI's standalone Codex package.
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
    echo "  Installing/updating official standalone Codex CLI..."
    if out="$(run_with_timeout "$timeout_seconds" sh -c '
        curl -fsSL https://chatgpt.com/codex/install.sh | \
            CODEX_NON_INTERACTIVE=1 CODEX_INSTALL_DIR="$1" sh
    ' sh "$CODEX_LAUNCHER_DIR" 2>&1)"; then
        echo "  Installed/updated official standalone Codex CLI."
    else
        echo "  WARNING: standalone Codex install failed; rerun this repository's ./install.sh."
        printf '%s\n' "$out" | sed 's/^/    /'
    fi
}

# Expose the official executable directly. Older installs placed a custom
# wrapper at this path; replace it instead of modifying Codex's argv.
install_codex_command() {
    local dest="$CODEX_LAUNCHER_DIR/codex"
    if [ ! -x "$CODEX_STANDALONE_BIN" ]; then
        if [ -f "$dest" ] &&
            grep -Fq 'CODEX_NPM_PREFIX="${CODEX_NPM_PREFIX:-$HOME/.local/share/octo-codex}"' "$dest" &&
            grep -Fq 'update_codex() {' "$dest"; then
            rm -f "$dest"
            echo "  Removed legacy Codex wrapper"
        fi
        echo "  WARNING: standalone Codex is unavailable; no official command was installed."
        return
    fi
    mkdir -p "$CODEX_LAUNCHER_DIR"
    if [ -L "$dest" ] && [ "$(readlink "$dest")" = "$CODEX_STANDALONE_BIN" ]; then
        echo "  Official Codex command unchanged"
        return
    fi
    if [ -e "$dest" ] || [ -L "$dest" ]; then
        rm -f "$dest"
    fi
    ln -s "$CODEX_STANDALONE_BIN" "$dest"
    echo "  Installed official Codex command"
}

# Bootstrap may replace the running server. Only use it for a fresh install or
# when the user explicitly requests --restart.
bootstrap_codex_app_server() {
    case "$(uname -s)" in
        Darwin|Linux) ;;
        *)
            echo "  WARNING: skipped managed Codex app-server; daemon bootstrap requires macOS or Linux."
            return 1
            ;;
    esac
    if [ ! -x "$CODEX_STANDALONE_BIN" ]; then
        echo "  WARNING: standalone Codex is unavailable; skipped managed app-server bootstrap."
        return 1
    fi

    local out
    if out="$("$CODEX_STANDALONE_BIN" app-server daemon bootstrap --remote-control 2>&1)"; then
        echo "  Codex managed app-server ready (Remote Control socket reused)"
    else
        case "$out" in
            *"app server is running but is not managed by codex app-server daemon"*)
                echo "  Existing Remote Control app-server ready (socket reused)"
                return 2
                ;;
            *)
                echo "  WARNING: Codex managed app-server bootstrap failed."
                printf '%s\n' "$out" | sed 's/^/    /'
                return 1
                ;;
        esac
    fi
    return 0
}

restart_codex_app_server() {
    local out
    if out="$("$CODEX_STANDALONE_BIN" app-server daemon restart 2>&1)"; then
        echo "  Restarted Codex managed app-server"
        return
    fi

    echo "  ERROR: Codex managed app-server restart failed." >&2
    printf '%s\n' "$out" | sed 's/^/    /' >&2
    return 1
}

stop_unmanaged_codex_app_server() {
    local socket="$CODEX_DIR/app-server-control/app-server-control.sock"
    local kill_bin owner_command owner_pid
    local -a owner_pids proxy_pids

    if ! command -v lsof >/dev/null 2>&1; then
        echo "  ERROR: lsof is required to identify the unmanaged Codex app-server safely." >&2
        return 1
    fi
    kill_bin="$(type -P kill 2>/dev/null || true)"
    if [ -z "$kill_bin" ]; then
        echo "  ERROR: kill command not found; cannot stop the unmanaged Codex app-server." >&2
        return 1
    fi

    mapfile -t owner_pids < <(lsof -t -- "$socket" 2>/dev/null | sort -u)
    if [ "${#owner_pids[@]}" -ne 1 ]; then
        echo "  ERROR: expected one Codex app-server socket owner, found ${#owner_pids[@]}." >&2
        return 1
    fi
    owner_pid="${owner_pids[0]}"
    owner_command="$(ps -p "$owner_pid" -o args= 2>/dev/null || true)"
    case "$owner_command" in
        *codex*app-server*--listen\ unix://*) ;;
        *)
            echo "  ERROR: refused to stop unexpected socket owner PID $owner_pid: $owner_command" >&2
            return 1
            ;;
    esac

    mapfile -t proxy_pids < <(
        ps -eo pid=,args= | awk \
            '$0 ~ /[/]codex([.]js)? app-server proxy([[:space:]]|$)/ { print $1 }'
    )
    if [ "${#proxy_pids[@]}" -gt 0 ]; then
        "$kill_bin" -TERM "${proxy_pids[@]}"
    fi
    "$kill_bin" -TERM "$owner_pid"

    local attempt
    for attempt in {1..10}; do
        if ! "$kill_bin" -0 "$owner_pid" 2>/dev/null; then
            return
        fi
        sleep 1
    done
    "$kill_bin" -KILL "$owner_pid"
}

replace_unmanaged_codex_app_server() {
    local out replacement_status=0
    if ! out="$("$CODEX_STANDALONE_BIN" remote-control stop 2>&1)"; then
        case "$out" in
            *"app server is running but is not managed by codex app-server daemon"*)
                stop_unmanaged_codex_app_server
                ;;
            *)
                echo "  ERROR: could not stop the existing Remote Control app-server." >&2
                printf '%s\n' "$out" | sed 's/^/    /' >&2
                return 1
                ;;
        esac
    fi

    bootstrap_codex_app_server || replacement_status=$?
    if [ "$replacement_status" -ne 0 ]; then
        echo "  ERROR: could not start the updated Codex managed app-server." >&2
        return 1
    fi
    remove_obsolete_codex_remote_services
    echo "  Restarted Codex Remote Control app-server under native daemon management"
}

# Older installers created a second app-server under systemd. Codex Remote
# Control already owns a native daemon, so the extra server competes for the
# same remote identity and chat writer. Remove both historical unit names.
remove_obsolete_codex_remote_services() {
    [ "$(uname -s)" = Linux ] || return 0
    local unit unit_dest cleaned=0
    for unit in octo-codex-remote-control.service octo-codex-app-server.service; do
        unit_dest="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/$unit"
        if ! command -v systemctl >/dev/null 2>&1; then
            if [ -e "$unit_dest" ] || [ -L "$unit_dest" ]; then
                echo "  WARNING: systemctl not found; could not remove obsolete $unit."
            fi
            continue
        fi
        if [ ! -e "$unit_dest" ] && [ ! -L "$unit_dest" ] &&
            ! systemctl --user is-active --quiet "$unit" &&
            ! systemctl --user is-enabled --quiet "$unit"; then
            continue
        fi
        if ! systemctl --user stop "$unit" >/dev/null 2>&1; then
            echo "  WARNING: could not stop obsolete $unit; left it installed."
            continue
        fi
        if ! systemctl --user disable "$unit" >/dev/null 2>&1; then
            echo "  WARNING: could not disable obsolete $unit; left it installed."
            continue
        fi
        rm -f "$unit_dest"
        cleaned=1
        echo "  Removed obsolete $unit"
    done
    if [ "$cleaned" -eq 1 ] && ! systemctl --user daemon-reload >/dev/null 2>&1; then
        echo "  WARNING: removed obsolete Codex service files, but systemd did not reload."
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
install_node          # node + npm, needed by Playwright
# Avoid touching the runtime on an existing installation, even when its socket
# is temporarily absent. Updating the package/bootstrap can replace the daemon;
# live config reloads can also change permissions underneath active turns.
if [ "$RESTART_CODEX_APP_SERVER" -eq 0 ] && {
    [ -x "$CODEX_STANDALONE_BIN" ] ||
    [ -e "$CODEX_DIR/app-server-control/app-server-control.sock" ] ||
    [ -e "$CODEX_DIR/app-server-daemon/app-server.pid" ]
}; then
    install_codex_command
    echo "  Preserved existing Codex runtime; use --restart to update and restart it."
    echo "  Installed configuration will apply when Codex next loads it."
else
    install_codex_standalone # official standalone package
    install_codex_command # direct PATH entry; no argv-modifying wrapper
    bootstrap_status=0
    bootstrap_codex_app_server || bootstrap_status=$?
    if [ "$bootstrap_status" -eq 0 ]; then # one daemon/socket shared by Remote Control + OctoCode
        remove_obsolete_codex_remote_services # native Codex daemon owns Remote Control
    else
        if [ "$bootstrap_status" -eq 2 ]; then
            if [ "$RESTART_CODEX_APP_SERVER" -eq 0 ]; then
                echo "  Preserved existing services because Remote Control owns the app-server."
            fi
        else
            echo "  Preserved existing services because no replacement app-server was started."
        fi
    fi
    if [ "$RESTART_CODEX_APP_SERVER" -eq 1 ]; then
        case "$bootstrap_status" in
            0)
                restart_codex_app_server
                ;;
            2)
                replace_unmanaged_codex_app_server
                ;;
            *)
                echo "  ERROR: cannot restart because no Codex app-server is available." >&2
                exit 1
                ;;
        esac
    fi
fi
install_playwright    # warms the Playwright MCP cache

echo ""
echo "Done. Installed skills:"
ls -1 "$CLAUDE_DIR/skills/"
echo ""
echo "Skills are available in ALL projects for both Claude Code (~/.claude) and Codex (~/.codex)."
echo "Codex review agents are available in ALL projects from ~/.codex/agents/."
echo "Project-specific skills go in <project>/.claude/skills/ (or <project>/.codex/skills/)."
