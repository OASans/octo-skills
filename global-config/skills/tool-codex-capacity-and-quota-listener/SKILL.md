---
name: tool-codex-capacity-and-quota-listener
description: >
  Human-invoked only: start, inspect, or stop a background Codex capacity and weekly-quota listener across local projects. Retry capacity failures and send a graceful stop command below 10% weekly allowance. Never invoke autonomously or from another agent or skill.
---

Run commands only when the human user explicitly invokes this skill or requests its start, status, or stop operation. Never invoke it autonomously, from another skill, or at another agent's request. Starting authorizes the quota stop command described below on the user’s behalf. It watches loaded root tasks on the existing local Codex daemon, regardless of project path. Separate daemons and machines need separate listeners.

## Weekly quota

- Read `account/rateLimits/read` each scan. Below 10% weekly allowance remaining, send a user-authorized stop command once per active root conversation, including the initiating chat. Watch newly active chats while quota stays low. Idle chats are not awakened.
- The command tells parents to start no new work or subagents, let existing subagents finish their current assignments, save progress and a handoff, pause active goals, and stop until the user explicitly resumes. Never interrupt workers or automatically resume paused work.
- Suppress capacity retries and cancel pending retries while quota is low. Quota recovery clears notification tracking; it does not resume tasks. Tracking persists across listener restarts.
- This is a cooperative stop request, not a spending cap. Finishing work and delivering commands can consume quota. Only loaded conversations on this daemon are covered.
- An unavailable or invalid weekly allowance stops the listener; never guess usage. Failed or uncertain command delivery is logged and not retried.

## Commands

Run the packaged [listener](scripts/listener.py) with Python 3:

```bash
python3 <skill-dir>/scripts/listener.py start --notify-thread "$CODEX_THREAD_ID"
python3 <skill-dir>/scripts/listener.py status
python3 <skill-dir>/scripts/listener.py stop
```

Use the actual directory containing this skill. Resolve the current thread ID before starting; never guess a conversation or use a project path as its identity. The default is three retry messages per task, five minutes apart. Honor requested limits with `--max-retries N` and `--retry-delay SECONDS` on `start`.

- Match only the exact structured error `codexErrorInfo == "serverOverloaded"` on a terminal failed turn. Never match message text, HTTP status, or any other error code.
- For capacity recovery, watch new failures after startup. Do not revive historical failures. Exclude the notification conversation and subagents; skip threads with no materialized history or unsupported ephemeral history.
- Recheck the failed turn, idle status, direct-input capability, and goal before sending. Preserve the task's model, directory, instructions, and permissions. Never resume an unloaded thread or restart a daemon.
- Retry counts persist per thread across listener restarts and successful turns; a task never receives more than its configured limit. A different error during recovery or an uncertain send stops recovery for that task. A listener connection/API failure stops the listener; do not automatically restart it.
- Each accepted capacity retry posts a notification in the initiating conversation. Active conversations receive a status-only steer; idle conversations receive a status-only turn. Notification failures are logged and never retried. Notifications can use model tokens; they do not authorize work or answer approvals.
- One listener runs per `CODEX_HOME`. Starting again reports its status and keeps its notification destination. `stop` cancels future retries without interrupting tasks already running. State and logs live in `${CODEX_HOME:-~/.codex}/octo-capacity-retry/`.

Report the command result, retry limit, delay, quota threshold, and notification destination compactly. Installing does not start the listener. If an older listener is running, explicitly stop and start it when the user requests activation of the updated listener. Do not promise recovery while the machine sleeps, the daemon is unavailable, or the listener has stopped.
