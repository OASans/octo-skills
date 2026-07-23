#!/usr/bin/env bash
# Deduplicates a user-started long-term consolidation for the CURRENT repo.
# Run only after a human explicitly invokes /octo-memory-long-term.
#   exit 1 + "DUE ..."   -> continue the manual consolidation
#   exit 0 + "DONE ..."  -> already consolidated today; stop
#   exit 2 + "ERROR ..." -> no 'origin' remote (memory can't be keyed per project)

. "$(dirname "${BASH_SOURCE[0]}")/store-path.sh"   # sets: key, store (exit 2 if no origin)

flag="$store/tracker.md"
last=$(grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' "$flag" 2>/dev/null | head -1)

if [ "$last" = "$(date +%F)" ]; then
  echo "DONE: consolidation already ran today ($last) for $key"
  exit 0
fi
echo "DUE: last consolidated ${last:-never} for $key"
exit 1
