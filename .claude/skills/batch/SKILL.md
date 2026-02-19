---
---

Execute tasks from a pre-approved tracker file via sequential subagents. Fully autonomous — no user review during execution.

Usage: `/batch <path-to-tracker-file>`

## Tracker Contract

The tracker file must have a **Context** section before the backlog. This section is passed verbatim to each subagent as its working instructions — it must contain: what kind of work to do, constraints, build/test/lint commands, project conventions, and any guidance the subagent needs to work autonomously. Plan-* skills produce this section.

## Steps

1. Check `.claude/skills/commit/SKILL.md` and `.claude/skills/review/SKILL.md` exist. If either is missing, tell user which skill(s) are missing: "Batch requires `/commit` and `/review` skills. Create them first." Stop.
2. Read `$ARGUMENTS` as tracker file path. Verify it has a **Context** section. If missing, tell user: "Tracker has no Context section. Use a plan-* skill to generate a proper tracker." Stop.
3. Parse incomplete items (unchecked `[ ]` or contextually incomplete). `TaskCreate` for each item. Merge tasks touching same files or similar scope — delete merged, update survivor.
4. Execute strictly sequentially — one subagent at a time, never parallel. Per task: `TaskUpdate` → `in_progress`, spawn one `general-purpose` subagent with the task description + tracker's **Context** section. Subagent instructions: read CLAUDE.md first, explore codebase and plan thoroughly before writing any code, implement changes, run build/test/lint/fmt until passing, run `/review` once and fix its suggestions, then run `/commit` to commit without asking for user approval. Do NOT interact with user.
5. After subagent completes: `TaskUpdate` → `completed`. Move to next task.
