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

**Gate (run first).** Inspect what changed this session (`git diff` + `git diff --cached`, plus any change under discussion):

- **No changes at all** (e.g. a conversation-start consolidation check) → gate does not apply; proceed to step 1 normally. Do **not** let an empty diff trip the skip.
- **There are changes and *every* one is docs/skill-only** — prose documentation (README, CHANGELOG, `docs/`, comments) and/or skill-definition files (`skills/**/SKILL.md`, `.claude/skills/**`) — **and** the conversation surfaced nothing genuinely worth remembering (a real decision, gotcha, pattern, or preference — judge honestly, don't rationalize a reason to write): report `SKIPPED (docs/skill-only, nothing to remember)` and stop. This mirrors the `/push` Phase 0 gate so memory can't over-trigger when invoked directly. **Use your own judgement** — a clearly valuable, hard-to-reconstruct learning still gets captured even if the diff is docs/skill-only.
- **Otherwise** → proceed to step 1.

1. **Run long-term review**: Always run `/memory-long-term`. It decides internally whether to promote existing short-term entries that aided this session, and whether to run today's consolidation (skipped if already done).
2. **Record new knowledge**: If you learned something reusable during this conversation (non-obvious patterns, gotchas, architectural decisions, debugging insights), run `/memory-short-term` to capture it. Skip if nothing non-obvious was learned.
3. **Fix stale topics**: If you noticed a long-term topic is wrong during your work, fix it inline and note the correction in today's short-term file.
