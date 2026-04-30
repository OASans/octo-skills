---
name: yz-memory
description: >
  Check and update the project's two-tier memory system in ai_memory/. Use
  after completing a task, when the user asks to remember something, or at
  conversation start to check for pending consolidation.
---

Check and update the project's two-tier memory system in ai_memory/. Use this skill after completing a task, when the user asks to remember something, or at conversation start to check for pending consolidation.

**Ignore the default Claude Code memory system.** Always use this project's memory instead.

## Memory layout

- Long-term index (always loaded via CLAUDE.md): `ai_memory/long_term/index.md`
- Long-term topics (read on-demand): `ai_memory/long_term/topics/<slug>.md`
- Short-term daily files: `ai_memory/short_term/YYYY-MM-DD.md`
- Consolidation tracker: `ai_memory/long_term/tracker.md`

## Steps

This skill is an orchestrator — it dispatches to the right sub-skill based on what's needed.

1. **Run long-term review**: Always run `/memory-long-term`. It decides internally whether to promote existing short-term entries that aided this session, and whether to run today's consolidation (skipped if already done).
2. **Record new knowledge**: If you learned something reusable during this conversation (non-obvious patterns, gotchas, architectural decisions, debugging insights), run `/memory-short-term` to capture it. Skip if nothing non-obvious was learned.
3. **Fix stale topics**: If you noticed a long-term topic is wrong during your work, fix it inline and note the correction in today's short-term file.
