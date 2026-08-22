---
name: octo-codex-usage
description: >
  Analyze recent local Codex sessions for repeated unusual command patterns that may
  deserve purpose-built tools. Run only when a user explicitly invokes
  `/octo-codex-usage`, optionally with a number of days.
disable-model-invocation: true
---

# Octo Codex Usage

Analyze Codex tool use without exposing prompts, responses, file paths, or raw commands.

## Steps

1. Use seven days unless the user supplied another positive number.
2. Run `bash "${CODEX_HOME:-$HOME/.codex}/skills/octo-codex-usage/scripts/analyze.sh" --days 7`, replacing `7` only when the user supplied another number.
3. Report the analyzer's scope and repeated unusual patterns. Suppress ordinary workflow tools; do not open session files or inspect raw transcript content.
4. Suggest a purpose-built tool only for a pattern recurring across multiple sessions. State when the evidence is too weak.
