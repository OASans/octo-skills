Batch execution of tasks from a tracker file. Plans all tasks, then executes each via subagent with user review.

Usage: `/batch <path-to-tracker-file>`

## Phase 0: Parse & Setup

1. Read `$ARGUMENTS` as tracker file path. Read the file.
2. Identify incomplete items (unchecked checkboxes `[ ]`, unnumbered tasks, or contextually incomplete entries).
3. `TaskCreate` for each incomplete item. Subject = task summary, description = full context from tracker.
4. Derive `<name>` from tracker filename (strip extension, kebab-case).
5. Create directory `ai-doc/batch/<name>/`.

## Phase 0.5: Merge Tasks (Optional)

Before planning, review all tasks and merge where reasonable:
- Tasks touching the same or nearby files.
- Tasks with similar scope (e.g., multiple "add tests for X" tasks in one module).
- Only merge if the combined task is still appropriate for a single subagent — don't overload one subagent with all heavy tasks.
- Update `TaskCreate` entries accordingly (delete merged tasks, update the surviving task's description to cover all merged work).

## Phase 1: Plan All Tasks

For each task (after merging):

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

**Strictly sequential — one subagent at a time.** Never run multiple subagents in parallel. Concurrent subagents cause file conflicts (simultaneous edits, competing test runs, inconsistent build state). Wait for each subagent to fully complete, get user approval, and commit before starting the next.

1. `TaskUpdate` → `in_progress`.
2. Read this task's plan file (`ai-doc/batch/<name>/plan-<task-id>.md`).
3. Spawn ONE `Task` subagent (`general-purpose`) with the plan content as prompt. Include these instructions for the subagent:
   - Read CLAUDE.md first to learn the project's build/test/lint/fmt workflow.
   - Implement all changes described in the plan.
   - Run the project's standard validation steps (build, test, lint, format) as discovered from CLAUDE.md. Iterate until all checks pass.
   - Do NOT: git commit, interact with user, push, or modify files outside the plan scope.
4. Show `git diff` to user for review.
6. If user approves → stage changed files, commit with the planned commit message, `TaskUpdate` → `completed`.
7. If user rejects → collect feedback, spawn new subagent with plan + user feedback, repeat from step 4.
8. Move to next task.
