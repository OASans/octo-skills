---
---

Take a rough idea or pain point and autonomously research, plan, and fix it. Minimum user input, maximum agent initiative.

Usage: `/draft <rough idea>`

## Principles

- User gives minimum words. Agent does maximum work.
- Research thoroughly before asking questions. Only ask if truly blocked.
- Wrong direction is OK — user will correct. Bias toward action.

## Steps

1. Read `$ARGUMENTS` as the user's rough idea.
2. Read CLAUDE.md. Understand project structure, conventions, relevant docs.
3. Spawn 2-3 Explore `Task` subagents in parallel to research the codebase: find code related to the pain point, understand current behavior, identify relevant files and modules. Give each agent a different search angle.
4. Synthesize findings. Map user's pain point to specific code, behavior, or limitation. Identify root cause and affected files.
5. If the idea is still ambiguous after research, ask the user 1-2 focused questions. Otherwise skip to step 6.
6. Write a concise plan: what changes, which files, why. Present to user for approval.
