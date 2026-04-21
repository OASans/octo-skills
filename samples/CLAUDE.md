# Global Context

## Most Important Instructions

When editing this CLAUDE.md file: space limited. Write compact: no decorative markdown, minimal words, skip formatting for human readability.

Input via Whisper STT. Expect mistranscriptions, confused homophones, misheard technical terms. Interpret/correct input using context before processing. Ask if ambiguous.

## Memory

**Ignore the default Claude Code memory system.** Use `/yz-memory` skill for all memory operations. Long-term index always loaded: @ai-memory/long-term/index.md. Last day's short-term also loaded: @ai-memory/short-term/latest.md (symlink refreshed by `/memory-long-term`).

## Plan Guide

Before planning, always run `/coding-guide` skill plus any other coding guide this CLAUDE.md specifies. Additional coding guides:
@ai-doc/rust_coding_guide.md

After plan approval, start implementation immediately. Do not ask "want me to start?" / "shall I kick off phase 1?" — ExitPlanMode approval IS the go-ahead.

## AI Tools

All build/test/lint commands are wrapped in `ai-tools/` scripts with minimal output to save context tokens. **Use these scripts for covered tasks. Other commands (git, cargo run, tmux, etc.) can be used directly if not covered here.**

- `ai-tool:review` — `/review` skill. Code review.
- `ai-tool:test` — `./ai-tools/test.sh`. Run tests. Flags: --e2e (E2E tests), --all (unit + E2E, WSL2-safe), <name> (single test). Default: unit tests only.
- `ai-tool:test-e2e` — `./ai-tools/test-e2e.sh`. Run OctoCode instance E2E tests (non-Slack). Optional: <name> (single test). Fast (~50s), no external APIs. Auto-cleans orphaned processes before/after.
- `ai-tool:test-e2e-slack` — `./ai-tools/test-e2e-slack.sh`. Run Slack E2E tests. Optional: <name> (single test). Slow, hits real Slack API (serial). Auto-cleans Slack test channels + orphaned processes. Test daemons auto-terminate after 5 min (`--terminate-after 300`) as safety net against orphaned processes.
- `ai-tool:build` — `./ai-tools/build.sh`. Build all binaries (errors only).
- `ai-tool:style` — `./ai-tools/style.sh`. Auto-fix formatting + clippy lint.
- `ai-tool:clean` — `./ai-tools/clean.sh`. Remove old build artifacts + stale test logs. Flag: --full (also `cargo clean` to free disk).

## Workflow

1. `git pull` — sync with remote, merge changes, verify clean state.
2. Add unit tests — target 100% coverage of new/changed code.
3. Verify:
   a. Run `ai-tool:review` once, fix its suggestions.
   b. Loop until `ai-tool:build` and `ai-tool:test` both pass.
   c. Run `ai-tool:style`, fix any issues.
4. Regression tests — every bug fix MUST include a test (unit or E2E) that would have caught the bug. No fix is complete without a regression test.
5. E2E tests — always run `ai-tool:test-e2e` (instance tests) as the final verification step. Run `ai-tool:test-e2e-slack` only when Slack-related code changed (remote_bridge, slack config, transcript watcher). E2E tests are expensive, so: prefer fitting new test scenarios into existing tests as additional user-path steps before creating standalone tests. One test covering multiple features > many single-feature tests. Never suppress stderr in test scripts (`2>&1` hides error output on failure).
6. E2E verify — use `/e2e-verify <description>` to verify behavior against a live test instance. Use proactively when unsure if a change works (tmux interaction, UI behavior, daemon-ctl flow). If the verification reveals a gap, formalize it into an automated E2E test in `tests/`. See `slack-e2e-test-plan.md` for Slack-specific cases.
7. Memory — after all tests pass, run /yz-memory to check and update memory.

## Notes

