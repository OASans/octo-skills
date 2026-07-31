---
name: knowledge-claude-code-settings
description: >
  Claude Code settings gotchas: token-window auto-compact; verbose, Remote Control,
  hooks, and env load at startup; verify keys in the binary.
user-invocable: false
---

# Claude Code Settings & Env-Var Gotchas

## What
- **Auto-compact is a token window, not a percentage.** It triggers as used tokens approach `min(window, model_max_context)`. Control it with the `autoCompactWindow` settings key ("auto" or a token number), the `CLAUDE_CODE_AUTO_COMPACT_WINDOW` env var (token number; highest-priority override), or `autoCompactEnabled` (bool). "auto" is model-tuned and adapts per model; a fixed number is model-specific and caps at the model max. There is **no percentage knob** — `CLAUDE_CODE_AUTOCOMPACT_PCT_OVERRIDE` is a dead no-op (the literal string isn't in the binary).
- **Settings/env vars can be silently dead.** A removed or never-implemented key is a no-op, not an error — it fails quiet.
- **Hooks + env are read once at session start.** Editing settings (or running `./install.sh`) does not affect live sessions — a new hook/env value takes effect only on the next `claude` launch.
- **Full tool output is opt-in.** Top-level `"verbose": true` shows full tool output every turn. In a live session, Ctrl+O opens the transcript viewer, Ctrl+E expands its content, and `/export` writes a readable transcript.
- **Remote Control can start automatically.** Top-level `"remoteControlAtStartup": true` starts the Remote Control bridge for each new interactive session; Claude.ai authentication and organization eligibility still apply.
- **A "disable" env var can be advisory-only.** `CLAUDE_CODE_DISABLE_BACKGROUND_TASKS` only suppresses the background-jobs advisory text for Bash/Agent; it does not reject an explicit `run_in_background: true`. A hard block needs a `PreToolUse` hook denying `.tool_input.run_in_background == true` (matcher `Bash|Agent`).

## How to Apply
- Express any auto-compact threshold in **tokens**, never a percent. In `global-settings.json`, `CLAUDE_CODE_AUTO_COMPACT_WINDOW` is the highest-priority override — a token count sized as a fraction of the model's context window. (The concrete number lives in the settings file, not here, so this note doesn't go stale.)
- Keep `remoteControlAtStartup` (and `verbose`, if ever re-enabled) at the top level of `global-settings.json`. Deploy with `./install.sh`, then start a new interactive session.
- Before trusting any Claude Code setting/env var, **grep the installed binary for the literal string**. Resolve the binary via `which claude`, readlink to the real install (a non-stripped ELF, e.g. under `~/.local/share/claude/versions/<ver>`), then grep the name. Absent string = no-op. This is how the dead PCT_OVERRIDE was caught.

## Key Files
- `global-settings.json` — `env` block (`CLAUDE_CODE_AUTO_COMPACT_WINDOW`)
- installed binary — resolve via `which claude`

<!-- Last verified: 2026-07-23, commit: bc3698f -->
