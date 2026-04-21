#!/bin/bash
# Project analytics: Rust file count, total LOC, git commits, avg LOC/file.
# Usage:
#   ./ai-tools/project-analytics.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

file_count=$(find src -name '*.rs' -type f | wc -l)
total_lines=$(find src -name '*.rs' -type f -exec cat {} + | wc -l)
commit_count=$(git rev-list --count HEAD)

if [[ "$file_count" -gt 0 ]]; then
    avg_lines=$(awk -v t="$total_lines" -v f="$file_count" 'BEGIN { printf "%.1f", t / f }')
else
    avg_lines="0.0"
fi

printf "Rust files:       %s\n" "$file_count"
printf "Total lines:      %s\n" "$total_lines"
printf "Git commits:      %s\n" "$commit_count"
printf "Avg lines/file:   %s\n" "$avg_lines"
