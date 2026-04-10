# Shared Claude Code Skills & Config

Shared skills and settings for Claude Code, installable across multiple projects via a single command.

## Install

```bash
git clone https://github.com/OASans/octo-skills.git
cd octo-skills
./install.sh
```

## Update

```bash
cd octo-skills
git pull
./install.sh
```

## What's included

### Skills (copied to `~/.claude/skills/`)

| Skill | Description |
|-------|-------------|
| `/coding-guide` | Shared coding guide — source of truth for code quality standards |
| `/review` | Code review with 3 parallel sub-agents (consumes `/coding-guide`) |
| `/plan-refactor` | Analyze codebase, refresh refactoring backlog (consumes `/coding-guide`) |
| `/design` | Feature design spec generator |
| `/push` | Push workflow with pre-flight checklist |
| `/pull` | Pull and sync with remote |
| `/commit-for-batch` | Commit for batch subagents (internal, used by `/yz-batch`) |
| `/yz-batch` | Execute tasks from a tracker file via sequential subagents |
| `/yz-memory` | Two-tier memory system orchestrator (short-term + long-term) |
| `/memory-short-term` | Capture daily learnings to short-term memory |
| `/memory-long-term` | Consolidate short-term into long-term topics |

### Settings (`~/.claude/settings.json`)

- Permissions: Bash, WebFetch, WebSearch
- Hook: sudo command approval gate
- Status line: context window %, rate limits, lines added/removed

## Project-specific skills

These shared skills are available in ALL projects. For project-specific skills, add them to `<project>/.claude/skills/` as usual — they won't conflict.

## Project setup

Each project still needs its own:
- `CLAUDE.md` — project-specific instructions, module map, workflow
- `ai-memory/` — project-specific memory (long-term index, short-term daily files)
- `.claude/settings.json` — project-level overrides (if needed)
