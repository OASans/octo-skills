# OctoSkills

Shared Claude Code + Codex skills and config, available in ALL projects once installed.

## Repo layout

- `skills/<name>/SKILL.md` — one directory per skill. This is the source of truth.
- `global-settings.json` — shared Claude Code settings (env vars, permissions, hooks). Installs to `~/.claude/settings.json`. Also the source for the git-sync `SessionStart` hook in Codex's `~/.codex/hooks.json` (install `jq`-derives it; the rest of settings.json is JSON/env-specific and doesn't port).
- `codex-hooks.json` — Codex-specific hook overlay merged over the derived git-sync hook. Holds the agent-activity logging (writes each hook payload to `~/.octo-activity/codex/<session_id>.jsonl`), self-sourcing its path/id from the stdin `session_id` because Codex doesn't inject Claude's `OCTO_HOOK_FILE`/`OCTO_AGENT_ID`.
- `global-CLAUDE.md` — shared user-level memory (global rules applied in every project). Installs to `~/.claude/CLAUDE.md` (Claude Code) and `~/.codex/AGENTS.md` (Codex). Edit this file, not the installed copies.
- `global-codex-config.toml` — managed Codex `[tui] status_line`. install.sh merges only that key into `~/.codex/config.toml` (Codex owns that file — theme, trusted projects, hook trust hashes — so it's spliced, never overwritten).
- `codex-migration.md` — reference notes for the Claude Code -> Codex port (feature map, sources).
- `install.sh` — the single install path for both agents: copies `skills/*` to `~/.claude/skills/` and `~/.codex/skills/`, installs `global-CLAUDE.md` as Claude `CLAUDE.md` + Codex `AGENTS.md`, `global-settings.json` as Claude `settings.json` and (jq-derived + `codex-hooks.json` overlay) Codex `hooks.json`, merges the `global-codex-config.toml` status line, then installs Node.js+npm (brew on macOS, the system package manager on Linux) and the Codex CLI (`npm i -g @openai/codex`). Idempotent — always safe to run directly. Deploy any edit by running `./install.sh`, not by hand-copying files; its Node / Codex-CLI / Swift-LSP / Playwright steps are guarded no-ops when those are already present, and a failed dependency install warns rather than aborting.

**Hook parity policy:** any hook added to `global-settings.json` MUST also work in Codex (port it to `codex-hooks.json`, self-sourcing from the stdin payload where Claude used injected env vars) — unless the change explicitly acknowledges why it's Claude-only (e.g. depends on the `Agent`/`Task` tool or a Claude-only env var).

## Skills

| Skill | Type | Description |
|-------|------|-------------|
| `/octo-coding-guide` | Reference (guide) | Code quality standards. `guide-scope: code` — source, config, build scripts |
| `/octo-rust-guide` | Reference (guide) | Rust-specific conventions. `guide-scope: **/*.rs` |
| `/octo-doc-guide` | Reference (guide) | Documentation bar — compact, self-contained, correct. `guide-scope: **/*.md` |
| `/octo-review` | Workflow | Code review; discovers the `octo-*-guide` family, fans out parallel reviewers over the guides the diff touches, then verifies bug claims before reporting |
| `/octo-commit` | Workflow | Primary commit path: verify the CLAUDE.md workflow was followed, then write a meaningful + compact commit. Never pushes |
| `/octo-blueprint` | Blueprint | Definition of a good AI-agent-native package + a review that grades the current package and returns action items. Explicitly-invoked only; never auto-runs. One parallel sub-agent per `###` blueprint dimension |
| `/octo-memory` | Memory | Two-tier memory system orchestrator (short-term + long-term) |
| `octo-memory-short-term` | Memory (internal) | Append one capture to short-term; invoked by `/octo-memory`, not directly |
| `octo-memory-long-term` | Memory (internal) | Consolidate short-term into long-term topics; invoked by `/octo-memory`, not directly |

## Skill Relationships

- The `octo-*-guide` skills (`octo-coding-guide`, `octo-rust-guide`, `octo-doc-guide`, …) are a **family of scoped review guides**. Each declares a `guide-scope` in frontmatter (which changed files it covers) and holds one or more `##` review domains. Scopes may overlap (a `.rs` change is reviewed by both the coding guide and the Rust guide); Markdown is reviewed by the doc guide only, never the code guides. Keep each guide to its own scope — don't duplicate another guide's rules.
- `/octo-review` is **structure-driven by the guide family**: it discovers every skill with a `guide-scope` frontmatter key, keeps the guides whose scope the diff touches, and fans out read-only reviewer sub-agents over their `##` domains — one per domain on large diffs, one per guide on small ones (criteria partitioned, no overlap). Findings that claim a runtime failure are then checked by independent verifier sub-agents before reporting. Adding a `##` domain to a guide — or adding a whole new `octo-*-guide` skill — grows the review with no edit to `/octo-review`. Keep `##` domains coherent and their `*Review focus:*` line accurate.
- `/octo-commit` is **structure-driven by CLAUDE.md's `## Workflow`**: it verifies every workflow step (e.g. `/octo-review`, `/octo-memory`) was followed before committing, and stops + hands back if one was skipped. Add a step to the workflow and `/octo-commit` enforces it with no edit here. It is the primary commit path and never pushes.
- `/octo-memory` orchestrates the internal `octo-memory-short-term` and `octo-memory-long-term` sub-skills (`user-invocable: false` — hidden from the slash menu, invoked only by the orchestrator by name).
- `/octo-blueprint` is **explicitly-invoked only** — enforced by the `disable-model-invocation: true` frontmatter flag (the agent can't auto-invoke it; a human runs `/octo-blueprint`), so it is never part of the `## Workflow`. It is self-contained: it carries the package blueprint (organized as `###` dimensions under *The Blueprint*) and the review that turns gaps into action items. Like `/octo-review` it is **structure-driven**, but by its own `###` dimensions rather than the coding guide: each dimension is one grading domain graded by one dedicated sub-agent (partitioned, no overlap), so adding a `###` dimension adds a grading agent with no edit to the steps. Where `/octo-review` grades a code diff against the `octo-*-guide` family, this grades a whole package against the blueprint; dimensions are filled in over time as `###` sections.

## Editing Skills

Edit skills in `skills/<name>/SKILL.md`, then run `./install.sh` to deploy. Do not edit copies in `~/.claude/skills/` — they get overwritten on install.
