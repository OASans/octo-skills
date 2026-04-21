#!/bin/bash
# Remove Xcode DerivedData for octo-echo-ui and all /tmp/octo-echo-* scratch files.
set -euo pipefail

# DerivedData for this project. Xcode uses a hashed suffix so glob it.
DERIVED=~/Library/Developer/Xcode/DerivedData
if [[ -d "$DERIVED" ]]; then
    find "$DERIVED" -maxdepth 1 -type d -name "octo-echo-ui-*" -exec rm -rf {} + 2>/dev/null || true
fi

# /tmp scratch files from test runs / screenshots / pid file.
rm -rf /tmp/octo-echo-last.xcresult
rm -rf /tmp/octo-echo-screenshots
rm -f /tmp/octo-echo-pid
rm -f /tmp/octo-echo-verify-*.png
rm -f /tmp/octo-echo-debug.txt
rm -f /tmp/octo-echo-error.txt

# Project-root log files.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
rm -f "$SCRIPT_DIR/../../echo-debug.txt"
rm -f "$SCRIPT_DIR/../../echo-error.txt"

echo "CLEAN OK"