- When implementing, update scripts/install_dependencies.sh for new deps.
- Ownership: every agent owns the entire codebase. If you encounter lint warnings, build failures, test failures, or E2E test failures — fix them. Period. **Never use `git stash`, `git diff`, `git log`, or any other git command to check whether a failure is pre-existing or caused by your changes.** That investigation is a waste of time and tokens. Instead, dive straight into the failing test and the code it exercises, understand the root cause, and fix it. Always run `ai-tool:test-e2e` and fix any failures before declaring done.

# Project Level Context

## Task Scope

At the start of every task, identify which project it targets:
- **octo-code** (default): this repo's voice-driven multi-agent dev env. No extra context to load.
- **octo-echo**: Swift-UI-on-Mac + Rust-server transcription tool. If the task mentions octo-echo, the `echo` feature flag, Swift UI, loopback/system-audio capture, or touches shared voice-pipeline code that affects octo-echo — read @ai-doc/octo-echo-context.md before planning.


## Debug

Logs are JSON (one object per line) in `octo-debug.txt` (general) and `octo-error.txt` (errors) at project root. Query with `jq`: `jq 'select(.fields.message | contains("xx"))' octo-debug.txt`. Live tail: `tail -f octo-debug.txt | jq`. If an issue is hard to diagnose, add more logging. Keep valuable log statements for future debugging — don't remove them after fixing.

E2E test logs: each test instance writes `octo-debug-{instance_id}.txt` and `octo-error-{instance_id}.txt` at project root. On test success, `Drop` cleans them. **On failure, logs are preserved.** When debugging a failed E2E test, check these files: `ls octo-{debug,error}-*.txt` then query with jq. Stale logs auto-cleaned at start of next test run. Manual cleanup: `./ai-tools/clean.sh`.

# OctoCode Project Guide

Voice-driven multi-agent dev environment in Rust. Uses tmux, OpenAI Whisper (STT), Silero VAD. Architecture: 1 orchestrator + 1 daemon + 1 dashboard UI process. The dashboard UI renders the per-agent status bar strip itself at the bottom of its own pane — there is no separate per-agent status bar process. Config: `~/.octo-code/config.json`.

## Module Map

Directory-level only. Update when adding/removing directories, not individual files.

src/ — lib.rs (shared library root)
src/cli/ — CLI binary: arg parsing, daemon launch, model download, status display
src/common/ — shared infrastructure
src/common/modules/ — cross-process modules (IPC, tmux, Slack bridge, daemon-ctl)
src/common/shared_types.rs — cross-process domain types (AgentId, AgentState, etc.)
src/common/state_types/ — wire-contract types shared across daemon↔UI socket (CoordinatorState, AgentEntry, VoiceStatus, etc.)
src/common/theme.rs — shared ratatui color palette
src/common/utils/ — config, logger, env, session settings
src/daemon_process/ — daemon runtime
src/daemon_process/common/ — shared daemon modules
src/daemon_process/threads/<name>/ — one folder per daemon thread (coordinator, voice_pipeline, transcriber, slack_bridge, ssh_connect, agent_init, terminate_timer)
src/dashboard_ui_process/ — dashboard UI (TUI + embedded per-agent status bar strip)
src/dashboard_ui_process/common/ — shared UI modules
src/dashboard_ui_process/threads/<name>/ — one folder per UI thread (main, daemon_client, capslock, vscode)
doc/ — project documentation (see @doc/index.md)

## Manual Run (debugging / writing E2E tests)

Build first: `./ai-tools/build.sh`

Run headless: `./target/debug/octo-code start --instance <id> -c /tmp/test_config.json --no-audio`
Cleanup: `./target/debug/octo-code stop --instance <id>`

Subcommands: `start` (always background), `stop`, `status`, `resize`, `command <cmd>`, `hook-event <spec>`, `agent <list|activate|deactivate>`. Common flags: --instance <id>, --no-audio, --debug.

Always clean up tmux sessions after manual runs.

## Documentation

See @doc/index.md for full table of contents.
