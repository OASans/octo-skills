#!/usr/bin/env bash
set -euo pipefail

CODEX_NPM_PREFIX="${CODEX_NPM_PREFIX:-$HOME/.local/share/octo-codex}"
UPDATE_LOCK="$CODEX_NPM_PREFIX/.update-lock"

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

if [ "${1:-}" = update ]; then
    exec env NPM_CONFIG_PREFIX="$CODEX_NPM_PREFIX" \
        node "$codex_js" "$@"
fi
exec node "$codex_js" --dangerously-bypass-hook-trust "$@"
