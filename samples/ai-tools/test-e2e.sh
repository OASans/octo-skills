#!/bin/bash
# Run OctoCode instance E2E tests (non-Slack).
# These are fast (~50s), use tmux but no external APIs.
# Usage:
#   ./ai-tools/test-e2e.sh            — all instance E2E tests
#   ./ai-tools/test-e2e.sh <name>     — single E2E test by name
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

process_cleanup() {
    # Kill orphaned test daemon processes (e2e-* prefixes)
    pkill -f 'octo-code-daemon.*--session-name octo-code-e2e-' 2>/dev/null || true
    # Kill orphaned test tmux servers (each test uses -L <session_name> for isolation).
    # Socket files live at /tmp/tmux-$UID/octo-code-e2e-*.
    local tmux_dir="/tmp/tmux-$(id -u)"
    if [[ -d "$tmux_dir" ]]; then
        for sock in "$tmux_dir"/octo-code-e2e-*; do
            [[ -e "$sock" ]] || continue
            local sock_name
            sock_name=$(basename "$sock")
            tmux -L "$sock_name" kill-server 2>/dev/null || true
        done
    fi
    # Also check the default server for any stray test sessions (backwards compat)
    local sessions
    sessions=$(tmux list-sessions -F '#{session_name}' 2>/dev/null | grep -E '^octo-code-e2e-' || true)
    if [[ -n "$sessions" ]]; then
        echo "$sessions" | while read -r sess; do tmux kill-session -t "$sess" 2>/dev/null || true; done
    fi
    # Remove stale socket dirs
    local run_dir="/run/user/$(id -u)"
    if [[ -d "$run_dir" ]]; then
        find "$run_dir" -maxdepth 1 -type d -name 'octo-code-e2e-*' -exec rm -rf {} + 2>/dev/null || true
    fi
    # Remove stale instance log files from prior runs
    find "$PROJECT_ROOT" -maxdepth 1 -name 'octo-debug-e2e-*.txt' -exec rm -f {} + 2>/dev/null || true
    find "$PROJECT_ROOT" -maxdepth 1 -name 'octo-error-e2e-*.txt' -exec rm -f {} + 2>/dev/null || true
}

check_orphans() {
    local found=0
    local daemons
    daemons=$(pgrep -fa 'octo-code-daemon.*--session-name octo-code-e2e-' 2>/dev/null || true)
    if [[ -n "$daemons" ]]; then
        echo "[E2E ERROR] Orphaned test daemon processes found:" >&2
        echo "$daemons" >&2
        found=1
    fi
    # Check for orphaned isolated tmux server sockets (only live servers)
    local tmux_dir="/tmp/tmux-$(id -u)"
    if [[ -d "$tmux_dir" ]]; then
        local live_socks=""
        for sock in "$tmux_dir"/octo-code-e2e-*; do
            [[ -e "$sock" ]] || continue
            local sock_name
            sock_name=$(basename "$sock")
            # Only report if the tmux server is actually alive
            if tmux -L "$sock_name" list-sessions &>/dev/null; then
                live_socks="$live_socks$sock"$'\n'
            fi
        done
        if [[ -n "$live_socks" ]]; then
            echo "[E2E ERROR] Orphaned test tmux servers still running:" >&2
            echo "$live_socks" >&2
            found=1
        fi
    fi
    # Also check default server for stray test sessions
    local sessions
    sessions=$(tmux list-sessions -F '#{session_name}' 2>/dev/null | grep -E '^octo-code-e2e-' || true)
    if [[ -n "$sessions" ]]; then
        echo "[E2E ERROR] Orphaned test tmux sessions found:" >&2
        echo "$sessions" >&2
        found=1
    fi
    return $found
}

# Pre-cleanup: catch orphans from prior crashed runs
process_cleanup

# Post-cleanup on EXIT
trap 'process_cleanup; check_orphans || true' EXIT

if [[ $# -eq 0 ]]; then
    cargo test \
        --test e2e_error_handling \
        --test screen_capture \
        --features full --quiet -- --test-threads=2 \
        || { echo "E2E TESTS FAILED"; exit 1; }

    echo "E2E TESTS OK"
else
    cargo test \
        --test e2e_error_handling \
        --test screen_capture \
        --features full "$1" --quiet -- --test-threads=1 \
        || { echo "E2E TEST FAILED: $1"; exit 1; }
    echo "E2E TEST OK: $1"
fi
