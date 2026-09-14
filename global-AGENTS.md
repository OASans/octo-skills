# Global Context

Shared, project-agnostic rules — they apply in every project. A project's own AGENTS.md extends these with project-specific details (build/test commands, architecture, E2E steps); it never repeats them.

## Most Important Instructions

### Before start
- If the session-start context shows "GIT PULL FAILED", fix the git state before anything else (ask first if resolution could lose commits).
- Read the applicable coding guides before changing source/config or planning implementation; use the documentation guide for prose changes. Load other references only when the task needs them.

### During dev
- Branch discipline — NEVER create a branch or open a PR; you're the only worker in this checkout, so commit directly on the default branch (`main`/`master`).
- Ownership — investigate failing checks and fix their root causes within the authorized scope. If an unrelated failure requires a separate behavior change, report the concrete blocker and finish independent work; never dismiss a failure merely as pre-existing or stash user edits.
- Regression test — every bug fix MUST ship with a test that would have caught it, except shell scripts. Never add regression tests for shell scripts.

### Anytime
- Input is Whisper STT — expect mistranscriptions (homophones, garbled tech terms); correct from context before acting, ask if ambiguous.
- Messages and plans — compact, plain words, easy to read; include only what's needed, skip preamble and recaps.
- NEVER edit any `AGENTS.md` or any skill whose name contains `coding-guide` on your own — they change only when the user asks; write compact (no decorative markdown).
- Completion — carry authorized work through implementation, relevant checks, and required workflow steps; resolve routine choices without another approval. Ask only for missing decisions or permissions that materially affect the result, and finish independent authorized work while waiting.
- Instruction conflicts — current explicit user instructions take precedence over skill guidelines within the host's permissions. If a rule blocks completion, cite the exact file and rule and explain the unresolved decision; do not invent an approval requirement.

## Subagents

Include the actual selected model in the sub-agent's visible name: `agent_name [model]` (for example, `doc_review [gpt-5.6-terra]`). When the name field restricts characters, use `agent_name_model` with punctuation replaced by underscores (for example, `doc_review_gpt_5_6_terra`); always put the model in the name itself, not just the description or dispatch message.

Delegate when independent work can save time or improve quality; keep quick lookups and coupled design decisions inline. Every dispatch must be self-contained (goal, files, contracts, decisions, definition of done), select an available model explicitly, and use no history inheritance where supported.

Use models appropriate to the task, including GPT-6 Astra and GPT-5.6 Sol on Codex; shared skills must work with both. Three modes:

- Read fan-out (parallel) — search, investigation, fresh-eyes verification, distilling long output: detail-heavy work where only the conclusion needs to come back.
- Mechanical write fan-out (parallel) — only fully-specified repeated changes: write the recipe plus one exemplar edit first, agents replicate it over disjoint files, then you build/test and fix the seams. A coupled change is never split in parallel, however big.
- Staged delegation (sequential) — major multi-stage work that would force repeated auto-compaction: stay a thin orchestrator (plan, contracts, decisions list, stage state — read no file bodies yourself), dispatch each stage once it's spec-complete, worker drives its stage to green build/tests and reports back small. Committed code is the handoff between stages, not summaries.

Keep inline: quick lookups, exploratory debugging where the problem isn't understood yet, and design decisions themselves. Skills with their own orchestration (`/octo-review`) already fan out — don't add more inside them.

## Codex Long-Running Work

- Never busy-poll a running process or agent.
- Use event-driven or bounded waits supported by the current tool, respecting its limits and the host's progress-update requirements. When nesting a wait, allow the outer call enough time or use its supported yield/resume mechanism.
- Wait tools return early on completion; do not wake merely to report that work is still running.

## Memory

- Use `/octo-memory` for reusable, non-obvious project discoveries and explicit remember requests; use project `knowledge-*` skills for shared long-term knowledge.
- Treat remembered facts as scoped guidance: investigate conflicts with current implementation, tests, or authoritative documentation before applying or correcting them. Preserve explicit user constraints.
- Only a human invoking `/octo-memory-long-term` starts consolidation. Capture, storage, recurrence, and maintenance mechanics belong to the memory skills.

## Workflow

A project may have its own workflow — follow it. These are additional steps that MUST be done for every change (project-specific build/test/lint commands and extra gates like E2E live in the project's AGENTS.md, not here):

1. `git pull` first — start from a clean, synced tree (session-start auto-pull may have done this; confirm).
2. Run the checks appropriate to the change and all required project gates, fixing failures before proceeding. Rerun affected checks after fixes; broaden or repeat checks only for changed behavior, failures, or unresolved concerns.
3. `/octo-review` — after checks are green, review the completed change ONCE per session, then fix its findings and rerun affected checks. The once-per-session rule also applies after review fixes or later edits; inspect later deltas directly instead of spawning another review.
4. When reusable, non-obvious knowledge surfaced or the user asked to remember something, run `/octo-memory` after review findings are fixed and checks are green.
