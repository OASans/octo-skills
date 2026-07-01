#!/usr/bin/env bash
# Emits the CURRENT repo's short-term captures as one blob for consolidation,
# in two labelled sections so the agent reads + judges but never re-derives the
# date range by hand:
#   PROMOTE — folders in [last_processed_date, today): the exactly-once promote set.
#   CONTEXT — the ~5 most recent already-processed day-folders (date < watermark):
#             read-only: the recurrence lookback (a PROMOTE entry with a twin here
#             has recurred → promotable) plus context for writing better topics;
#             never promote CONTEXT entries on their own.
#
# Why PROMOTE's bounds are `>= watermark` and `< today`:
#   >= watermark (include the boundary day): a capture written later on a day that
#     already ran lands in that day's folder; `>` would orphan it (the watermark only climbs).
#   <  today     (exclude today's folder): today is still receiving captures; promoting it
#     now, then stamping today, would orphan everything captured later today.
#   Net: each day's folder is promoted exactly once, on the first run after that day.
#
#   exit 0 -> emitted (either section may be empty)
#   exit 2 -> no 'origin' remote (memory can't be keyed per project)

export LC_ALL=C   # deterministic YYYY-MM-DD comparison and sort

. "$(dirname "${BASH_SOURCE[0]}")/store-path.sh"   # sets: key, store (exit 2 if no origin)

st="$store/short_term"
flag="$store/tracker.md"
today=$(date +%F)
wm=$(grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' "$flag" 2>/dev/null | head -1)
wm=${wm:-0000-00-00}   # missing / empty / first run -> epoch (promote all complete days)

emit_dir() {  # $1 = date folder; cat each capture with a provenance header
  for f in "$1"*.md; do
    [ -e "$f" ] || continue
    echo "===== $f ====="
    cat "$f"
    echo
  done
}

# Date-named capture folders (YYYY-MM-DD basenames), ascending. Computed once.
days=$(for d in "$st"/*/; do
  b=$(basename "$d")
  [[ "$b" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] && echo "$b"
done | sort)

echo "## PROMOTE  (captures in [$wm, $today) — classify these: promote / update / hold / skip)"
for day in $days; do
  [[ ! "$day" < "$wm" ]] && [[ "$day" < "$today" ]] && emit_dir "$st/$day/"
done

echo
echo "## CONTEXT  (the ~5 most recent already-processed days, date < $wm — recurrence lookback: a PROMOTE entry with a twin here has recurred; do NOT promote these directly)"
for day in $(echo "$days" | while read -r d; do [ -n "$d" ] && [[ "$d" < "$wm" ]] && echo "$d"; done | tail -5); do
  emit_dir "$st/$day/"
done
