Batch execution of tasks from a tracker file. Plans all tasks, then executes each via subagent with user review.

Usage: `/batch <path-to-tracker-file>`

## Phase 0: Parse & Setup

1. Read `$ARGUMENTS` as tracker file path. Read the file.
2. Identify incomplete items (unchecked checkboxes `[ ]`, unnumbered tasks, or contextually incomplete entries).
3. `TaskCreate` for each incomplete item. Subject = task summary, description = full context from tracker.
4. Derive `<name>` from tracker filename (strip extension, kebab-case).
5. Create directory `ai-doc/batch/<name>/`.

## Phase 1: Plan All Tasks

For each task:

1. Read source files referenced by the task. Explore codebase for context via Glob/Grep/Read.
2. Write a self-contained plan to `ai-doc/batch/<name>/plan-<task-id>.md`. Plan must include:
   - Goal: what this task accomplishes.
   - Files to read: exact paths for context.
   - Files to modify/create: exact paths.
   - Implementation steps: numbered, specific, one action each.
   - Tests: what to add or verify.
   - Commit message: conventional commit format per CLAUDE.md.
3. Plan must be detailed enough for a zero-context subagent to execute directly without asking questions.

After all plans are written, show the user a summary of all plans. Wait for approval before proceeding to Phase 2. If user requests changes, revise affected plans and re-present.

## Phase 2: Execute Loop

Process one task at a time, in order:

1. `TaskUpdate` → `in_progress`.
2. Read this task's plan file (`ai-doc/batch/<name>/plan-<task-id>.md`).
3. Spawn ONE `Task` subagent (`general-purpose`) with the plan content as prompt. Include these instructions for the subagent:
   - Implement all changes described in the plan.
   - Validate: `cargo dev`, `cargo test-safe`, `cargo clippy --all-features --quiet -- -D warnings`, `cargo fmt --check`.
   - Iterate until all checks pass.
   - Do NOT: git commit, interact with user, push, or modify files outside the plan scope.
4. After subagent completes, run a sanity check: `cargo dev` and `cargo test-safe`.
5. Show `git diff` to user for review.
6. If user approves → stage changed files, commit with the planned commit message, `TaskUpdate` → `completed`.
7. If user rejects → collect feedback, spawn new subagent with plan + user feedback, repeat from step 4.
8. Move to next task.
