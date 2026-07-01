---
name: octo-memory
description: >
  Check and update the project's two-tier memory: long-term knowledge skills
  plus a local short-term buffer. Use whenever the user wants to remember, note,
  or save a reusable learning ("remember this", "make a note that…", "don't
  forget…", "add this to memory"), after finishing work that surfaced a
  non-obvious gotcha, decision, or pattern worth keeping, and at conversation
  start to check for pending consolidation. For durable project knowledge — not
  personal reminders, one-off file saves, or commit messages.
---

Check and update the project's two-tier memory. Use it when the user wants to remember, note, or save a reusable learning, after finishing work that surfaced a non-obvious gotcha, decision, or pattern worth keeping, or at conversation start to check for pending consolidation.

**Ignore the default Claude Code memory system.** Always use this project's memory instead.

## Memory layout

- **Long-term** — one topic per `.claude/skills/knowledge-<slug>/SKILL.md` (project-level, committed). Descriptions auto-load every session (the index); bodies load on demand. No `index.md`, no CLAUDE.md `@`-import.
- **Short-term** — local capture buffer at `~/.octo-memory/<key>/short_term/<date>/` (`<key>` = repo name from `git remote get-url origin`). Never committed, not loaded into context; read only by `octo-memory-long-term`.
- **Consolidation flag** — `~/.octo-memory/<key>/tracker.md` (`last_processed_date`, per machine).
- **Usage log** — `~/.octo-memory/<key>/usage.log`: one line per knowledge-topic load, appended by a global hook; consolidation folds it into per-topic `usage.md` sidecars (script-owned) as its retention signal.

## Steps

This skill is an orchestrator — it dispatches to the right sub-skill based on what's needed.

**Gate (run first).** Inspect what changed this session (`git diff` + `git diff --cached`, plus any change under discussion):

- **No changes at all** (e.g. a conversation-start consolidation check) → gate doesn't apply; proceed to step 1. Don't let an empty diff trip the skip.
- **Every change is docs/skill-only** — prose docs (README, CHANGELOG, `docs/`, comments) and/or skill files (`skills/**/SKILL.md`, `.claude/skills/**`) — **and** nothing genuinely worth remembering surfaced (a real decision, gotcha, pattern, or preference — judge honestly): report `SKIPPED (docs/skill-only, nothing to remember)` and stop. This keeps memory from over-triggering when invoked directly. Use judgement — a clearly valuable, hard-to-reconstruct learning still gets captured even from a docs/skill-only diff.
- **Otherwise** → proceed to step 1.

1. **Consolidation gate**: Run `bash ~/.claude/skills/octo-memory/consolidation-due.sh`. On **DUE** (exit 1), run `octo-memory-long-term` — promote new short-term into `knowledge-*` skills, sweep stale ones. On **DONE** (exit 0), skip; don't load `octo-memory-long-term`. The cheap check avoids loading the full skill body just to find today's consolidation already ran.
2. **Record new knowledge**: If you learned something reusable during this conversation (non-obvious patterns, gotchas, architectural decisions, debugging insights), run `octo-memory-short-term` to capture it. Capture even when an earlier session probably noted the same thing — independent re-captures are the recurrence signal that long-term promotion runs on. Skip if nothing non-obvious was learned.
3. **Fix stale topics**: If you noticed a `knowledge-*` skill is wrong during your work, fix it inline and capture the correction via `octo-memory-short-term`.
