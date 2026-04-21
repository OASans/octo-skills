#!/bin/bash
# Launch the built OctoEchoUI app. Writes PID to /tmp/octo-echo-pid.
# Usage:
#   ./ai-tools/echo/run.sh                                  — launch normally
#   ./ai-tools/echo/run.sh --test-mode --mock-script <path> — launch with flags
# All arguments are forwarded to the app binary.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/../../octo-echo-ui"

SETTINGS=$(xcodebuild \
    -project "$PROJECT_DIR/octo-echo-ui.xcodeproj" \
    -scheme OctoEchoUI \
    -configuration Debug \
    -destination "platform=macOS" \
    -showBuildSettings 2>&1) || {
    echo "xcodebuild -showBuildSettings failed:"
    echo "$SETTINGS" | tail -40
    exit 1
}

BUILT_PRODUCTS_DIR=$(echo "$SETTINGS" | awk -F' = ' '/ BUILT_PRODUCTS_DIR =/ {print $2; exit}')
if [[ -z "$BUILT_PRODUCTS_DIR" ]]; then
    echo "Could not find BUILT_PRODUCTS_DIR in xcodebuild -showBuildSettings output. Run ai-tools/echo/build.sh first."
    exit 1
fi

APP="$BUILT_PRODUCTS_DIR/OctoEchoUI.app"
BINARY="$APP/Contents/MacOS/OctoEchoUI"

if [[ ! -x "$BINARY" ]]; then
    echo "App binary not found at $BINARY. Run ai-tools/echo/build.sh first."
    exit 1
fi

"$BINARY" "$@" &
PID=$!
echo "$PID" > /tmp/octo-echo-pid
echo "OctoEchoUI launched (PID $PID, args: $*)"
