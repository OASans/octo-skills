#!/bin/bash
# Terminate any running OctoEchoUI instance.
set -euo pipefail

PID_FILE="/tmp/octo-echo-pid"

if [[ -f "$PID_FILE" ]]; then
    PID=$(cat "$PID_FILE")
    # Identity check — only kill if PID still belongs to OctoEchoUI (defends against PID reuse)
    if [[ -n "$PID" ]] && ps -p "$PID" -o comm= 2>/dev/null | grep -q "OctoEchoUI"; then
        if kill "$PID" 2>/dev/null; then
            echo "Killed tracked OctoEchoUI PID $PID"
        fi
    fi
    rm -f "$PID_FILE"
fi

# Belt-and-braces: kill any stray OctoEchoUI process.
if pkill -x OctoEchoUI 2>/dev/null; then
    echo "Killed stray OctoEchoUI process(es)"
fi

echo "KILL OK"
