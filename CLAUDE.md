# Global Context

## Most Important Instructions

When editing this CLAUDE.md file: space limited. Write compact: no decorative markdown, minimal words, skip formatting for human readability.

Input via Whisper STT. Expect mistranscriptions, confused homophones, misheard technical terms. Interpret/correct input using context before processing. Ask if ambiguous.

## Plan Guide

Plans must stay high-level. Focus on what changes and why, not how at the code level.
- No low-level code changes, class definitions, code snippets, or implementation details in plans — unless the code is critical (user must read it to understand risk or a non-obvious decision).
- Clearly call out important design decisions: new types, trait boundaries, module splits, API shape changes. User will ask for details when needed.
- Structure: goals → approach → key decisions → affected areas. Not a line-by-line diff.

## AI Tools

All build/test/lint commands are wrapped in `ai-tools/` scripts with minimal output to save context tokens. **Use these scripts for covered tasks. Other commands (git, cargo run, tmux, etc.) can be used directly if not covered here.**

- `ai-tool:review` — `/review` skill. Code review. **Mandatory** in verify step.
- `ai-tool:test` — `./ai-tools/test.sh`. Run tests. Flags: --e2e (E2E tests), --all (unit + E2E, WSL2-safe), <name> (single test). Default: unit tests only.
- `ai-tool:build` — `./ai-tools/build.sh`. Build all binaries (errors only).
- `ai-tool:lint` — `./ai-tools/lint.sh`. Clippy lint (errors only).
- `ai-tool:fmt` — `./ai-tools/fmt.sh`. Auto-fix formatting.
- `ai-tool:sweep` — `./ai-tools/sweep.sh`. Remove old build artifacts.

## Workflow

1. `git pull` — sync with remote, merge changes, verify clean state.
2. Plan — read relevant code/docs first. Follow @doc/coding-guide.md for all design and implementation decisions. See Plan Guide above. Simple changes: code directly. Complex: clarify first.
3. Implement — update scripts/install_dependencies.sh for new deps.
4. Add unit tests — target 100% coverage of new/changed code.
5. Verify:
   a. Run `ai-tool:review` once, fix its suggestions.
   b. Loop until `ai-tool:build` and `ai-tool:test` both pass.
   c. Run `ai-tool:lint` and `ai-tool:fmt`, fix any issues.

Ownership: every agent owns the entire codebase. If you encounter lint warnings, build failures, or test failures — even if you didn't cause them — fix them before completing your task.

# Project Level Context

## Debug

`tail -f octo-debug.txt` (general log) and `octo-error.txt` (errors) at project root. If an issue is hard to diagnose, add more logging. Keep valuable log statements for future debugging — don't remove them after fixing.

# OctoCode Project Guide

Voice-driven multi-agent dev environment in Rust. Uses tmux, OpenAI Whisper (STT), Silero VAD. Architecture: 1 orchestrator + 1 control center (voice UI) + N agent status bars. Config: `~/.octo-code/config.json`.

## Module Map

Directory-level only. Update when adding/removing directories, not individual files.

src/ — entry points (main.rs, lib.rs)
src/modules/ — shared modules (CLI, IPC, snapshot)
src/orchestrator_process/ — tmux session setup
src/control_center_process/ — voice UI (threads, panels, transcript parsing)
src/agent_process/ — per-agent status TUI
src/modules/tmux/ — tmux wrappers (grid, layout, panes, session)
src/utils/ — config, logger, model downloader, env, theme
doc/ — project documentation (see @doc/index.md)

## Manual Run (debugging / writing E2E tests)

Build first: `./ai-tools/build.sh`

Run headless: `./target/debug/octo-code --instance <id> -c /tmp/test_config.json --detached --no-audio`
Snapshot: `./target/debug/octo-code --snapshot --instance <id>`
Cleanup: `tmux kill-session -t octo-code-<id>`

Flags: --detached (background, no attach), --no-audio (skip Whisper/VAD), --snapshot (pane JSON to stdout), --instance <id> (session name: octo-code-<id>).

Always clean up tmux sessions after manual runs.

## Documentation

See @doc/index.md for full table of contents.
