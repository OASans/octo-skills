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
| `/octo-coding-guide` | Reference | Shared coding guide — source of truth for code quality standards |
| `/octo-review` | Workflow | Code review; one parallel sub-agent per `/octo-coding-guide` major section. Consumes `/octo-coding-guide` |
| `/octo-commit` | Workflow | Primary commit path: verify the CLAUDE.md workflow was followed, then write a meaningful + compact commit. Never pushes |
| `/octo-memory` | Memory | Two-tier memory system orchestrator (short-term + long-term) |
| `octo-memory-short-term` | Memory (internal) | Append one capture to short-term; invoked by `/octo-memory`, not directly |
| `octo-memory-long-term` | Memory (internal) | Consolidate short-term into long-term topics; invoked by `/octo-memory`, not directly |

## Skill Relationships

- `/octo-coding-guide` is a shared reference consumed by `/octo-review`. When the coding guide changes, `/octo-review` picks up the new version automatically.
- `/octo-review` is **structure-driven by `/octo-coding-guide`**: each `##` major section is one review domain reviewed by one dedicated sub-agent (criteria partitioned, no overlap). Adding a `##` section to the coding guide adds a review agent with no edit to `/octo-review`. Keep `##` sections coherent and their `*Review focus:*` line accurate.
- `/octo-commit` is **structure-driven by CLAUDE.md's `## Workflow`**: it verifies every workflow step (e.g. `/octo-review`, `/octo-memory`) was followed before committing, and stops + hands back if one was skipped. Add a step to the workflow and `/octo-commit` enforces it with no edit here. It is the primary commit path and never pushes.
- `/octo-memory` orchestrates the internal `octo-memory-short-term` and `octo-memory-long-term` sub-skills (`user-invocable: false` — hidden from the slash menu, invoked only by the orchestrator by name).

## Editing Skills

Edit skills in `skills/<name>/SKILL.md`, then run `./install.sh` to deploy. Do not edit copies in `~/.claude/skills/` — they get overwritten on install.
