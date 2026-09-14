# Project memory

`octo-memory` captures project-specific knowledge that changes future decisions and is expensive to rediscover. It also corrects stale topics encountered during work; ordinary tasks with no qualifying discovery need no memory step.

## Storage and lifecycle

- Captures live at `~/.octo-memory/<repo>/short_term/<date>/`, keyed by the origin repository name. They are machine-local, shared across checkouts, and unavailable to development sessions.
- Long-term topics live in committed `.codex/skills/knowledge-*/SKILL.md` files. Descriptions are discovery cues; selected bodies provide concise constraints, rationale, and source pointers.
- A human explicitly invokes `octo-memory-long-term` to promote captures and maintain topics, at most once per day. New topics normally require independent recurrence; the skill owns the exceptions and verification criteria.

## Components

| Component | Responsibility |
|---|---|
| `octo-memory/SKILL.md` | Admission, capture, and encountered corrections |
| `octo-memory-long-term/SKILL.md` | Manual promotion and maintenance |
| `store-path.sh` | Resolve the per-repository local store |
| `consolidation-due.sh` | Deduplicate manual runs for the day |
| `collect-captures.sh` | Select new captures and recurrence context |
| `mark-consolidated.sh` | Advance the completed-run watermark |

The former capture sub-skill is folded into `octo-memory`. Usage-based retention, the load hook, and `usage-stats.sh` are retired because their counts missed Codex and direct reads; existing machine-local usage logs may remain inert, and project `usage.md` sidecars can be removed.
