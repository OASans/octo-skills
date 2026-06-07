# Global Context

Shared, project-agnostic rules — they apply in every project. A project's own CLAUDE.md extends these with project-specific details (build/test commands, architecture, E2E steps); it never repeats them.

## Most Important Instructions

### Before start
- If the session-start context shows "GIT PULL FAILED", fix the git state before anything else (ask first if resolution could lose commits).
- ALWAYS read `/coding-guide` (or the project's equivalent skills) before planning or coding.

### During dev
- Branch discipline — NEVER create a branch or open a PR; you're the only worker in this checkout, so commit directly on the default branch (`main`/`master`).
- Ownership — you own the whole codebase; any lint/build/test failure is yours to fix. NEVER `git stash`/`diff`/`log` to check if it's pre-existing — dive into the failing code and fix the root cause.
- Regression test — every bug fix MUST ship with a test that would have caught it.

### Anytime
- Input is Whisper STT — expect mistranscriptions (homophones, garbled tech terms); correct from context before acting, ask if ambiguous.
- Messages and plans — compact, plain words, easy to read; include only what's needed, skip preamble and recaps.
- Editing any CLAUDE.md — write compact (no decorative markdown); usually edit only when the user asks.

## Memory

**Ignore the default Claude Code memory system** — it can't be shared across the team and isn't visible or tracked in git. Use the `/octo-memory` skill for all memory operations (it orchestrates `/memory-short-term` capture and `/memory-long-term` consolidation).

- **Long-term** — one topic per `.claude/skills/knowledge-<slug>/SKILL.md`, committed and team-shared. Claude Code auto-loads each skill's description (the index) and loads a body on demand — so there's **no `index.md` and no CLAUDE.md `@`-import**; it just loads.
- **Short-term** — a local buffer at `~/.octo-memory/<repo>/short_term/` (`<repo>` from `git remote get-url origin`), shared across that repo's checkouts on one machine. Never committed, **not loaded into context**; it's only consolidation input, and losing it is fine.
- **Consolidation** — once per day per machine (flag at `~/.octo-memory/<repo>/tracker.md`): `/memory-long-term` promotes valuable short-term into `knowledge-*` skills and prunes stale ones.

## Workflow

A project may have its own workflow — follow it. These are additional steps that MUST be done for every change (project-specific build/test/lint commands and extra gates like E2E live in the project's CLAUDE.md, not here):

1. `git pull` first — start from a clean, synced tree (session-start auto-pull may have done this; confirm).
2. `/review` — once unit tests pass and build/lint are green, run `/review` ONCE per session (repeat review isn't useful), then fix its findings.
3. `/octo-memory` — after `/review` findings are fixed and everything's green, update memory.
