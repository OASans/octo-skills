#!/usr/bin/env bash
# octo-ctl.sh — convenience wrapper for OctoCode E2E interaction.
#
# Subcommands:
#   start <instance> [config]       Start a headless instance
#   stop <instance>                 Kill the tmux session
#   snapshot <instance>             Take snapshot (JSON to stdout)
#   cmd <instance> <command>        Send command via --command
#   state <instance>                Shortcut for: cmd <instance> state
#   wait-ready <instance> <count> [timeout]
#                                   Poll snapshot until N agents are ready

set -euo pipefail

BINARY="./target/debug/octo-code"

usage() {
    cat <<'EOF'
Usage: octo-ctl.sh <subcommand> [args...]

Subcommands:
  start <instance> [config]         Start headless (--no-audio)
  stop <instance>                   Kill tmux session octo-code-<instance>
  snapshot <instance>               Capture snapshot JSON to stdout
  cmd <instance> <command>          Send IPC command (select:0, clear, type:text, reload, quit, state)
  state <instance>                  Shortcut for: cmd <instance> state
  wait-ready <instance> <count> [timeout]
                                    Poll until <count> agents detected (default timeout: 30s)
EOF
    exit 1
}

cmd_start() {
    local instance="${1:?missing instance}"
    local config="${2:-}"
    local args=("start" "--instance" "$instance" "--no-audio")
    if [[ -n "$config" ]]; then
        args+=("-c" "$config")
    fi
    "$BINARY" "${args[@]}"
}

cmd_stop() {
    local instance="${1:?missing instance}"
    tmux kill-session -t "octo-code-${instance}" 2>/dev/null || true
}

cmd_snapshot() {
    local instance="${1:?missing instance}"
    "$BINARY" snapshot --instance "$instance"
}

cmd_cmd() {
    local instance="${1:?missing instance}"
    local command="${2:?missing command}"
    "$BINARY" command --instance "$instance" "$command"
}

cmd_state() {
    local instance="${1:?missing instance}"
    cmd_cmd "$instance" "state"
}

cmd_wait_ready() {
    local instance="${1:?missing instance}"
    local count="${2:?missing agent count}"
    local timeout="${3:-30}"
    local elapsed=0

    while (( elapsed < timeout )); do
        local json
        json=$(cmd_snapshot "$instance" 2>/dev/null) || true
        if [[ -n "$json" ]]; then
            local agent_count
            agent_count=$(echo "$json" | jq '.agents | length' 2>/dev/null) || agent_count=0
            if (( agent_count >= count )); then
                return 0
            fi
        fi
        sleep 1
        (( elapsed++ )) || true
    done

    echo "Timeout: expected $count agents after ${timeout}s" >&2
    return 1
}

# -- Main dispatch --
[[ $# -lt 1 ]] && usage

subcmd="$1"
shift

case "$subcmd" in
    start)      cmd_start "$@" ;;
    stop)       cmd_stop "$@" ;;
    snapshot)   cmd_snapshot "$@" ;;
    cmd)        cmd_cmd "$@" ;;
    state)      cmd_state "$@" ;;
    wait-ready) cmd_wait_ready "$@" ;;
    *)          echo "Unknown subcommand: $subcmd" >&2; usage ;;
esac
