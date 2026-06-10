---
name: octo-memory
description: >
  Check and update the project's two-tier memory: long-term knowledge skills
  plus a local short-term buffer. Use after completing a task, when the user
  asks to remember something, or at conversation start to check for pending
  consolidation.
---

Check and update the project's two-tier memory. Use this skill after completing a task, when the user asks to remember something, or at conversation start to check for pending consolidation.

**Ignore the default Claude Code memory system.** Always use this project's memory instead.

## Memory layout

- **Long-term** — one topic per `.claude/skills/knowledge-<slug>/SKILL.md` (project-level, committed). Descriptions auto-load every session (the index); bodies load on demand. No `index.md`, no CLAUDE.md `@`-import.
- **Short-term** — local capture buffer at `~/.octo-memory/<key>/short_term/<date>/` (`<key>` = repo name from `git remote get-url origin`). Never committed, not loaded into context; read only by `octo-memory-long-term`.
- **Consolidation flag** — `~/.octo-memory/<key>/tracker.md` (`last_processed_date`, per machine).

## Steps

This skill is an orchestrator — it dispatches to the right sub-skill based on what's needed.

**Gate (run first).** Inspect what changed this session (`git diff` + `git diff --cached`, plus any change under discussion):

- **No changes at all** (e.g. a conversation-start consolidation check) → gate does not apply; proceed to step 1 normally. Do **not** let an empty diff trip the skip.
- **There are changes and *every* one is docs/skill-only** — prose documentation (README, CHANGELOG, `docs/`, comments) and/or skill-definition files (`skills/**/SKILL.md`, `.claude/skills/**`) — **and** the conversation surfaced nothing genuinely worth remembering (a real decision, gotcha, pattern, or preference — judge honestly, don't rationalize a reason to write): report `SKIPPED (docs/skill-only, nothing to remember)` and stop — this keeps memory from over-triggering when invoked directly. **Use your own judgement** — a clearly valuable, hard-to-reconstruct learning still gets captured even if the diff is docs/skill-only.
- **Otherwise** → proceed to step 1.

1. **Consolidation gate**: Run `bash ~/.claude/skills/octo-memory/consolidation-due.sh`. On **DUE** (exit 1), run `octo-memory-long-term` — promote new short-term into `knowledge-*` skills, sweep stale ones. On **DONE** (exit 0), skip; don't load `octo-memory-long-term`. The cheap check avoids loading the full skill body just to find today's consolidation already ran.
2. **Record new knowledge**: If you learned something reusable during this conversation (non-obvious patterns, gotchas, architectural decisions, debugging insights), run `octo-memory-short-term` to capture it. Skip if nothing non-obvious was learned.
3. **Fix stale topics**: If you noticed a `knowledge-*` skill is wrong during your work, fix it inline and capture the correction via `octo-memory-short-term`.
