#!/bin/bash
# Run tests with minimal output.
# Usage:
#   ./ai-tools/test.sh              — unit tests only (safe, fast)
#   ./ai-tools/test.sh --e2e        — instance E2E tests (no Slack)
#   ./ai-tools/test.sh --all        — unit + instance E2E separately (safe for WSL2)
#   ./ai-tools/test.sh <name>       — single test by name
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

if [[ $# -eq 0 ]]; then
    cargo test-safe || { echo "UNIT TESTS FAILED"; exit 1; }
    echo "UNIT TESTS OK"
elif [[ "$1" == "--e2e" ]]; then
    "$SCRIPT_DIR/test-e2e.sh" || { echo "E2E TESTS FAILED"; exit 1; }
elif [[ "$1" == "--all" ]]; then
    cargo test-safe || { echo "UNIT TESTS FAILED"; exit 1; }
    echo "UNIT TESTS OK"
    "$SCRIPT_DIR/test-e2e.sh" || { echo "E2E TESTS FAILED"; exit 1; }
else
    cargo test "$1" --quiet || { echo "TEST FAILED: $1"; exit 1; }
    echo "TEST OK: $1"
fi
