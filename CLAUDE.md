## Most Important Instructions

When editing this CLAUDE.md file: space limited. Write compact: no decorative markdown, minimal words, skip formatting for human readability.

Input via Whisper STT. Expect mistranscriptions, confused homophones, misheard technical terms. Interpret/correct input using context before processing. Ask if ambiguous.

# OctoCode Project Guide

Voice-driven multi-agent dev environment in Rust. Uses tmux, OpenAI Whisper (STT), Silero VAD. Architecture: 1 orchestrator + 1 control center (voice UI) + N agent status bars. Config: `~/.octo-code/config.json`.

## Files

src/main.rs,lib.rs — entry
src/modules/cli.rs — CLI arg parsing
src/modules/agent_ipc.rs — Unix socket IPC
src/modules/snapshot.rs — E2E snapshot
src/orchestrator_process/ — tmux setup
src/control_center_process/ — voice UI (main_thread, transcriber_thread, coordinator_thread, panels, transcript_parser)
src/agent_process/ — per-agent status TUI
src/modules/tmux/ — tmux wrappers (grid, layout, panes, session, agents, config, ssh)
src/utils/ — config, logger, model downloader, env, theme
doc/ — all project documentation (see table of contents below)

## Permissions

`.claude/settings.json` manages all Claude Code permissions (allowed/denied commands, web domains). Update it when adding new tools or commands that agents need.

## AI Tools

All build/test/lint commands are wrapped in `ai-tools/` scripts with minimal output to save context tokens. **Use these scripts for covered tasks. Other commands (git, cargo run, tmux, etc.) can be used directly if not covered here.**

./ai-tools/build.sh — build all binaries (errors only)
./ai-tools/test.sh — run tests
  --e2e: E2E tests, --all: unit + E2E (WSL2-safe), <name>: single test. Default: unit tests only.
./ai-tools/fmt.sh — auto-fix formatting
./ai-tools/lint.sh — clippy lint (errors only)
./ai-tools/coverage.sh — per-file coverage table + uncovered line ranges
./ai-tools/sweep.sh — remove old build artifacts

Debug: `tail -f octo-debug.txt` (general log) and `octo-error.txt` (errors) at project root. If an issue is hard to diagnose, add more logging. Keep valuable log statements for future debugging — don't remove them after fixing.

## Workflow

1. `git pull` — sync with remote, merge changes, verify clean state.
2. Plan — read relevant code/docs first. Follow @doc/coding-guide.md for all design and implementation decisions. Read doc/ui.md before UI changes. Simple changes: code directly. Complex: clarify first.
3. Implement — update scripts/install_dependencies.sh for new deps.
4. Run /review once — check all uncommitted changes against coding guide. Fix any issues raised.
5. Add unit tests — target 100% coverage of new/changed code. Run `./ai-tools/coverage.sh` to verify.
6. Verify — loop until all pass: `./ai-tools/test.sh`, `./ai-tools/build.sh`, `./ai-tools/lint.sh`, `./ai-tools/fmt.sh`.

Ownership: every agent owns the entire codebase. If you encounter clippy warnings, build failures, or test failures — even if you didn't cause them — fix them before completing your task.


## Manual Run (debugging / writing E2E tests)

Build first: `./ai-tools/build.sh`

Run headless: `./target/debug/octo-code --instance <id> -c /tmp/test_config.json --detached --no-audio`
Snapshot: `./target/debug/octo-code --snapshot --instance <id>`
Cleanup: `tmux kill-session -t octo-code-<id>`

Flags: --detached (background, no attach), --no-audio (skip Whisper/VAD), --snapshot (pane JSON to stdout), --instance <id> (session name: octo-code-<id>).

Always clean up tmux sessions after manual runs.

## Documentation

See @doc/index.md for full table of contents.
