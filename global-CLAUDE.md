# Global Context

Shared, project-agnostic rules — they apply in every project. A project's own CLAUDE.md extends these with project-specific details (build/test commands, architecture, E2E steps); it never repeats them.

## Most Important Instructions

### Before start
- If the session-start context shows "GIT PULL FAILED", fix the git state before anything else (ask first if resolution could lose commits).
- ALWAYS read `/octo-coding-guide-code` (or the project's equivalent skills) before planning or coding.

### During dev
- Branch discipline — NEVER create a branch or open a PR; you're the only worker in this checkout, so commit directly on the default branch (`main`/`master`).
- Ownership — you own the whole codebase; any lint/build/test failure is yours to fix. NEVER `git stash`/`diff`/`log` to check if it's pre-existing — dive into the failing code and fix the root cause.
- Regression test — every bug fix MUST ship with a test that would have caught it.

### Anytime
- Input is Whisper STT — expect mistranscriptions (homophones, garbled tech terms); correct from context before acting, ask if ambiguous.
- Messages and plans — compact, plain words, easy to read; include only what's needed, skip preamble and recaps.
- NEVER edit any `CLAUDE.md`/`AGENTS.md` or any skill whose name contains `coding-guide` on your own — they change only when the user asks; write compact (no decorative markdown).

## Subagents

For Codex, include the actual selected model in the sub-agent's visible name: `agent_name [model]` (for example, `doc_review [gpt-5.6-terra]`). When the name field restricts characters, use `agent_name_model` with punctuation replaced by underscores (for example, `doc_review_gpt_5_6_terra`); always put the model in the name itself, not just the description or dispatch message.

Delegate to keep the main context small and to parallelize where work truly splits. Subagents see no conversation history — every dispatch prompt must be self-contained (goal, files, contracts, decisions so far, definition of done). `model` is required on every spawn (a hook denies the start if it's missing) — pick the best model for the task: think about how hard it is and match it (cheaper/faster for mechanical or search work, stronger for reasoning-heavy work). Three modes:

- Read fan-out (parallel) — search, investigation, fresh-eyes verification, distilling long output: detail-heavy work where only the conclusion needs to come back.
- Mechanical write fan-out (parallel) — only fully-specified repeated changes: write the recipe plus one exemplar edit first, agents replicate it over disjoint files, then you build/test and fix the seams. A coupled change is never split in parallel, however big.
- Staged delegation (sequential) — major multi-stage work that would force repeated auto-compaction: stay a thin orchestrator (plan, contracts, decisions list, stage state — read no file bodies yourself), dispatch each stage once it's spec-complete, worker drives its stage to green build/tests and reports back small. Committed code is the handoff between stages, not summaries.

Keep inline: quick lookups, exploratory debugging where the problem isn't understood yet, and design decisions themselves. Skills with their own orchestration (`/octo-review`) already fan out — don't add more inside them.

## Codex Long-Running Work

- Never busy-poll a running process or agent.
- Empty `write_stdin` polls and `functions.wait` calls must use `yield_time_ms >= 180000`; prefer `300000` when intermediate output is unnecessary.
- `wait_agent` should use `timeout_ms: 3600000` unless intermediate results are required.
- When a wait is nested inside `functions.exec`, set the outer `@exec yield_time_ms` at least 30000 ms longer than the longest nested wait.
- Non-empty `write_stdin` calls that send interactive input are exempt.
- Wait tools return early on completion; do not wake merely to report that work is still running.

## Memory

- Use `/octo-memory` for reusable, non-obvious project discoveries and explicit remember requests; use project `knowledge-*` skills for shared long-term knowledge. Ignore Claude Code's default memory system.
- Treat remembered facts as scoped guidance: investigate conflicts with current implementation, tests, or authoritative documentation before applying or correcting them. Preserve explicit user constraints.
- Only a human invoking `/octo-memory-long-term` starts consolidation. Capture, storage, recurrence, and maintenance mechanics belong to the memory skills.

## Workflow

A project may have its own workflow — follow it. These are additional steps that MUST be done for every change (project-specific build/test/lint commands and extra gates like E2E live in the project's CLAUDE.md, not here):

1. `git pull` first — start from a clean, synced tree (session-start auto-pull may have done this; confirm).
2. `/octo-review` — once unit tests pass and build/lint are green, run `/octo-review` ONCE per session (repeat review isn't useful), then fix its findings.
3. When reusable, non-obvious knowledge surfaced or the user asked to remember something, run `/octo-memory` after review findings are fixed and checks are green.
