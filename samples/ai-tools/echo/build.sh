#!/bin/bash
# Build OctoEchoUI (Swift/Xcode). Minimal output: errors only on failure.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/../../octo-echo-ui"
PROJECT="$PROJECT_DIR/octo-echo-ui.xcodeproj"

if [[ ! -d "$PROJECT" ]]; then
    echo "octo-echo-ui.xcodeproj not found at $PROJECT"
    echo "Run 'xcodegen generate' from $PROJECT_DIR first."
    exit 1
fi

OUTPUT=$(xcodebuild build \
    -project "$PROJECT" \
    -scheme OctoEchoUI \
    -configuration Debug \
    -destination "platform=macOS" \
    -quiet 2>&1) || {
    FILTERED=$(echo "$OUTPUT" | grep -E "error:|warning:|ld:|Undefined|fatal|xcodebuild:" || true)
    if [[ -n "$FILTERED" ]]; then
        echo "$FILTERED" | head -60
    else
        echo "$OUTPUT" | tail -60
    fi
    echo ""
    echo "BUILD FAILED"
    exit 1
}
echo "BUILD OK"
