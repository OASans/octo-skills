#!/bin/bash
# Clean build artifacts and stale log files.
# Default: remove old artifacts (>1 day) + stale test logs.
# --full: also runs cargo clean to remove entire target/ dir.
# Requires: cargo install cargo-sweep
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Sweep old build artifacts
if ! command -v cargo-sweep &>/dev/null; then
    echo "cargo-sweep not found. Install: cargo install cargo-sweep"
    exit 1
fi
cargo sweep --time 1 2>&1

# Remove stale instance-specific log files (octo-{debug,error}-*.txt)
# Keeps the default octo-debug.txt and octo-error.txt (no instance suffix)
count=$(find "$PROJECT_ROOT" -maxdepth 1 \( -name 'octo-debug-*.txt' -o -name 'octo-error-*.txt' \) | wc -l)
if [[ "$count" -gt 0 ]]; then
    find "$PROJECT_ROOT" -maxdepth 1 \( -name 'octo-debug-*.txt' -o -name 'octo-error-*.txt' \) -exec rm -f {} +
    echo "Removed $count stale log files"
fi

# Full clean if requested
if [[ "${1:-}" == "--full" ]]; then
    cargo clean 2>&1
    echo "FULL CLEAN OK"
else
    echo "CLEAN OK"
fi
