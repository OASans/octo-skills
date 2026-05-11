---
name: octo-peer
description: Send messages to other agents in the same OctoCode session. Use when the user asks you to coordinate with another agent (local or SSH-remote), delegate a task, ask another agent to verify or investigate something, or pass results back to a peer that requested work.
---

# OctoCode peer messaging

This skill lets you send messages directly to other AI coding agents running under the same OctoCode daemon. Peers can be local or SSH-remote — the daemon handles delivery uniformly.

## What this skill is (and what it is NOT)

Peer messaging is **OctoCode's own feature**, separate from Claude Code's hook system. Claude Code's `.claude/settings.json` hooks fire on `UserPromptSubmit` / `Stop` / `PermissionRequest` / `PreToolUse` / etc. and produce `user_prompt_submit`, `stop`, `permission`, `ask_user_question`, and `exit_plan_mode` events. This skill produces `peer_send` events. Both happen to be appended to the same `$OCTO_HOOK_FILE` (the channel is already plumbed), but they are independent event sources owned by different subsystems. Don't conflate them.

## Discovering peers — `$OCTO_PEERS`

The `$OCTO_PEERS` environment variable lists who you can message. The format is **tab-separated lines, one peer per line**:

```
name<TAB>description
```

If a peer has no `description`, the line is just `name` with no trailing tab. Empty `$OCTO_PEERS` means you have no peers configured (you are isolated from peer messaging).

Read each peer's `description` to pick the right recipient for a given question. Names are stable identifiers; descriptions tell you what each peer is for.

## The three verbs

All invoked via `bash ~/.claude/skills/octo-peer/peer.sh ...`:

```bash
# Print your peer list (or a friendly empty message).
bash ~/.claude/skills/octo-peer/peer.sh list

# Send a one-shot message — recipient gets the message but is not asked to reply.
bash ~/.claude/skills/octo-peer/peer.sh send <name> '<message>'

# Send a message AND ask the recipient to reply with a summary when done.
bash ~/.claude/skills/octo-peer/peer.sh send-with-callback <name> '<message>'
```

`send-with-callback` is just `send` with an extra "please reply when complete" suffix appended to the message body. The recipient sees the suffix and (if they have this skill installed) honors the convention by sending a peer message back to you.

## Message etiquette

**Messages must be concise and self-contained.** The recipient agent does **not** have access to your conversation history. They see only the bytes you send.

Include enough context so the recipient can act without follow-up questions:

- Relevant file paths and line numbers
- Code snippets or commit SHAs that matter
- The specific question or expected outcome
- Constraints, assumptions, or already-tried approaches

Hard cap is **4 KB per message** — the script rejects anything longer. If you need to share more, summarize the relevant parts rather than dumping logs.

### Bad

```
Can you check that?
```

The recipient has no idea what "that" is.

### Good

```
Please verify that the auth endpoint at src/api/auth.rs:42 correctly rejects
requests with expired tokens. The fix in commit abc123 changed the validation
logic; I want to confirm the rejection still happens.
```

The recipient can act immediately.

## Callback convention

When you finish a task another agent asked you to do (especially via `send-with-callback`), reply to the requester:

```bash
bash ~/.claude/skills/octo-peer/peer.sh send <requester_name> '<concise summary of result>'
```

Keep the summary short — what you found, what you changed, where to look. The requester can ask follow-up questions if they need more detail.

## Reminder pattern

If you sent `send-with-callback` to a peer and have been waiting for their reply, judge from your own conversation context how much time has passed (e.g., "I asked 12 turns ago, the user has moved on to other things"). When that's "long enough" by your judgment, send a polite nudge using plain `send`:

```bash
bash ~/.claude/skills/octo-peer/peer.sh send <name> 'Following up on my earlier request to verify the auth fix — any progress?'
```

There is no daemon-provided liveness signal. Your own context is the timing oracle.

## Error behaviors

- **Unknown peer name**: if `<name>` is not in your `$OCTO_PEERS`, the script exits non-zero with `error: '<name>' is not in your peer list. Available peers:` followed by the peer list. This catches typos and out-of-allowlist names early — re-check `$OCTO_PEERS` and try again with a valid name.
- **Oversized message**: messages over 4 KB are rejected. Shorten before retrying.
- **Missing arguments**: the script prints a `usage:` line and exits non-zero.

## Safety note

Peer messages **bypass Claude Code's permission system**. The recipient receives the message text directly into their CLI input — there is no per-message approval prompt. Treat peer messaging as you would treat directly typing into another agent's terminal. Don't include destructive commands in messages and don't message agents you do not trust.
