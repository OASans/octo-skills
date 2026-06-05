# OctoSkills

Shared Claude Code skills, available in ALL projects once installed.

## Repo layout

- `skills/<name>/SKILL.md` — one directory per skill. This is the source of truth.
- `global-settings.json` — shared Claude Code settings (env vars, permissions, hooks). Installs to `~/.claude/settings.json`.
- `global-CLAUDE.md` — shared user-level memory (global rules applied in every project). Installs to `~/.claude/CLAUDE.md`. Edit this file, not the installed copy.
- `install.sh` — copies `skills/*` to `~/.claude/skills/`, and always overwrites `~/.claude/settings.json` from `global-settings.json` and `~/.claude/CLAUDE.md` from `global-CLAUDE.md`. Run after any edit.

## Skills

| Skill | Type | Description |
|-------|------|-------------|
| `/coding-guide` | Reference | Shared coding guide — source of truth for code quality standards |
| `/review` | Workflow | Code review; one parallel sub-agent per `/coding-guide` major section. Consumes `/coding-guide` |
| `/plan-refactor` | Planning | Analyze codebase, refresh refactoring backlog. Consumes `/coding-guide` |
| `/push` | Workflow | Push workflow with pre-flight checklist |
| `/pull` | Workflow | Pull and sync with remote |
| `/commit-for-batch` | Internal | Commit for batch subagents. Consumed by `/yz-batch` |
| `/yz-batch` | Execution | Execute tasks from a tracker file via sequential subagents |
| `/yz-memory` | Memory | Two-tier memory system orchestrator (short-term + long-term) |
| `/memory-short-term` | Memory | Capture daily learnings to short-term memory |
| `/memory-long-term` | Memory | Consolidate short-term into long-term topics |
| `/octo-share-image` | Integration | Share an image to the OctoCode Slack channel via media bridge |

## Skill Relationships

- `/coding-guide` is a shared reference consumed by `/review` and `/plan-refactor`. When the coding guide changes, both skills pick up the new version automatically.
- `/review` is **structure-driven by `/coding-guide`**: each `##` major section is one review domain reviewed by one dedicated sub-agent (criteria partitioned, no overlap). Adding a `##` section to the coding guide adds a review agent with no edit to `/review`. Keep `##` sections coherent and their `*Review focus:*` line accurate.
- `/yz-batch` consumes `/commit-for-batch` internally for committing after each task.
- `/yz-memory` orchestrates `/memory-short-term` and `/memory-long-term`.
- `/plan-refactor` produces tracker files consumed by `/yz-batch`.

## Editing Skills

Edit skills in `skills/<name>/SKILL.md`, then run `./install.sh` to deploy. Do not edit copies in `~/.claude/skills/` — they get overwritten on install.
