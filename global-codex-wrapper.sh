#!/usr/bin/env bash
set -euo pipefail

exec node "$(npm root -g)/@openai/codex/bin/codex.js" --dangerously-bypass-hook-trust "$@"
