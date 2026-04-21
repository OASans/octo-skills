#!/bin/bash
# Run OctoEchoUI XCUITests. Minimal output: pass/fail summary + failing tests.
# Usage:
#   ./ai-tools/echo/test.sh                                 — run all tests
#   ./ai-tools/echo/test.sh OctoEchoUITests/LaunchTests     — run a specific test / class
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$SCRIPT_DIR/../../octo-echo-ui"
PROJECT="$PROJECT_DIR/octo-echo-ui.xcodeproj"
RESULT_BUNDLE="/tmp/octo-echo-last.xcresult"

rm -rf "$RESULT_BUNDLE"

CMD=(
    xcodebuild test
    -project "$PROJECT"
    -scheme OctoEchoUI
    -destination "platform=macOS"
    -resultBundlePath "$RESULT_BUNDLE"
    -quiet
)

if [[ $# -gt 0 ]]; then
    CMD+=(-only-testing:"$1")
    LABEL="$1"
else
    LABEL="all"
fi

OUTPUT=$("${CMD[@]}" 2>&1) || {
    FILTERED=$(echo "$OUTPUT" | grep -E "error:|Testing failed|Failing tests:|XCTAssert|\*\* TEST FAILED \*\*|ld:|fatal" || true)
    if [[ -n "$FILTERED" ]]; then
        echo "$FILTERED" | head -80
    else
        echo "$OUTPUT" | tail -80
    fi
    echo ""
    echo "TESTS FAILED ($LABEL). Result bundle: $RESULT_BUNDLE"
    exit 1
}
echo "TESTS OK ($LABEL)"
echo "Result bundle: $RESULT_BUNDLE"
