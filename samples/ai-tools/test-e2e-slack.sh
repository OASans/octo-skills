#!/bin/bash
# Run Slack E2E tests using the mock Slack server (fast, parallel).
# Does NOT hit real Slack API. For real Slack contract tests, use --contract.
# Usage:
#   ./ai-tools/test-e2e-slack.sh            — mock-based Slack E2E tests
#   ./ai-tools/test-e2e-slack.sh <name>     — single test by name filter
#   ./ai-tools/test-e2e-slack.sh --contract — real Slack contract tests (ignored by default)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

slack_cleanup() {
    "$SCRIPT_DIR/slack-cleanup.sh" || true
}

process_cleanup() {
    # Kill orphaned test daemon processes (ws* prefixes used by Slack tests)
    pkill -f 'octo-code-daemon.*--session-name octo-code-ws[0-9]-' 2>/dev/null || true
    # Kill orphaned test tmux servers (each test uses -L <session_name> for isolation)
    local tmux_dir="/tmp/tmux-$(id -u)"
    if [[ -d "$tmux_dir" ]]; then
        for sock in "$tmux_dir"/octo-code-ws*; do
            [[ -e "$sock" ]] || continue
            local sock_name
            sock_name=$(basename "$sock")
            tmux -L "$sock_name" kill-server 2>/dev/null || true
        done
    fi
    # Also check default server for stray test sessions (backwards compat)
    local sessions
    sessions=$(tmux list-sessions -F '#{session_name}' 2>/dev/null | grep -E '^octo-code-ws[0-9]-' || true)
    if [[ -n "$sessions" ]]; then
        echo "$sessions" | while read -r sess; do tmux kill-session -t "$sess" 2>/dev/null || true; done
    fi
    # Remove stale socket dirs
    local run_dir="/run/user/$(id -u)"
    if [[ -d "$run_dir" ]]; then
        find "$run_dir" -maxdepth 1 -type d -name 'octo-code-ws*-*' -exec rm -rf {} + 2>/dev/null || true
    fi
    # Remove stale instance log files from prior runs
    find "$PROJECT_ROOT" -maxdepth 1 -name 'octo-debug-ws*.txt' -exec rm -f {} + 2>/dev/null || true
    find "$PROJECT_ROOT" -maxdepth 1 -name 'octo-error-ws*.txt' -exec rm -f {} + 2>/dev/null || true
}

check_orphans() {
    local found=0
    local daemons
    daemons=$(pgrep -fa 'octo-code-daemon.*--session-name octo-code-ws[0-9]-' 2>/dev/null || true)
    if [[ -n "$daemons" ]]; then
        echo "[E2E ERROR] Orphaned test daemon processes found:" >&2
        echo "$daemons" >&2
        found=1
    fi
    # Check for orphaned isolated tmux server sockets (only live servers)
    local tmux_dir="/tmp/tmux-$(id -u)"
    if [[ -d "$tmux_dir" ]]; then
        local live_socks=""
        for sock in "$tmux_dir"/octo-code-ws*; do
            [[ -e "$sock" ]] || continue
            local sock_name
            sock_name=$(basename "$sock")
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
    sessions=$(tmux list-sessions -F '#{session_name}' 2>/dev/null | grep -E '^octo-code-ws[0-9]-' || true)
    if [[ -n "$sessions" ]]; then
        echo "[E2E ERROR] Orphaned test tmux sessions found:" >&2
        echo "$sessions" >&2
        found=1
    fi
    return $found
}

# Pre-cleanup
process_cleanup
slack_cleanup

# Post-cleanup on EXIT
trap 'process_cleanup; slack_cleanup; check_orphans || true' EXIT

if [[ "${1:-}" == "--contract" ]]; then
    # Run real Slack contract tests (normally ignored)
    slack_cleanup
    cargo test \
        --test slack \
        --features full -- contract --include-ignored --test-threads=1 \
        || { echo "CONTRACT TESTS FAILED (Slack)"; exit 1; }
    echo "CONTRACT TESTS OK (Slack)"
elif [[ $# -eq 0 ]]; then
    # Run mock-based Slack tests (fast, parallel)
    cargo test \
        --test slack \
        --features full -- --test-threads=2 \
        || { echo "E2E TESTS FAILED (Slack)"; exit 1; }
    echo "E2E TESTS OK (Slack)"
else
    cargo test \
        --test slack \
        --features full -- "$1" --test-threads=2 \
        || { echo "E2E TEST FAILED (Slack): $1"; exit 1; }
    echo "E2E TEST OK (Slack): $1"
fi
