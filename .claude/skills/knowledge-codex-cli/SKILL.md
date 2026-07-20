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
- **Install/update:** on macOS/Linux, `install.sh` installs both the npm package under user-owned `~/.local/share/octo-codex` and OpenAI's standalone package under `$CODEX_HOME/packages/standalone` (default `~/.codex/packages/standalone`). It pins the official installer's visible command to `~/.local/bin/codex`; `install_codex_wrapper` removes only that symlink and restores the managed launcher. The launcher uses the npm package, checks for a newer release on every start, serializes concurrent updates, and warns before using the installed release when an update fails. Windows shell installs keep the npm package only.
- **Hook trust bypass is launch-only and always warns:** `--dangerously-bypass-hook-trust` bypasses persisted hook trust for one invocation, and Codex prints a TUI warning every time it is present. Persisted trust does not hide that warning; for a banner-free launch, remove the flag and use `/hooks` to trust definitions instead of filtering stderr (the TUI renders it). `global-codex-wrapper.sh` currently passes the flag on every launch.
- **Managed hook trust is hash-bound:** `global-codex-config.toml` persists the reviewed global-hook hashes plus the identical `SubagentStop` hook for `fin-1` through `fin-6`; those projects also need `trust_level = "trusted"` or Codex skips their `.codex/` layers. When a hook definition changes, run `./install.sh` to deploy it, re-review the live definition with `/hooks`, copy its new `trusted_hash` into the managed config, then run `./install.sh` again.
- **octo-skills install.sh is dual-target:** mirrors `skills/*` to both `~/.claude/skills` and `~/.codex/skills`, installs `global-CLAUDE.md` as both `CLAUDE.md` and `AGENTS.md`, and derives `~/.codex/hooks.json` from `global-settings.json` via jq. OctoCode exports `OCTO_AGENT_ID`/`OCTO_HOOK_FILE`, so the shared git-sync and agent-activity hooks port verbatim. The derivation keeps `SessionStart`, `UserPromptSubmit`, `PreToolUse`, `PostToolUse`, `PermissionRequest`, and `Stop`, while dropping Claude-only matcher groups for Agent/Task model gating, AskUserQuestion/ExitPlanMode, and Skill usage logging.

## Key Files
- `install.sh` — dual-target install + jq hook derivation.
- `global-codex-wrapper.sh` — auto-updates the managed package and passes the per-launch hook-trust bypass.
- `global-codex-config.toml` — managed project trust and reviewed hook-definition hashes.
- `codex-migration.md` — full Claude→Codex feature map and doc sources (hooks: learn.chatgpt.com/docs/hooks).

<!-- Last verified: 2026-07-20, commit: b8d853c -->
