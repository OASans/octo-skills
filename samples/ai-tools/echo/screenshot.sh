#!/bin/bash
# Capture a full-screen PNG for visual inspection by Claude.
# Usage: ./ai-tools/echo/screenshot.sh <name>
# Writes to /tmp/octo-echo-verify-<name>-<timestamp>.png and prints the path.
set -euo pipefail

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <name>"
    exit 1
fi

NAME="$1"
if [[ "$NAME" == *"/"* || "$NAME" == *".."* ]]; then
    echo "error: name must not contain '/' or '..'"
    exit 1
fi
TIMESTAMP=$(date +%s)
OUT="/tmp/octo-echo-verify-${NAME}-${TIMESTAMP}.png"

screencapture -o "$OUT" 2>&1 || {
    echo "screencapture denied — grant Screen Recording permission to Terminal in System Settings → Privacy & Security → Screen Recording, then retry."
    exit 1
}

if [[ ! -f "$OUT" ]]; then
    echo "screencapture failed"
    exit 1
fi

echo "$OUT"
