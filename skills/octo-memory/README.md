# octo-memory

Two-tier memory for Claude Code, keyed per repo. Goal: what a session learns once stays learned — without bloating every future session's context.

## The two tiers

**Short-term** — a local capture buffer at `~/.octo-memory/<repo>/short_term/<date>/`. Cheap notes written during sessions (gotchas, decisions, patterns). Never committed, never loaded into context. Machine-local, shared by all checkouts of the repo.

**Long-term** — one topic per `.claude/skills/knowledge-<slug>/SKILL.md`, committed and team-shared. Claude Code always loads each skill's one-line description (the index) and loads a body only when it looks relevant — so a topic costs one line per session, not a page.

## How knowledge flows

1. A session learns something → `octo-memory-short-term` appends it to the buffer. Low bar, write freely.
2. Once a day, when `/octo-memory` runs → `octo-memory-long-term` consolidates: captures that are reusable, still accurate, and **recurred** (independently captured by ≥2 sessions) become `knowledge-*` topics; causal claims must also survive a refutation attempt. Existing topics get swept — stale ones pruned, overlapping ones merged.

Recurrence is the noise filter: one session calling something important is a weak signal; the same lesson resurfacing independently proves it's load-bearing. Captures that never recur silently age out — that's the filter working, not a loss. Exception: "remember this" from the user (`(user-asked)` tag) promotes immediately.

## Usage telemetry

A global hook logs every knowledge-topic load to `~/.octo-memory/<repo>/usage.log`. Consolidation folds that into a small script-owned `usage.md` sidecar next to each topic (`loads`, `last-loaded`) — committed, so disuse is visible in git. A topic not loaded in ~90 days is a candidate to merge into a sibling or demote back to the buffer, where it can re-earn its slot by recurring.

## The pieces

| Piece | Role |
|---|---|
| `octo-memory` (SKILL.md) | Orchestrator — gates, then dispatches capture / consolidation |
| `octo-memory-short-term` | Capture rules — what to write, what to skip |
| `octo-memory-long-term` | Consolidation — promotion criteria, refutation gate, staleness sweep |
| `consolidation-due.sh` | Once-a-day gate (`~/.octo-memory/<repo>/tracker.md`) |
| `collect-captures.sh` | Emits captures to judge: PROMOTE (new) + CONTEXT (recurrence lookback) |
| `usage-stats.sh` | Prints per-topic usage; `--stamp` folds the log into sidecars |
| `mark-consolidated.sh` | Stamps the daily watermark |
| `store-path.sh` | Shared lib — resolves `~/.octo-memory/<repo>` from the origin remote |

Scripts own the mechanics (dates, watermarks, folding); the agent owns only judgment (promote / hold / skip / prune). Full criteria live in the three SKILL.md files.
