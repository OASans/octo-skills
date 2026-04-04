---
name: yz-memory
description: >
  Check and update the project's two-tier memory system in ai-memory/. Use
  after completing a task, when the user asks to remember something, or at
  conversation start to check for pending consolidation.
---

Check and update the project's two-tier memory system in ai-memory/. Use this skill after completing a task, when the user asks to remember something, or at conversation start to check for pending consolidation.

**Ignore the default Claude Code memory system.** Always use this project's memory instead.

## Memory layout

- Long-term index (always loaded via CLAUDE.md): `ai-memory/long-term/index.md`
- Long-term topics (read on-demand): `ai-memory/long-term/topics/<slug>.md`
- Short-term daily files: `ai-memory/short-term/YYYY-MM-DD.md`
- Consolidation tracker: `ai-memory/long-term/tracker.md`

## Steps

This skill is an orchestrator — it dispatches to the right sub-skill based on what's needed.

1. **Check consolidation**: Read `ai-memory/long-term/tracker.md`. If `last_processed_date` < today and unprocessed short-term files exist, run `/memory-long-term`.
2. **Record new knowledge**: If you learned something reusable during this conversation (non-obvious patterns, gotchas, architectural decisions, debugging insights), run `/memory-short-term` to capture it. Skip if nothing non-obvious was learned.
3. **Fix stale topics**: If you noticed a long-term topic is wrong during your work, fix it inline and note the correction in today's short-term file.
