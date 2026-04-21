#!/bin/bash
# Extract XCUITest attachments (screenshots) from an xcresult bundle.
# Usage:
#   ./ai-tools/echo/extract-screenshots.sh                        — uses /tmp/octo-echo-last.xcresult
#   ./ai-tools/echo/extract-screenshots.sh <path-to-xcresult>     — uses given bundle
# Output directory: /tmp/octo-echo-screenshots/
set -euo pipefail

XCRESULT="${1:-/tmp/octo-echo-last.xcresult}"
OUT_DIR="/tmp/octo-echo-screenshots"

if [[ ! -d "$XCRESULT" ]]; then
    echo "xcresult bundle not found: $XCRESULT"
    exit 1
fi

rm -rf "$OUT_DIR"
mkdir -p "$OUT_DIR"

xcrun xcresulttool export attachments \
    --path "$XCRESULT" \
    --output-path "$OUT_DIR" \
    >/dev/null 2>&1 || {
    echo "xcresulttool export attachments failed for $XCRESULT"
    exit 1
}

COUNT=$(find "$OUT_DIR" -type f \( -name "*.png" -o -name "*.jpg" -o -name "*.heic" \) 2>/dev/null | wc -l | tr -d ' ')
echo "Extracted $COUNT screenshots to $OUT_DIR"
