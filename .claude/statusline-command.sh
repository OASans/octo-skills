#!/usr/bin/env bash
# Claude Code status line script

input=$(cat)

# Context window fields
used_pct=$(echo "$input" | jq -r '.context_window.used_percentage // 0')
ctx_size=$(echo "$input" | jq -r '.context_window.context_window_size // 0')

# Code change stats
lines_added=$(echo "$input" | jq -r '.cost.total_lines_added // 0')
lines_removed=$(echo "$input" | jq -r '.cost.total_lines_removed // 0')

# Format context window size as K (e.g. 200000 -> 200k)
if [ "$ctx_size" -ge 1000 ] 2>/dev/null; then
  ctx_size_fmt="$((ctx_size / 1000))k"
else
  ctx_size_fmt="$ctx_size"
fi

# ANSI colors
RESET="\033[0m"
BOLD="\033[1m"
DIM="\033[2m"
CYAN="\033[36m"
YELLOW="\033[33m"
GREEN="\033[32m"
RED="\033[31m"

# Color context usage: cyan < 50%, yellow 50-79%, red >= 80%
if [ "$(echo "$used_pct >= 80" | bc -l 2>/dev/null)" = "1" ]; then
  ctx_color="$RED"
elif [ "$(echo "$used_pct >= 50" | bc -l 2>/dev/null)" = "1" ]; then
  ctx_color="$YELLOW"
else
  ctx_color="$CYAN"
fi

printf "${DIM}ctx:${RESET} ${ctx_color}${BOLD}${used_pct}%%${RESET}${DIM}/${ctx_size_fmt}${RESET}  ${DIM}+${RESET}${GREEN}${lines_added}${RESET}${DIM}/-${RESET}${RED}${lines_removed}${RESET}"
