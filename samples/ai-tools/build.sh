#!/bin/bash
# Build all binaries: per-binary minimal features (catches dead-code warnings
# that only appear in release builds), then full features for dev.
# Minimal output: only errors shown.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../scripts/binary-features.sh"

# Per-binary minimal features — same as release builds
OUTPUT=$(build_release_binaries 2>&1) || {
    echo "$OUTPUT" | grep -E "^error" | head -30
    echo ""
    echo "BUILD FAILED (per-binary minimal features)"
    exit 1
}

# Full features — the main dev build
OUTPUT=$(cargo dev 2>&1) || {
    echo "$OUTPUT" | grep -E "^error" | head -30
    echo ""
    echo "BUILD FAILED (full features)"
    exit 1
}
echo "BUILD OK"
