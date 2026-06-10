#!/usr/bin/env bash
# Tells whether daily long-term consolidation needs to run for the CURRENT repo.
#   exit 1 + "DUE ..."   -> run octo-memory-long-term
#   exit 0 + "DONE ..."  -> already consolidated today; skip
#   exit 2 + "ERROR ..." -> no 'origin' remote (memory can't be keyed per project)
# Cheap on purpose: lets the orchestrator skip loading the heavy octo-memory-long-term
# skill on the ~every session where consolidation already ran today.

url=$(git remote get-url origin 2>/dev/null)
key=${url##*/}; key=${key%.git}
if [ -z "$key" ]; then
  echo "ERROR: no 'origin' remote — set one (git remote add origin <url>) so memory can be keyed per project" >&2
  exit 2
fi

flag="$HOME/.octo-memory/$key/tracker.md"
last=$(grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}' "$flag" 2>/dev/null | head -1)

if [ "$last" = "$(date +%F)" ]; then
  echo "DONE: consolidation already ran today ($last) for $key"
  exit 0
fi
echo "DUE: last consolidated ${last:-never} for $key"
exit 1
