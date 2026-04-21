#!/bin/bash
# Test coverage report. Uses cargo-llvm-cov.
# Usage:
#   ./ai-tools/coverage.sh          — per-file summary with uncovered lines
#   ./ai-tools/coverage.sh --html   — HTML report with line highlighting
#   ./ai-tools/coverage.sh --all    — include integration tests
set -euo pipefail

if ! command -v cargo-llvm-cov &>/dev/null; then
    echo "cargo-llvm-cov not found. Install with:"
    echo "  rustup component add llvm-tools-preview"
    echo "  cargo install cargo-llvm-cov"
    exit 1
fi

SCOPE="--lib"
MODE="text"

for arg in "$@"; do
    case "$arg" in
        --html) MODE="html" ;;
        --all)  SCOPE="" ;;
        --help|-h)
            echo "Usage: ./ai-tools/coverage.sh [--html] [--all]"
            exit 0
            ;;
        *) echo "Unknown option: $arg"; exit 1 ;;
    esac
done

if [[ "$MODE" == "html" ]]; then
    # shellcheck disable=SC2086
    cargo llvm-cov --features full $SCOPE --html --output-dir target/coverage 2>/dev/null
    echo "Report: target/coverage/html/index.html"
    exit 0
fi

# Run both formats in one instrumented run using --lcov, then get the text table separately
# shellcheck disable=SC2086
TABLE=$(cargo llvm-cov --features full $SCOPE 2>/dev/null) || {
    echo "COVERAGE FAILED"
    exit 1
}
# shellcheck disable=SC2086
LCOV=$(cargo llvm-cov --features full $SCOPE --lcov 2>/dev/null) || true

# --- Part 1: Coverage table (strip branch columns, color by line coverage %) ---
echo "$TABLE" | sed -n '/^Filename/,$p' | cut -c1-195 | awk '
    BEGIN { RED="\033[31m"; YEL="\033[33m"; GRN="\033[32m"; BOLD="\033[1m"; RST="\033[0m" }
    /^Filename/ || /^-+/ { print BOLD $0 RST; next }
    /^TOTAL/ {
        pct = $10 + 0
        color = (pct >= 80) ? GRN : (pct >= 50) ? YEL : RED
        print BOLD color $0 RST; next
    }
    {
        pct = $10 + 0
        color = (pct >= 80) ? GRN : (pct >= 50) ? YEL : RED
        print color $0 RST
    }
'

# --- Part 2: Uncovered lines per file ---
if [[ -n "$LCOV" ]]; then
    echo ""
    echo -e "\033[1mUncovered lines:\033[0m"
    echo "$LCOV" | awk '
        BEGIN { RED="\033[31m"; YEL="\033[33m"; GRN="\033[32m"; RST="\033[0m" }
        /^SF:/ {
            file = $0; sub(/^SF:.*\/src\//, "", file)
            hit=0; found=0; delete uncov; nuncov=0
            next
        }
        /^DA:/ {
            sub(/^DA:/, ""); split($0, p, ",")
            line = p[1]+0; count = p[2]+0; found++
            if (count > 0) hit++
            else { nuncov++; uncov[nuncov] = line }
            next
        }
        /^end_of_record/ {
            if (found == 0 || nuncov == 0) next
            pct = hit * 100.0 / found
            color = (pct >= 80) ? GRN : (pct >= 50) ? YEL : RED
            # Collapse consecutive lines into ranges
            ranges = ""; start = uncov[1]; prev = uncov[1]
            for (i = 2; i <= nuncov; i++) {
                if (uncov[i] == prev + 1) { prev = uncov[i] }
                else {
                    ranges = ranges (ranges != "" ? "," : "") \
                        (start == prev ? start : start "-" prev)
                    start = uncov[i]; prev = uncov[i]
                }
            }
            ranges = ranges (ranges != "" ? "," : "") \
                (start == prev ? start : start "-" prev)
            printf "%s%s%s: %s\n", color, file, RST, ranges
            next
        }
    '
fi
