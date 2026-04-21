#!/bin/bash
# Find Rust source files exceeding 500 lines.
# Usage:
#   ./ai-tools/large-files.sh
set -euo pipefail

THRESHOLD=500

echo "Rust files over ${THRESHOLD} lines:"
echo ""

find src -name "*.rs" -exec wc -l {} + \
  | sort -rn \
  | awk -v t="$THRESHOLD" '$1 > t && !/total$/ { printf "%5d  %s\n", $1, $2 }'
