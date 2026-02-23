---
---

Execute tasks from a pre-approved tracker file via sequential subagents. Fully autonomous — no user review during execution.

Usage: `/batch <path-to-tracker-file>`

## Tracker Contract

The tracker file is organized into sections grouped by principle headers (`###`). Each section has a **Context** block before its items — containing the planning agent's analysis, relevant coding guide points, and suggested approach. Plan-* skills produce this format.

## Steps

1. Check that `/commit-for-batch` and `/review` skills are available in context. If either is missing, tell user which skill(s) are missing: "Batch requires `/commit-for-batch` and `/review` skills. Create them first." Stop.
2. Read `$ARGUMENTS` as tracker file path. Verify it has sections with **Context** blocks. If missing, tell user: "Tracker has no Context sections. Use a plan-* skill to generate a proper tracker." Stop.
3. `TaskCreate` for each item. Merge tasks touching same files or similar scope — delete merged, update survivor.
4. Execute strictly sequentially — one subagent at a time, never parallel. Per task: `TaskUpdate` → `in_progress`, spawn one `general-purpose` subagent with the task description + the **Context** block from the task's section in the tracker file. Subagent instructions: read CLAUDE.md first, use the provided context as your starting point, implement changes, run build/test/lint/fmt until passing, run `/review` once and fix its suggestions, then run `/commit-for-batch` to commit without asking for user approval. Do NOT interact with user.
5. After subagent completes: `TaskUpdate` → `completed`, remove the task entirely from the tracker file. Move to next task.
