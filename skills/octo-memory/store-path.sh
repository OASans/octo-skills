# store-path.sh — shared resolver for the per-repo memory store. Sourced (not
# executed) by the octo-memory scripts; each script still resolves its own paths
# at run time — this just keeps the resolution in one place.
# Sets: key (repo name from the 'origin' remote), store (~/.octo-memory/<key>).
# Exits the sourcing script with 2 when there is no 'origin' remote.

url=$(git remote get-url origin 2>/dev/null)
key=${url##*/}; key=${key%.git}
if [ -z "$key" ]; then
  echo "ERROR: no 'origin' remote — set one (git remote add origin <url>) so memory can be keyed per project" >&2
  exit 2
fi
store="$HOME/.octo-memory/$key"
