#!/bin/bash
# Kill all stale Claude Code processes.
# Safe to run when no Claude Code session is actively needed.

pids=$(pgrep -x claude)

if [ -z "$pids" ]; then
    echo "No claude processes found."
    exit 0
fi

echo "Found claude processes:"
ps -p "$pids" -o pid,ppid,lstart,etime,%cpu,%mem,cmd --no-headers
echo ""

read -p "Kill all? [y/N] " confirm
if [[ "$confirm" =~ ^[Yy]$ ]]; then
    kill $pids 2>/dev/null
    sleep 2
    # Force kill any that survived
    remaining=$(pgrep -x claude)
    if [ -n "$remaining" ]; then
        echo "Force killing remaining: $remaining"
        kill -9 $remaining 2>/dev/null
    fi
    echo "Done."
else
    echo "Aborted."
fi
