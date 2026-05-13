#!/usr/bin/env bash
# OctoCode peer messaging helper. Appends events of type `octo_peer_send` to
# `$OCTO_HOOK_FILE` under an exclusive `flock` on `$OCTO_HOOK_FILE.lock`,
# serializing against Claude Code hook writers and the daemon's read+truncate
# poll. These are OctoCode-origin events, distinct from Claude Code's
# `.claude/settings.json` hook system.
set -eu

MAX_MSG_BYTES=4096

escape_json() {
    local s="$1"
    s="${s//\\/\\\\}"      # backslash first
    s="${s//\"/\\\"}"
    s="${s//$'\n'/\\n}"
    s="${s//$'\r'/\\r}"
    s="${s//$'\t'/\\t}"
    printf '%s' "$s"
}

# Returns 0 if `target` is in $OCTO_PEERS; 1 otherwise.
is_peer() {
    local target="$1"
    [ -z "${OCTO_PEERS:-}" ] && return 1
    while IFS=$'\t' read -r name _; do
        [ "$name" = "$target" ] && return 0
    done <<< "$OCTO_PEERS"
    return 1
}

list() {
    if [ -z "${OCTO_PEERS:-}" ]; then
        echo "(no peers configured for this agent)"
    else
        echo "$OCTO_PEERS"
    fi
}

send() {
    local to="${1:-}" msg="${2:-}"
    if [ -z "$to" ] || [ -z "$msg" ]; then
        echo "usage: $0 send <name> <message>" >&2
        return 1
    fi
    if ! is_peer "$to"; then
        echo "error: '$to' is not in your peer list. Available peers:" >&2
        list >&2
        return 1
    fi
    if [ "${#msg}" -gt "$MAX_MSG_BYTES" ]; then
        echo "error: message exceeds ${MAX_MSG_BYTES} byte limit (got ${#msg})" >&2
        return 1
    fi
    local escaped_msg
    escaped_msg=$(escape_json "$msg")
    ( flock -x -w 5 9; printf '{"type":"octo_peer_send","data":{"from":"%s","to":"%s","msg":"%s"}}\n' \
        "$OCTO_AGENT_NAME" "$to" "$escaped_msg" >> "$OCTO_HOOK_FILE" ) 9>"$OCTO_HOOK_FILE.lock"
}

send_with_callback() {
    local to="${1:-}" msg="${2:-}"
    if [ -z "$to" ] || [ -z "$msg" ]; then
        echo "usage: $0 send-with-callback <name> <message>" >&2
        return 1
    fi
    local nl=$'\n'
    local templated="${msg}${nl}${nl}**Please send a peer message back to me with a summary when complete.**"
    send "$to" "$templated"
}

case "${1:-}" in
    list)               shift; list "$@" ;;
    send)               shift; send "$@" ;;
    send-with-callback) shift; send_with_callback "$@" ;;
    *) echo "usage: $0 {list|send <name> <msg>|send-with-callback <name> <msg>}" >&2; exit 1 ;;
esac
