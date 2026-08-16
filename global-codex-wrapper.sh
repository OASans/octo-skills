#!/usr/bin/env bash
set -euo pipefail

CODEX_NPM_PREFIX="${CODEX_NPM_PREFIX:-$HOME/.local/share/octo-codex}"
UPDATE_LOCK="$CODEX_NPM_PREFIX/.update-lock"
export OCTO_HOOK_FILE="${OCTO_HOOK_FILE:-/tmp/octo-hook-octo-code-default.jsonl}"

print_update_failure() {
    local message="$1" output="$2"
    printf 'WARNING: %s; starting the installed Codex version.\n' "$message" >&2
    [ -z "$output" ] || printf '%s\n' "$output" | sed 's/^/  /' >&2
}

update_codex() {
    local codex_js="$1" current_version="" current_label latest_version update_output
    if [ -f "$codex_js" ]; then
        current_version="$(node "$codex_js" --version 2>/dev/null)" || current_version=""
    fi

    if ! latest_version="$(npm view @openai/codex@latest version \
        --loglevel=error --fetch-retries=0 --fetch-timeout=5000 2>&1)"; then
        print_update_failure "Codex update check failed" "$latest_version"
        return
    fi
    if [[ ! "$latest_version" =~ ^[0-9]+\.[0-9]+\.[0-9]+([+-][0-9A-Za-z.-]+)?$ ]]; then
        print_update_failure "npm returned an invalid Codex version" "$latest_version"
        return
    fi
    [ "$current_version" = "codex-cli $latest_version" ] && return

    if ! update_output="$(npm install --global --prefix "$CODEX_NPM_PREFIX" \
        "@openai/codex@$latest_version" 2>&1)"; then
        print_update_failure "Codex update failed" "$update_output"
        return
    fi
    current_label="${current_version#codex-cli }"
    [ -n "$current_label" ] || current_label="not installed"
    printf 'Updated Codex: %s -> %s\n' "$current_label" "$latest_version"
}

cleanup_update_lock() {
    rm -f "$UPDATE_LOCK/pid"
    rmdir "$UPDATE_LOCK" 2>/dev/null || true
}

clear_stale_update_lock() {
    local owner_pid=""
    [ -r "$UPDATE_LOCK/pid" ] || return 1
    IFS= read -r owner_pid < "$UPDATE_LOCK/pid" || return 1
    [[ "$owner_pid" =~ ^[0-9]+$ ]] || return 1
    kill -0 "$owner_pid" 2>/dev/null && return 1
    rm -f "$UPDATE_LOCK/pid"
    rmdir "$UPDATE_LOCK" 2>/dev/null
}

wait_for_update() {
    local attempts=0
    while [ -d "$UPDATE_LOCK" ] && [ "$attempts" -lt 300 ]; do
        sleep 0.1
        attempts=$((attempts + 1))
    done
    [ ! -d "$UPDATE_LOCK" ] || print_update_failure \
        "another Codex update is still running" ""
}

command -v npm >/dev/null 2>&1 || { echo "ERROR: npm is required to launch Codex." >&2; exit 1; }
command -v node >/dev/null 2>&1 || { echo "ERROR: node is required to launch Codex." >&2; exit 1; }

mkdir -p "$CODEX_NPM_PREFIX"
if ! codex_root="$(npm root --global --prefix "$CODEX_NPM_PREFIX" 2>/dev/null)"; then
    echo "ERROR: could not resolve the Codex npm prefix." >&2
    exit 1
fi
codex_js="$codex_root/@openai/codex/bin/codex.js"

lock_acquired=0
if mkdir "$UPDATE_LOCK" 2>/dev/null; then
    lock_acquired=1
elif clear_stale_update_lock && mkdir "$UPDATE_LOCK" 2>/dev/null; then
    lock_acquired=1
fi

if [ "$lock_acquired" -eq 1 ]; then
    printf '%s\n' "$$" > "$UPDATE_LOCK/pid"
    trap cleanup_update_lock EXIT INT TERM
    update_codex "$codex_js"
    cleanup_update_lock
    trap - EXIT INT TERM
else
    wait_for_update
fi

[ -f "$codex_js" ] || {
    echo "ERROR: Codex is not installed under $CODEX_NPM_PREFIX; run octo-skills/install.sh." >&2
    exit 1
}

# Hooks are installed from this repository. Bypass per-definition trust hashes
# so hook updates cannot prevent unattended Remote Control from starting.
if [ "${1:-}" = update ]; then
    exec env NPM_CONFIG_PREFIX="$CODEX_NPM_PREFIX" \
        node "$codex_js" --dangerously-bypass-hook-trust "$@"
fi

# OctoCode panes join the existing Remote Control App Server so its WebSocket
# stream is the authoritative root/subagent status source. Preserve explicit
# remote endpoints and non-TUI subcommands.
is_tui_invocation() {
    while [ "$#" -gt 0 ]; do
        case "$1" in
            -c|--config|--enable|--disable|-i|--image|-m|--model|--local-provider|-p|--profile|-s|--sandbox|-a|--ask-for-approval|-C|--cd|--add-dir|--remote|--remote-auth-token-env)
                [ "$#" -ge 2 ] || return 0
                shift 2
                ;;
            --config=*|--enable=*|--disable=*|--image=*|--model=*|--local-provider=*|--profile=*|--sandbox=*|--ask-for-approval=*|--cd=*|--add-dir=*|--remote=*|--remote-auth-token-env=*)
                shift
                ;;
            --oss|--approve-for-me|--dangerously-bypass-approvals-and-sandbox|--dangerously-bypass-hook-trust|--search|--no-alt-screen|--strict-config)
                shift
                ;;
            exec|e|review|login|logout|mcp|plugin|mcp-server|app-server|remote-control|completion|update|doctor|sandbox|debug|apply|resume|archive|delete|unarchive|fork|cloud|exec-server|features|help)
                return 1
                ;;
            -*) shift ;;
            *) return 0 ;;
        esac
    done
    return 0
}

has_remote_arg=0
for arg in "$@"; do
    case "$arg" in
        --remote|--remote=*) has_remote_arg=1 ;;
    esac
done
app_server_socket="${CODEX_HOME:-$HOME/.codex}/app-server-control/app-server-control.sock"
if [ -n "${OCTO_AGENT_ID:-}" ] && [ "$has_remote_arg" -eq 0 ] && is_tui_invocation "$@"; then
    if [ ! -S "$app_server_socket" ]; then
        echo "WARNING: Codex App Server socket is unavailable; starting this pane locally." >&2
        exec node "$codex_js" --dangerously-bypass-hook-trust "$@"
    fi
    routing_key="$(printf '%s' "$OCTO_HOOK_FILE" | tr -c 'A-Za-z0-9._-' '_')"
    routing_root="/tmp/octocode-app-server-cwd"
    routing_cwd="$routing_root/$routing_key-$OCTO_AGENT_ID"
    mkdir -p "$routing_root"
    if [ -e "$routing_cwd" ] && [ ! -L "$routing_cwd" ]; then
        echo "ERROR: Codex App Server routing path is not a symlink: $routing_cwd" >&2
        exit 1
    fi
    if [ -L "$routing_cwd" ]; then
        ln -sfn "$PWD" "$routing_cwd"
    else
        ln -s "$PWD" "$routing_cwd"
    fi
    exec node "$codex_js" --dangerously-bypass-hook-trust \
        --remote unix:// --cd "$routing_cwd" "$@"
fi
exec node "$codex_js" --dangerously-bypass-hook-trust "$@"
