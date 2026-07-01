#!/usr/bin/env bash
# Stamps today as the last consolidation date for the CURRENT repo.
# Called by octo-memory-long-term Phase 3 (Finalize) so no model writes the
# tracker by hand — the file stays a single `last_processed_date:` line.
#   exit 0 + "STAMPED ..." -> tracker updated
#   exit 2 + "ERROR ..."   -> no 'origin' remote (memory can't be keyed per project)

. "$(dirname "${BASH_SOURCE[0]}")/store-path.sh"   # sets: key, store (exit 2 if no origin)

flag="$store/tracker.md"
today=$(date +%F)
mkdir -p "$store"
printf 'last_processed_date: %s\n' "$today" > "$flag"
echo "STAMPED: last_processed_date=$today for $key"
