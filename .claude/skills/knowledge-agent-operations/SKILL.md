---
name: knowledge-agent-operations
description: >
  Safe local code-agent rescue operations for Claude Code and Codex: inspect tmux and
  process state, check memory, message another session, stop it gracefully, and resume
  or reconnect its exact conversation. Load when diagnosing, unblocking, controlling,
  restarting, recovering, or reconnecting Claude Code, Codex, fin-*, or another local
  agent without interrupting live work.
user-invocable: false
---

# Local Agent Operations

Inspect and recover local Claude Code and Codex sessions while preserving live work and conversation state.

## Steps

1. Classify the request as read-only or mutating. Status and diagnosis authorize only pane capture, process inspection, and log reads; require explicit authorization before sending input, stopping a session, or changing a service.
2. Resolve the exact target by tmux pane ID, working directory, title, PID, current command, and dead state:

   ```bash
   tmux list-panes -a -F '#{session_name}\t#{window_index}.#{pane_index}\t#{pane_id}\t#{pane_title}\t#{pane_current_path}\t#{pane_pid}\t#{pane_current_command}\t#{pane_dead}'
   ```

3. Capture the pane without sending input, then inspect its process tree and resources:

   ```bash
   tmux capture-pane -p -t %PANE_ID -S -160
   pstree -ap PANE_PID
   ps -p PID -o pid,ppid,stat,etimes,%cpu,rss,comm,args
   ```

   - Treat `Working`, a spinner, or `Waiting for agents` as active work.
   - Treat a shell prompt with no agent descendants as exited.
   - Report agent and descendant RSS separately from the pane shell and any Remote Control server; one process's RSS is not the session total.
4. If a read-only tmux or process command is sandbox-blocked or returns an unexpectedly empty process tree, treat the result as inconclusive and request approval for that exact command. Do not type into the target merely to test responsiveness.
5. When authorized to message an agent, re-check the pane ID immediately before sending. Send literal text and Enter separately, capture the pane afterward, and wait for the reply:

   ```bash
   tmux send-keys -t %PANE_ID -l -- 'MESSAGE'
   tmux send-keys -t %PANE_ID Enter
   ```

6. Prefer asking a working agent to finish its current batch and stop safely. Do not interrupt it until it confirms the batch is complete unless the user explicitly requests an immediate interruption.
7. When authorized to stop an idle session, use its normal exit command (`/exit` for Claude Code or `/quit` for Codex), verify the TUI exits to a shell, and confirm its descendants are gone. Never use broad commands such as `pkill`, `killall`, or `tmux kill-session`.
8. Before restarting, record the exact agent type, conversation or thread ID, working directory, and desired work state. Confirm the old writer exited so only one process owns the conversation.

## Claude Code Recovery

1. Resume the exact conversation and explicitly enable Remote Control:

   ```bash
   claude --resume "SESSION_ID" --remote-control "SESSION_NAME"
   ```

2. Use `--continue` only when the most recent conversation in that directory is unambiguous. `remoteControlAtStartup` may enable Remote Control globally, but pass `--remote-control` during recovery so the launch does not depend on that setting.
3. Restart the target session after changing hooks, settings, or environment variables because Claude Code reads them at startup. Verify the resumed pane and phone connection before declaring recovery complete.

## Codex Recovery

1. Inspect the native Remote Control daemon without restarting it. `codex remote-control start` owns it — there are no systemd units (`install.sh` removes the historical `octo-codex-*` services):

   ```bash
   pgrep -af 'codex.*app-server'
   tail -n 100 "${CODEX_HOME:-$HOME/.codex}/app-server-control/app-server.log"
   ```

   The daemon's socket is `${CODEX_HOME:-$HOME/.codex}/app-server-control/app-server-control.sock`; a second app-server on the same `CODEX_HOME` conflicts with the phone connection and the chat writer.

2. Resume the exact thread through that daemon:

   ```bash
   codex --remote "unix://${CODEX_HOME:-$HOME/.codex}/app-server-control/app-server-control.sock" -C "WORKING_DIRECTORY" resume "THREAD_ID"
   ```

   Omit `-C` when the launcher already starts in the intended working directory.
   Do not add an approvals or sandbox bypass unless the user explicitly authorizes that risk for this launch.
3. Keep conversation resume separate from durable-goal resume. Choose `Leave paused` when preserving a paused goal; choose `Resume goal` only when the user wants its work restarted.
4. Capture the resumed pane and check `app-server.log` for `thread/resume` over `unix_socket`. Treat an active-writer error as proof that the old writer still owns the thread; resolve it instead of starting another copy.

## Remote Control Rules

- Do not stop the daemon (`codex remote-control stop`) while its assigned sessions are active.
- Use the `app-server-control.sock` path above; never hardcode an observed temporary path.
- Take pane and process snapshots before and after every mutation. Stop and ask if the target, conversation, agent type, or desired work state is ambiguous.

## Key Files

- `global-settings.json` — managed Claude Code Remote Control startup setting
- `global-codex-config.toml` — managed Codex project trust and reviewed hook hashes

<!-- Last verified: 2026-08-21 -->
