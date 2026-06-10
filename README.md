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
| `/octo-coding-guide` | Shared coding guide — source of truth for code quality standards |
| `/octo-review` | Code review with 3 parallel sub-agents (consumes `/octo-coding-guide`) |
| `/design` | Feature design spec generator |
| `/octo-commit` | Primary commit path: verify the CLAUDE.md workflow, then write a meaningful + compact commit (never pushes) |
| `/octo-memory` | Two-tier memory system orchestrator (short-term + long-term) |
| `/octo-memory-short-term` | Capture daily learnings to short-term memory |
| `/octo-memory-long-term` | Consolidate short-term into long-term topics |

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
