# Codex hybrid / migration notes

Reference for porting this Claude Code setup (global CLAUDE.md, settings, hooks, `octo-skills`) to OpenAI Codex CLI, for a hybrid Claude Code + Codex workflow. Captured 2026-06; Codex tooling moves fast, re-verify before acting.

## Feature map

| Claude Code | Codex equivalent | Portable? |
|---|---|---|
| `claude` / `claude -p "…"` | `codex` (TUI) / `codex exec "…"` | Yes — same idea |
| Global `~/.claude/CLAUDE.md` | Global `~/.codex/AGENTS.md` | Rename/symlink |
| Project `CLAUDE.md` | Project `AGENTS.md` (+ nested) | Rename/symlink |
| `settings.json` (JSON) | `~/.codex/config.toml` (TOML) | No — different format |
| Hooks in `settings.json` | `~/.codex/hooks.json` / `[hooks]` in config.toml | Similar schema, adapt |
| `~/.claude/skills/*/SKILL.md` | `~/.codex/skills/*/SKILL.md` | Yes — same standard |

## 1. CLI terminal tool

Open-source binary (`npm i -g @openai/codex` or brew). Two modes:
- `codex` — interactive TUI (the Claude Code REPL equivalent).
- `codex exec "prompt"` — non-interactive/headless: runs one task to completion, progress to stderr, final message to stdout, clean exit (the `claude -p` equivalent). `--json` emits JSON-Lines for piping to `jq` in scripts/CI.

## 2. Global prompt

Codex uses `AGENTS.md`, not a single overridable system prompt. Instruction chain built once per session, merged root-first → leaf-last (closer files override):
1. `~/.codex/AGENTS.md` (global; `AGENTS.override.md` wins over it if present).
2. Project-root `AGENTS.md`, then nested `AGENTS.md` down to cwd.

Like CLAUDE.md, this is appended guidance — the core system prompt is baked into the binary. `CODEX_HOME` relocates `~/.codex`. Hybrid trick: keep one source file, symlink `CLAUDE.md` → `AGENTS.md`.

## 3. Global settings

`~/.codex/config.toml` — TOML, not JSON, so `global-settings.json` does NOT port; maintain separately. Holds `model`, `approval_policy` (`untrusted`/`on-request`/`never`/granular), `sandbox_mode` (`read-only`/`workspace-write`/`danger-full-access`), MCP servers, etc.

Profiles (no Claude Code equivalent): `--profile ci` overlays `~/.codex/ci.config.toml` on the base. Precedence: CLI flags > project `.codex/config.toml` (trusted projects only) > selected profile > global config.

## 4. Hooks

Recent addition (PreToolUse/PostToolUse ~v0.117; UserPromptSubmit Mar 2026), modeled on Claude Code. Ten events: `SessionStart`, `SubagentStart`, `PreToolUse`, `PermissionRequest`, `PostToolUse`, `PreCompact`, `PostCompact`, `UserPromptSubmit`, `SubagentStop`, `Stop`.

- Defined in `~/.codex/hooks.json` (global), project `.codex/hooks.json`, or inline `[hooks]` in config.toml; layers merge.
- Same JSON-over-stdin/stdout contract: stdin has `session_id`, `cwd`, `hook_event_name`, `tool_name`, `tool_input`…; stdout returns `continue`, `permissionDecision`, `additionalContext`, `updatedInput`; exit code 2 blocks.
- Trust model: must review+trust a hook definition (by hash) before it runs.
- Lighter path: `notify` (external program on `agent-turn-complete`) + built-in `tui.notifications`.

Hook scripts may be largely reusable; wrapper config and some field names differ. Newest of the five subsystems — expect rougher edges.

## 5. Skills (global supported)

Codex adopted the same `SKILL.md` standard (Anthropic format, now the open spec at agentskills.io shared by Codex, Claude Code, Gemini CLI, Cursor, Copilot, …). Same progressive disclosure: metadata at startup, body on demand.

- Global skills: `~/.codex/skills/<name>/SKILL.md` — across all projects, like `~/.claude/skills/`. Project skills also supported.
- Required frontmatter: `name` + `description`.
- Invocation: `/skills` menu (manual) or implicit auto-invocation from the description.
- Codex's older custom prompts (`~/.codex/prompts/*.md` slash commands) are deprecated in favor of skills — don't build on them.

Caveat for this repo: skills lean on Claude-Code-specific frontmatter (`disable-model-invocation: true`, `user-invocable: false`) and `/octo-*` slash-command triggering. The `SKILL.md` body + name/description port directly; those control-flow flags and slash semantics are NOT in the shared standard — verify per skill in Codex.

## Hybrid takeaway

`install.sh` could grow a Codex target with modest effort:
- Copy `skills/*` to both `~/.claude/skills/` and `~/.codex/skills/` (same format).
- Symlink an `AGENTS.md` from the CLAUDE.md source.
- Hand-write a separate `config.toml` (the JSON→TOML settings gap is the only hard wall).
- Hooks: portable in spirit, adapt per event.

## Sources

- Non-interactive mode: https://developers.openai.com/codex/noninteractive — Headless (DeepWiki): https://deepwiki.com/openai/codex/4.2-headless-execution-mode-(codex-exec)
- AGENTS.md: https://developers.openai.com/codex/guides/agents-md
- Config reference: https://developers.openai.com/codex/config-reference — Config basics: https://developers.openai.com/codex/config-basic
- Hooks: https://developers.openai.com/codex/hooks — Hooks system (DeepWiki): https://deepwiki.com/openai/codex/3.11-hooks-system
- Skills: https://developers.openai.com/codex/skills — Custom prompts (deprecated): https://developers.openai.com/codex/custom-prompts
