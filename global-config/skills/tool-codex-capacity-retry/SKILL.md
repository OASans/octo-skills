---
name: tool-codex-capacity-retry
description: >
  Human-invoked only: start, inspect, or stop a background Codex capacity-error listener across local projects, with bounded retries and notifications in the initiating conversation. Never invoke autonomously or from another agent or skill.
---

Run commands only when the human user explicitly invokes this skill or requests its start, status, or stop operation. Never invoke it autonomously, from another skill, or at another agent's request. It watches loaded root tasks on the existing local Codex daemon, regardless of project path. Separate daemons and machines need separate listeners.

## Commands

Run the packaged [listener](scripts/listener.py) with Python 3:

```bash
python3 <skill-dir>/scripts/listener.py start --notify-thread "$CODEX_THREAD_ID"
python3 <skill-dir>/scripts/listener.py status
python3 <skill-dir>/scripts/listener.py stop
```

Use the actual directory containing this skill. Resolve the current thread ID before starting; never guess a conversation or use a project path as its identity. The default is three retry messages per task, five minutes apart. Honor requested limits with `--max-retries N` and `--retry-delay SECONDS` on `start`.

- Match only the exact structured error `codexErrorInfo == "serverOverloaded"` on a terminal failed turn. Never match message text, HTTP status, or any other error code.
- Watch new failures after startup. Do not revive historical failures. Exclude the notification conversation and subagents.
- Recheck the failed turn, idle status, direct-input capability, and goal before sending. Preserve the task's model, directory, instructions, and permissions. Never resume an unloaded thread or restart a daemon.
- Retry counts persist per thread across listener restarts and successful turns; a task never receives more than its configured limit. A different error during recovery or an uncertain send stops recovery for that task. A listener connection/API failure stops the listener; do not automatically restart it.
- Each accepted retry posts a notification in the initiating conversation. Active conversations receive a status-only steer; idle conversations receive a status-only turn. Notification failures are logged and never retried. Notifications can use model tokens; they do not authorize work or answer approvals.
- One listener runs per `CODEX_HOME`. Starting again reports its status and keeps its notification destination. `stop` cancels future retries without interrupting tasks already running. State and logs live in `${CODEX_HOME:-~/.codex}/octo-capacity-retry/`.

Report the command result, retry limit, delay, and notification destination compactly. Do not promise recovery while the machine sleeps, the daemon is unavailable, or the listener has stopped.
