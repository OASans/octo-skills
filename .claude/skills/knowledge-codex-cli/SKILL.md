---
name: knowledge-codex-cli
description: >
  Codex CLI (OpenAI): ~/.codex layout (AGENTS.md, skills, hooks.json, config.toml),
  hooks.json event nesting, npm-g EACCES. Load for Codex or hybrid Claude+Codex setup.
user-invocable: false
---

# Codex CLI (OpenAI) — hybrid Claude Code + Codex

## What
Codex is OpenAI's Claude-Code-equivalent CLI, adopting the same open `SKILL.md` standard (agentskills.io). Config home `~/.codex` (relocatable via `CODEX_HOME`):
- `AGENTS.md` — global appended prompt, the `CLAUDE.md` equivalent (merged root-first→leaf-last).
- `skills/<name>/SKILL.md` — same standard as Claude Code (`name`+`description` required).
- `hooks.json` — hooks; contract (stdin/stdout JSON, `additionalContext`, exit 2 blocks) mirrors Claude Code, so plain git/shell hook commands port as-is.
- `config.toml` — settings; **TOML, not JSON**, so Claude's `settings.json` does NOT port (maintain separately).

Run modes: `codex` = interactive TUI (claude REPL); `codex exec "…"` = headless one-shot (claude -p), `--json` for JSON-Lines.

## How to Apply
- **hooks.json GOTCHA — events nest under a top-level `hooks` key, NOT the root.** Shape: `{"hooks":{"<Event>":[{"matcher":"…","hooks":[{"type":"command","command":"…","timeout":600}]}]}}`. Putting the event at the root fails: `unknown field 'SessionStart', expected 'description' or 'hooks'`. The inner block is identical to Claude's `settings.json` `hooks`, so derive Codex hooks from it: `jq '{hooks: {SessionStart: .hooks.SessionStart}}' global-settings.json`. Events: SessionStart, SubagentStart, PreToolUse, PermissionRequest, PostToolUse, PreCompact, PostCompact, UserPromptSubmit, SubagentStop, Stop.
- **Install:** `npm i -g @openai/codex`. On apt-installed Node the global prefix `/usr/local/lib/node_modules` is root-owned → npm fails `EACCES`; brew/macOS prefix is user-owned (no sudo). Pattern: try `npm i -g` unprivileged, and only on `grep -q EACCES` retry `sudo npm i -g`.
- **octo-skills install.sh is dual-target:** mirrors `skills/*` to both `~/.claude/skills` and `~/.codex/skills`, installs `global-CLAUDE.md` as both `CLAUDE.md` and `AGENTS.md`, and derives `~/.codex/hooks.json` from `global-settings.json` via jq. OctoCode exports `OCTO_AGENT_ID`/`OCTO_HOOK_FILE`, so the shared git-sync and agent-activity hooks port verbatim. The derivation keeps `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PermissionRequest`, and `Stop`, while dropping Claude-only matcher groups for Agent/Task model gating, AskUserQuestion/ExitPlanMode, and Skill usage logging.

## Key Files
- `install.sh` — dual-target install + jq hook derivation.
- `codex-migration.md` — full Claude→Codex feature map and doc sources (hooks: learn.chatgpt.com/docs/hooks).

<!-- Last verified: 2026-07-12, commit: f12ae06 -->
