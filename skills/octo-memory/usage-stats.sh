#!/usr/bin/env bash
# Usage telemetry for the CURRENT repo's knowledge-* topics.
#
# Data flow: a global PostToolUse(Skill) hook appends "YYYY-MM-DD knowledge-<slug>"
# to ~/.octo-memory/<key>/usage.log on every knowledge-topic load (machine-local,
# shared by all checkouts of the repo). This script joins that log against the
# repo's .claude/skills/knowledge-*/ dirs:
#
#   (default)  read-only: print "<topic> loads=<N> last-loaded=<date|never>" per
#              topic, where N = committed total (usage.md sidecar) + log lines not
#              yet folded. Consolidation Phase 2 reads this for retention judgment.
#   --stamp    fold log lines dated [last_stamped_date, today) into each topic's
#              usage.md sidecar (loads += pending, last-loaded = max), advance the
#              machine-local fold watermark (usage-tracker.md), then trim log lines
#              older than 30 days (already folded; tail kept only for inspection).
#              Run by octo-memory-long-term Phase 3 (Finalize).
#
# Sidecar .claude/skills/knowledge-<slug>/usage.md (script-owned, committed):
#     last-loaded: <YYYY-MM-DD|never>
#     loads: <N>
#   It is rewritten only when its topic was actually loaded — plus a one-time
#   bootstrap (loads: 0, last-loaded: never) when the sidecar doesn't exist yet —
#   so a long-unchanged sidecar IS the disuse evidence. `loads` stays additive
#   across machines through git because the fold watermark is machine-local, and
#   the fold window is the same half-open [watermark, today) bucket rule as
#   collect-captures.sh: each log line is folded exactly once, and today's
#   still-growing bucket never is.
#
# Known limits (fine for a coarse retention signal): loads via the Skill tool are
# counted, direct file Reads are not; a log append racing the --stamp trim can
# lose at most the racing line; a corrupt hand-edited sidecar field resets to
# 0/never rather than aborting the fold.
#
#   exit 0 -> ok (either mode)
#   exit 2 -> no 'origin' remote, or unknown mode

export LC_ALL=C   # deterministic YYYY-MM-DD comparison

mode="${1:-}"
case "$mode" in
  ""|--stamp) ;;
  *) echo "ERROR: unknown mode '$mode' (usage: usage-stats.sh [--stamp])" >&2; exit 2 ;;
esac

. "$(dirname "${BASH_SOURCE[0]}")/store-path.sh"   # sets: key, store (exit 2 if no origin)

log="$store/usage.log"
fold_flag="$store/usage-tracker.md"
today=$(date +%F)
wm=$(grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' "$fold_flag" 2>/dev/null | head -1)
wm=${wm:-0000-00-00}   # first run: fold every complete day

root=$(git rev-parse --show-toplevel 2>/dev/null || echo .)

# pending_for <topic>: "<count> <newest-date>" of log lines for <topic> in
# [wm, today). Dates compare as dash-stripped digits — no locale ambiguity.
pending_for() {
  [ -f "$log" ] || { echo "0 "; return; }
  awk -v t="$1" -v w="${wm//-/}" -v td="${today//-/}" '
    $2==t { d=$1; gsub(/-/,"",d); if (d+0>=w+0 && d+0<td+0) { c++; if ($1>mx) mx=$1 } }
    END { print c+0, mx }
  ' "$log"
}

side_field() { sed -n "s/^$2: //p" "$1" 2>/dev/null | head -1; }

stamped_topics=0; folded_lines=0
for dir in "$root"/.claude/skills/knowledge-*/; do
  [ -d "$dir" ] || continue
  name=$(basename "$dir")
  side="${dir}usage.md"

  # Corrupt hand-edits reset to 0/never; 10# blocks octal surprises like "018".
  loads=$(side_field "$side" loads)
  if [[ "$loads" =~ ^[0-9]+$ ]]; then loads=$((10#$loads)); else loads=0; fi
  last=$(side_field "$side" last-loaded)
  [[ "$last" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || last="never"

  read -r pending newest <<EOF
$(pending_for "$name")
EOF

  total=$((loads + pending))
  last_out="$last"
  if [ -n "$newest" ] && { [ "$last" = "never" ] || [[ "$newest" > "$last" ]]; }; then
    last_out="$newest"
  fi

  if [ "$mode" = "--stamp" ]; then
    if [ "$pending" -gt 0 ] || [ ! -f "$side" ]; then
      printf 'last-loaded: %s\nloads: %s\n' "$last_out" "$total" > "$side"
      stamped_topics=$((stamped_topics + 1)); folded_lines=$((folded_lines + pending))
    fi
  else
    echo "$name loads=$total last-loaded=$last_out"
  fi
done

trim_log() {
  cutoff=$(date -d '30 days ago' +%F 2>/dev/null || date -v-30d +%F 2>/dev/null || echo 0000-00-00)
  awk -v c="${cutoff//-/}" '{ d=$1; gsub(/-/,"",d); if (d+0>=c+0) print }' "$log" > "$log.tmp" && mv "$log.tmp" "$log"
}

if [ "$mode" = "--stamp" ]; then
  mkdir -p "$store"
  printf 'last_stamped_date: %s\n' "$today" > "$fold_flag"
  if [ -f "$log" ]; then
    # flock when available (util-linux; absent on stock macOS — trim unlocked
    # there, same worst case as the hook's unlocked append: one racing line).
    if command -v flock >/dev/null 2>&1; then
      ( flock -x -w 5 9 || exit 0; trim_log ) 9>"$log.lock" 2>/dev/null
    else
      trim_log
    fi
  fi
  echo "STAMPED: $stamped_topics sidecar(s) written, $folded_lines load(s) folded, watermark=$today for $key"
fi
