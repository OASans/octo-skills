# Global Context

## Most Important Instructions

When editing this CLAUDE.md file: space limited. Write compact: no decorative markdown, minimal words, skip formatting for human readability.

Input via Whisper STT. Expect mistranscriptions, confused homophones, misheard technical terms. Interpret/correct input using context before processing. Ask if ambiguous.

## Memory

**Ignore the default Claude Code memory system.** Use `/yz-memory` skill for all memory operations. Long-term index always loaded: @ai_memory/long_term/index.md. Last day's short-term also loaded: @ai_memory/short_term/latest.md (symlink refreshed by `/memory-long-term`).

## Plan Guide

Before planning, read the coding guide first: `/coding-guide` (includes a Rust Guidance section for Rust projects).

ExitPlanMode approval IS the go-ahead — implement immediately, never re-ask ("want me to start?" / "shall I kick off phase 1?").

Plan format: ExitPlanMode plan = two parts in ONE message, split by a `---` line.

PART 1 human-read — behavior/decision layer ONLY. Never name files/functions/symbols/"Phase N" (→ Part 2). No sentence/line/word limits — concision is categorical, never counted. Four sections, this order:
- Goal: one statement — bug fixed | feature built → ideal outcome, checkable met/not-met; NOT the situation restated (falsifiability test: a Goal is markable met/not-met, narration isn't). GOOD: "Bug: agent reads idle while working after SSH reconnect → done = status correct within one poll cycle." BAD: "User runs client on Mac, server on WSL2, manages agents with OctoCode; today when the client finds a fix…" (situation echo).
- Approach: bullets. Causal story + plan; for a bug: defect → why it produces the symptom → fix step by step. Deletion test per bullet: remove it and the fix reads as non-sequitur ⇒ keep; still stands ⇒ padding. No re-arguing a diagnosis settled in chat; no file:line.
- Decisions: bullets — choices made + why (X over Y); the user's override surface.
- Open questions: bullets, LAST. Each MUST carry a suggested answer applied on user silence ("Suggest: …. Silence = this."). Risks route here: `<risk> → Suggest: <mitigate|accept>` — no separate Risk/Covers section. Fork with no defensible default (user-only info, or unsafe to default) ⇒ do NOT emit a plan; ask first.

PART 2 AI-read — implementing model's spec, not the user's: NO concision/length/format rules (dense + redundant fine). Two non-concision rules: restate §Workflow verify steps (reinforcement → actually run); on user feedback amend in place / diff — NEVER reprint the whole plan.

## Message Guide

Axiom: classify output by READER. A message needs a concision rule only if the user reads it; if not meant to be read, don't emit it as a user message.

Q&A — user question (not a task): answer at the question's OWN resolution, never tutorial resolution; match the question's shape, cut what it did not ask. No numeric limits.
- yes/no Q → verdict + the single load-bearing consequence + the one caveat that changes whether the user cares. No "what it is / why / code path" taxonomy. BAD: "can I delete X?" → 1.8K-char spec w/ What-it-is/Why/Code-path(6 bullets)/Companion/Note. GOOD: "No — it's the daemon's live dedup state; delete it and every scheduled job re-fires once on next restart (regenerates, so no permanent damage)."
- is-this-correct Q → verdict + the precise correction. The supporting tutorial is expansion-on-request, not the answer.
- how/why Q → the FULL mechanism: every non-obvious step + gotcha stays — NOT blanket terseness. Cut by CATEGORY not by word: drop decorative diagrams restating prose, tables/rates not asked for, runnable code when the algorithm was the question. BAD: 5 steps + billing table + ASCII diagram + full jq script. GOOD: the 5 steps incl. both gotchas, nothing else.

Expansion is on request: stop at the resolution; do NOT append "want me to elaborate?". "Bottom line:" / closing re-summary banned — the answer already IS the bottom line.

Closure (task done): outcome + identifier (SHA/version) + gate/memory status + anything needing attention; nothing re-enumerated; one message, at the end only.

Process narration — the harness shows tool calls; don't narrate what it shows: NO tool-call preamble ("Now I'll… / Let me… / Time to…"), NO standing-workflow checklist recitation (§Workflow steps as DONE/NOT-DONE), NO mid-stream "now summarizing" / progress commentary. Two carve-outs (user-read, keep): (1) a genuine deviation/failure/result — surface it WHEN it happens, never swallow it; (2) a one-clause heads-up at an interruptible judgment call ("going with X over Y — proceeding"). Long autonomous runs (multi-phase): zero progress narration by default; only these two.

## AI Tools

All build/test/lint commands are wrapped in `ai_tools/` scripts with minimal output to save context tokens. **Use these scripts for covered tasks. Other commands (git, cargo run, tmux, etc.) can be used directly if not covered here.**

- `ai-tool:review` — `/review` skill. Code review.
- `ai-tool:test` — `./ai_tools/test.sh`. Run tests. Flags: --e2e (E2E tests), --all (unit + E2E, WSL2-safe), <name> (single test). Default: unit tests only.
- `ai-tool:test-e2e` — `./ai_tools/test-e2e.sh`. Run OctoCode instance E2E tests (non-Slack). Optional: <name> (single test). Fast (~50s), no external APIs. Auto-cleans orphaned processes before/after.
- `ai-tool:test-e2e-slack` — `./ai_tools/test-e2e-slack.sh`. Run Slack E2E tests. Optional: <name> (single test). Slow, hits real Slack API (serial). Auto-cleans Slack test channels + orphaned processes. Test daemons auto-terminate after 5 min (`--terminate-after 300`) as safety net against orphaned processes.
- `ai-tool:build` — `./ai_tools/build.sh`. Build all binaries (errors only).
- `ai-tool:style` — `./ai_tools/style/run.sh`. Auto-fix formatting + clippy lint (chains `format.sh` + `lint.sh`). Sibling `./ai_tools/style/file-check.sh` enforces snake_case file/folder names (dot-prefixed dirs exempt) + `_tests.rs` plural; reports >500-line files via `git ls-files`; not chained yet.
- `ai-tool:clean` — `./ai_tools/clean.sh`. Remove old build artifacts + stale test logs. Flag: --full (also `cargo clean` to free disk).

## Workflow

1. `git pull` — sync with remote, merge changes, verify clean state.
2. Add unit tests — target 100% coverage of new/changed code.
3. Verify:
   a. Run `ai-tool:review` once, fix its suggestions.
   b. Loop until `ai-tool:build` and `ai-tool:test` both pass.
   c. Run `ai-tool:style`, fix any issues.
4. Regression tests — every bug fix MUST include a test (unit or E2E) that would have caught the bug. No fix is complete without a regression test.
5. E2E tests — always run `ai-tool:test-e2e` (instance tests) as the final verification step. Run `ai-tool:test-e2e-slack` only when Slack-related code changed (remote_bridge, slack config, transcript watcher). E2E tests are expensive, so: prefer fitting new test scenarios into existing tests as additional user-path steps before creating standalone tests. One test covering multiple features > many single-feature tests. Never suppress stderr in test scripts (`2>&1` hides error output on failure). Verification is via E2E test, not a separate skill: when unsure if a change works (tmux/UI/daemon-ctl/Slack/hook flow), add or extend an E2E test that proves it — run `/e2e-coding-guide` first for the test layout + helper API.
6. Memory — after all tests pass, run /yz-memory to check and update memory.

## Notes

- Branch discipline: ALWAYS commit/work directly on `main`. Never create a branch, never open a PR/merge-request. A fix left on a side branch ships nothing — root cause of the 2026-05-18 OCTO_PEERS-quoting + hook-signal regressions (fixes were committed to an unmerged branch while the release was cut from `main`).
- When implementing, update scripts/install_dependencies.sh for new deps.
- Ownership: every agent owns the entire codebase. If you encounter lint warnings, build failures, test failures, or E2E test failures — fix them. Period. **Never use `git stash`, `git diff`, `git log`, or any other git command to check whether a failure is pre-existing or caused by your changes.** That investigation is a waste of time and tokens. Instead, dive straight into the failing test and the code it exercises, understand the root cause, and fix it. Always run `ai-tool:test-e2e` and fix any failures before declaring done.
- `src/common/` 100% coverage rule: every new file under `src/common/shared_types/`, `src/common/config_provider/`, `src/common/{logger,monotonic,session_settings}.rs` MUST ship with 100% line coverage (`./ai_tools/coverage.sh`). Exec-side `tmux/` + `agent_ipc/` are best-effort: gaps allowed for unreachable branches (real-tmux-required, OS-conditional, defensive panics) but document each gap inline.

# Project Level Context

## Debug

Logs are JSON (one object per line) in `~/.octo-code/logs/` (override via `OCTO_LOG_DIR`; controlled by `debug: true` in config — no CLI flag). Five sinks:
- `octo-debug.txt` — event/action/startup logs WITHOUT an `agent` field.
- `octo-lifecycle.txt` — polling/heartbeat logs (`target: "lifecycle::<source>"`) WITHOUT an `agent` field.
- `octo-audio.txt` — voice pipeline (`target: "audio::<subsystem>.<event>"`); always lands here regardless of agent field.
- `octo-error.txt` — non-agent ERRORs across all targets. Agent ERRORs route to the per-agent file ONLY.
- `agents/{instance}/{display_name}.txt` — every event tagged with `agent` or `agent_id` (or carried via span). Routing-only: agent-tagged events leave the four global sinks. Filename uses the human-readable display_name from config (validated `^[a-zA-Z][a-zA-Z0-9_-]*$`); falls back to agent_id if unmapped.

Archive: orchestrator start moves the previous run to `~/.octo-code/logs/last/` (mirrors layout). Exactly one prior run is kept; older archive is wiped first. Daemon (append mode) doesn't trigger archive. Per-instance scoped — concurrent instances don't disturb each other's archives.

Query: `jq 'select(.fields.message | contains("xx"))' ~/.octo-code/logs/octo-debug.txt`, or filter by lifecycle cycle: `jq 'select(.target == "lifecycle::coordinator.slug_poll")' ~/.octo-code/logs/octo-lifecycle.txt`, or by agent: `tail -f ~/.octo-code/logs/agents/default/engineer.txt | jq`. New polling sites: pass `target: "lifecycle::<subsystem>.<cycle>"`. New per-agent context: stamp `agent = %agent_id` (or `agent_id = …`) at the call site OR enclose in `info_span!("…", agent = …)` — see @ai_memory/long_term/topics/json-logging.md.

E2E test logs: harness sets `OCTO_LOG_DIR=$CARGO_MANIFEST_DIR` so each test writes `octo-{debug,lifecycle,audio,error}-{instance_id}.txt` + `agents/{instance_id}/*.txt` + `last/{instance_id files}` at the project root. `Drop` cleans all of them on success; **preserves on failure**. When debugging a failed E2E test: `ls octo-*-{instance_id}.txt agents/{instance_id}/` then query with jq. Manual cleanup: `./ai_tools/clean.sh` (sweeps project root and `~/.octo-code/logs/`, including `agents/` and `last/`).

# OctoCode Project Guide

Voice-driven multi-agent dev environment in Rust. Uses tmux, OpenAI Whisper (STT), Silero VAD. Architecture: 1 orchestrator + 1 daemon + 1 dashboard UI process. The dashboard UI renders the per-agent status bar strip itself at the bottom of its own pane — there is no separate per-agent status bar process. Config: `~/.octo-code/config.json`.

## Module Map

Directory-level only. Update when adding/removing directories, not individual files.

src/ — lib.rs (shared library root)
src/cli/ — CLI binary: arg parsing, daemon launch, model download, status display
src/common/ — shared infrastructure (fully flat). Post common-refactor (CR1–CR9): only `shared_types/` (wire types) + `agent_ipc/`, `config_provider/`, `tmux/` (genuinely shared impl) + `logger.rs`, `monotonic.rs`, `session_settings.rs`.
src/common/shared_types/ — wire-contract types: agent, agent_entry, coordinator_state, daemon_ctl, hook_event, media_paths, project, remote_bridge, scheduled_jobs, tmux, voice, voice_status. Every file at 100% line coverage; new files MUST ship with 100%.
src/common/{agent_ipc,config_provider,tmux}/ — cohesive cross-process impl (every process calls them). `config_provider/` at 100%; `agent_ipc/` and `tmux/` best-effort with documented exec-side gaps.
src/common/{logger,monotonic,session_settings}.rs — top-level shared utilities. Each at ≥99% line coverage.
src/daemon_process/ — daemon runtime
src/daemon_process/common/ — shared daemon modules
src/daemon_process/threads/<name>/ — one folder per daemon thread (coordinator, voice_pipeline, transcriber, remote_bridge, peer_messaging, ssh_connect, agent_init, terminate_timer)
src/dashboard_ui_process/ — dashboard UI (TUI + embedded per-agent status bar strip)
src/dashboard_ui_process/common/ — shared UI modules
src/dashboard_ui_process/threads/<name>/ — one folder per UI thread (main, daemon_client, capslock)
release/ — end-user README; release_docs/ — extra setup guides bundled into the release tarball by scripts/release.sh

## Manual Run (debugging / writing E2E tests)

Build first: `./ai_tools/build.sh`

Run headless: `./target/debug/octo-code start --instance <id> -c /tmp/test_config.json --no-audio`
Cleanup: `./target/debug/octo-code stop --instance <id>`

Subcommands: `start` (always background), `stop`, `status`, `resize`, `command <cmd>`, `hook-event <spec>`, `agent <list|activate|deactivate>`. Common flags: --instance <id>, --no-audio. (File logging is controlled by `debug: true` in `~/.octo-code/config.json` — no CLI flag.)

Always clean up tmux sessions after manual runs.

## Documentation

End-user setup guides live in `release/README.md` + `release_docs/`. Internal architecture knowledge is consolidated into the long-term-memory system (@ai_memory/long_term/index.md is always loaded). Active design intent (refactor plans, voice-optimization tracker) lives in `ai_doc/`.

