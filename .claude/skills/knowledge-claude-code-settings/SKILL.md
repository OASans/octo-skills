---
name: knowledge-claude-code-settings
description: >
  Claude Code settings gotchas: auto-compact is a token window not a %;
  verify a setting is real by grepping the binary. Load for global-settings.json edits.
user-invocable: false
---

# Claude Code Settings & Env-Var Gotchas

## What
- **Auto-compact is a token window, not a percentage.** It triggers as used tokens approach `min(window, model_max_context)`. Control it with the `autoCompactWindow` settings key ("auto" or a token number), the `CLAUDE_CODE_AUTO_COMPACT_WINDOW` env var (token number; highest-priority override), or `autoCompactEnabled` (bool). "auto" is model-tuned and adapts per model; a fixed number is model-specific and caps at the model max. There is **no percentage knob** — `CLAUDE_CODE_AUTOCOMPACT_PCT_OVERRIDE` is a dead no-op (the literal string isn't in the binary).
- **Settings/env vars can be silently dead.** A removed or never-implemented key is a no-op, not an error — it fails quiet.

## How to Apply
- Express any auto-compact threshold in **tokens**, never a percent. In `global-settings.json`, `CLAUDE_CODE_AUTO_COMPACT_WINDOW` is the highest-priority override — a token count sized as a fraction of the model's context window. (The concrete number lives in the settings file, not here, so this note doesn't go stale.)
- Before trusting any Claude Code setting/env var, **grep the installed binary for the literal string**. Resolve the binary via `which claude`, readlink to the real install (a non-stripped ELF, e.g. under `~/.local/share/claude/versions/<ver>`), then grep the name. Absent string = no-op. This is how the dead PCT_OVERRIDE was caught.

## Key Files
- `global-settings.json` — `env` block (`CLAUDE_CODE_AUTO_COMPACT_WINDOW`)
- installed binary — resolve via `which claude`

<!-- Last verified: 2026-06-10, commit: 656045f -->
