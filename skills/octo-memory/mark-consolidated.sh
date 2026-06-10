#!/usr/bin/env bash
# Stamps today as the last consolidation date for the CURRENT repo.
# Called by octo-memory-long-term Phase 3 (Finalize) so no model writes the
# tracker by hand — the file stays a single `last_processed_date:` line.
#   exit 0 + "STAMPED ..." -> tracker updated
#   exit 2 + "ERROR ..."   -> no 'origin' remote (memory can't be keyed per project)

url=$(git remote get-url origin 2>/dev/null)
key=${url##*/}; key=${key%.git}
if [ -z "$key" ]; then
  echo "ERROR: no 'origin' remote — set one (git remote add origin <url>) so memory can be keyed per project" >&2
  exit 2
fi

flag="$HOME/.octo-memory/$key/tracker.md"
today=$(date +%F)
mkdir -p "$(dirname "$flag")"
printf 'last_processed_date: %s\n' "$today" > "$flag"
echo "STAMPED: last_processed_date=$today for $key"
