#!/bin/bash
# slack-cleanup.sh — Archive all test Slack channels matching a prefix.
# Reads SLACK_BOT_TOKEN and SLACK_TEST_PREFIX from .env.
#
# Usage:
#   ./ai-tools/slack-cleanup.sh             — clean channels matching SLACK_TEST_PREFIX
#   ./ai-tools/slack-cleanup.sh <prefix>    — clean channels matching custom prefix
#
# Exits 0 even if no .env or no token (non-Slack environments shouldn't break).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"

# Load .env (best-effort)
if [[ ! -f "$ENV_FILE" ]]; then
    echo "[slack-cleanup] No .env file — skipping"
    exit 0
fi

BOT_TOKEN=""
TEST_PREFIX=""
while IFS='=' read -r key value; do
    case "$key" in
        SLACK_BOT_TOKEN) BOT_TOKEN="$value" ;;
        SLACK_TEST_PREFIX) TEST_PREFIX="$value" ;;
    esac
done < <(grep -v '^#' "$ENV_FILE" | grep '=' || true)

if [[ -z "$BOT_TOKEN" ]]; then
    echo "[slack-cleanup] No SLACK_BOT_TOKEN in .env — skipping"
    exit 0
fi

# Use argument as prefix override, else fall back to SLACK_TEST_PREFIX
PREFIX="${1:-$TEST_PREFIX}"
if [[ -z "$PREFIX" ]]; then
    echo "[slack-cleanup] No prefix specified and no SLACK_TEST_PREFIX in .env — skipping"
    exit 0
fi

echo "[slack-cleanup] Cleaning channels matching prefix '$PREFIX' (+ legacy patterns)..."

# Paginated fetch of all active (non-archived) channels into a temp file
CHANNELS_FILE=$(mktemp)
trap "rm -f '$CHANNELS_FILE'" EXIT

echo "[]" > "$CHANNELS_FILE"
cursor=""
while true; do
    url="https://slack.com/api/conversations.list?types=public_channel&exclude_archived=true&limit=200"
    if [[ -n "$cursor" ]]; then
        url="$url&cursor=$cursor"
    fi
    resp=$(curl -s -H "Authorization: Bearer $BOT_TOKEN" "$url")
    # Extract channels and next_cursor, append to accumulator
    result=$(RESP="$resp" python3 -c "
import json, os, sys
resp = json.loads(os.environ['RESP'])
if not resp.get('ok'):
    print('ERROR', file=sys.stderr)
    json.dump({'channels': [], 'cursor': ''}, sys.stdout)
else:
    acc = json.load(open('$CHANNELS_FILE'))
    acc.extend(resp.get('channels', []))
    with open('$CHANNELS_FILE', 'w') as f:
        json.dump(acc, f)
    cursor = resp.get('response_metadata', {}).get('next_cursor', '')
    print(cursor)
" 2>/dev/null) || true
    cursor="$result"
    if [[ -z "$cursor" ]]; then
        break
    fi
done

# Filter channels matching our prefix or legacy patterns
# PREFIX passed via env var to avoid shell injection in Python snippet
matching=$(CLEANUP_PREFIX="$PREFIX" python3 -c "
import json, os
channels = json.load(open('$CHANNELS_FILE'))
prefix = os.environ['CLEANUP_PREFIX']
matches = []
for ch in channels:
    name = ch.get('name', '')
    # Match: {prefix}- (e.g. ws1-...) or {prefix}-- (instance prefix)
    if name.startswith(prefix + '-') or name.startswith(prefix + '--'):
        matches.append((ch['id'], name))
    # Legacy: e2e-test-- (old e2e-verify instance prefix)
    elif name.startswith('e2e-test--'):
        matches.append((ch['id'], name))
    # Legacy: octo-code-control-{anything} (old control channel pattern for non-default instances)
    # TODO: Remove after all instances have been restarted with the new naming convention
    elif name.startswith('octo-code-control-'):
        matches.append((ch['id'], name))
for ch_id, name in matches:
    print(f'{ch_id} {name}')
" 2>/dev/null)

if [[ -z "$matching" ]]; then
    echo "[slack-cleanup] No matching channels found"
    exit 0
fi

count=0
ts=$(date +%s)
while IFS=' ' read -r ch_id ch_name; do
    deprecated="deprecated-${ts}-${ch_name}"
    # Truncate to 80 chars (Slack limit)
    if [[ ${#deprecated} -gt 80 ]]; then
        deprecated="${deprecated:0:80}"
        # Trim trailing hyphens
        deprecated="${deprecated%-}"
    fi
    # Join first to ensure membership (required for rename + archive)
    curl -s -H "Authorization: Bearer $BOT_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"channel\":\"$ch_id\"}" \
        "https://slack.com/api/conversations.join" > /dev/null 2>&1 || true
    # Rename to free the original name
    curl -s -H "Authorization: Bearer $BOT_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"channel\":\"$ch_id\",\"name\":\"$deprecated\"}" \
        "https://slack.com/api/conversations.rename" > /dev/null 2>&1 || true
    # Archive the renamed channel
    curl -s -H "Authorization: Bearer $BOT_TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"channel\":\"$ch_id\"}" \
        "https://slack.com/api/conversations.archive" > /dev/null 2>&1 || true
    echo "  Archived: $ch_name"
    count=$((count + 1))
    ts=$((ts + 1))
    # Pace API calls to avoid Slack rate limits (Tier 2: ~20 req/min).
    # Each channel uses 3 calls (join + rename + archive), so 2s between
    # channels keeps us well under the limit even after heavy E2E runs.
    sleep 2
done <<< "$matching"

echo "[slack-cleanup] Archived $count channel(s)"
