# OctoSkills

Shared Claude Code skills installed to `~/.claude/skills/` via `install.sh`. Available in ALL projects.

## Skills

| Skill | Type | Description |
|-------|------|-------------|
| `/coding-guide` | Reference | Shared coding guide — source of truth for code quality standards |
| `/review` | Workflow | Code review with 3 parallel sub-agents. Consumes `/coding-guide` |
| `/plan-refactor` | Planning | Analyze codebase, refresh refactoring backlog. Consumes `/coding-guide` |
| `/design` | Planning | Feature design spec generator |
| `/push` | Workflow | Push workflow with pre-flight checklist |
| `/pull` | Workflow | Pull and sync with remote |
| `/commit-for-batch` | Internal | Commit for batch subagents. Consumed by `/yz-batch` |
| `/yz-batch` | Execution | Execute tasks from a tracker file via sequential subagents |
| `/yz-memory` | Memory | Two-tier memory system orchestrator (short-term + long-term) |
| `/memory-short-term` | Memory | Capture daily learnings to short-term memory |
| `/memory-long-term` | Memory | Consolidate short-term into long-term topics |

## Skill Relationships

- `/coding-guide` is a shared reference consumed by `/review` and `/plan-refactor`. When the coding guide changes, both skills pick up the new version automatically.
- `/yz-batch` consumes `/commit-for-batch` internally for committing after each task.
- `/yz-memory` orchestrates `/memory-short-term` and `/memory-long-term`.
- `/plan-refactor` produces tracker files consumed by `/yz-batch`.

## Editing Skills

Edit skills directly in this repo, then run `./install.sh` to deploy. Do not edit copies in `~/.claude/skills/` — they get overwritten on install.
