#!/bin/bash
# Auto-fix formatting + run clippy lint. Minimal output: only warnings/errors shown.
# Usage:
#   ./ai-tools/style.sh
set -euo pipefail

# Step 1: Format
cargo fmt 2>&1 || { echo "FMT FAILED"; exit 1; }
echo "FMT OK"

# Step 2: Lint
OUTPUT=$(cargo clippy --all-features --quiet -- -D warnings 2>&1) || {
    echo "$OUTPUT" | grep -E "^(warning|error)" | head -30
    echo ""
    echo "LINT FAILED"
    exit 1
}
echo "LINT OK"

# Step 3: Forbid fully-qualified `tracing::{info,warn,error,debug,trace}!` —
# use the bare macro form (with `use tracing::...;`) instead.
if grep -rn --include='*.rs' -E 'tracing::(info|warn|error|debug|trace)!' src/ >&2; then
    echo "" >&2
    echo "CONVENTION FAILED: use bare info!/warn!/error!/debug!/trace! (add \`use tracing::{...};\`)" >&2
    exit 1
fi
echo "CONVENTION OK"
