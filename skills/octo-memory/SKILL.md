---
name: octo-memory
description: >
  Capture durable project knowledge in a local short-term buffer. Use for
  "remember this" requests and after work surfaces a reusable gotcha, decision,
  or pattern. Never run long-term consolidation; only a user invoking
  /octo-memory-long-term may do that.
---

Capture reusable project knowledge in the short-term memory buffer. Never initiate long-term consolidation.

**Ignore the default Claude Code memory system.** Always use this project's memory instead.

## Memory layout

- **Long-term** — one topic per `.claude/skills/knowledge-<slug>/SKILL.md` (project-level, committed). Descriptions auto-load every session (the index); bodies load on demand. No `index.md`, no CLAUDE.md `@`-import.
- **Short-term** — local capture buffer at `~/.octo-memory/<key>/short_term/<date>/` (`<key>` = repo name from `git remote get-url origin`). Never committed, not loaded into context; read only by `octo-memory-long-term`.
- **Consolidation flag** — `~/.octo-memory/<key>/tracker.md` (`last_processed_date`, per machine), used only by the manually invoked `/octo-memory-long-term`.
- **Usage log** — `~/.octo-memory/<key>/usage.log`: one line per knowledge-topic load, appended by a global hook; consolidation folds it into per-topic `usage.md` sidecars (script-owned) as its retention signal.

## Steps

This skill gates and dispatches short-term capture only.

**Gate (run first).** Inspect what changed this session (`git diff` + `git diff --cached`, plus any change under discussion):

- **No changes and no reusable learning or explicit memory request** → report `SKIPPED (nothing to remember)` and stop.
- **Every change is docs/skill-only** — prose docs (README, CHANGELOG, `docs/`, comments) and/or skill files (`skills/**/SKILL.md`, `.claude/skills/**`) — **and** nothing genuinely worth remembering surfaced (a real decision, gotcha, pattern, or preference — judge honestly): report `SKIPPED (docs/skill-only, nothing to remember)` and stop. This keeps memory from over-triggering when invoked directly. Use judgement — a clearly valuable, hard-to-reconstruct learning still gets captured even from a docs/skill-only diff.
- **Otherwise** → proceed to step 1.

1. **Record new knowledge**: If you learned something reusable during this conversation (non-obvious patterns, gotchas, architectural decisions, debugging insights), run `octo-memory-short-term` to capture it. Capture even when an earlier session probably noted the same thing — independent re-captures are the recurrence signal that long-term promotion runs on. Skip if nothing non-obvious was learned.
2. **Fix stale topics**: If you noticed a `knowledge-*` skill is wrong during your work, fix it inline and capture the correction via `octo-memory-short-term`.

**Consolidation boundary:** Never run `consolidation-due.sh`, `collect-captures.sh`, `usage-stats.sh --stamp`, `mark-consolidated.sh`, or `octo-memory-long-term`. A human starts consolidation explicitly with `/octo-memory-long-term`.
