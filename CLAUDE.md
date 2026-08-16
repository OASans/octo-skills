# OctoSkills

Shared Claude Code + Codex skills and config, available in ALL projects once installed.

## Repo layout

- `skills/<name>/SKILL.md` — one directory per skill. This is the source of truth.
- `CLAUDE.md` — this file: project memory, and the source of truth for it. `AGENTS.md` is a committed symlink to it, because Claude Code reads only `CLAUDE.md` and Codex reads only `AGENTS.md`. Edit `CLAUDE.md`; never replace the symlink with a copy.
- `.claude/skills/` — this project's own skills (the `knowledge-*` topics written by `/octo-memory`), and the source of truth for them. `.codex/skills` is a committed symlink to this directory, so both agents load one set. Same rule for any project: keep the skills in `.claude/skills/` and symlink `.codex/skills -> ../.claude/skills`.
- `global-settings.json` — shared Claude Code settings (env vars, permissions, hooks). Installs to `~/.claude/settings.json`. It is also the source for Codex's `~/.codex/hooks.json`, but only the `SessionStart` Git Sync hook is derived; Codex status comes from its App Server, so OctoCode activity hooks stay Claude-only.
- `global-CLAUDE.md` — shared user-level memory (global rules applied in every project). Installs to `~/.claude/CLAUDE.md` (Claude Code) and `~/.codex/AGENTS.md` (Codex). Edit this file, not the installed copies.
- `global-codex-config.toml` — complete source of truth for `~/.codex/config.toml`; install.sh overwrites the installed file with it.
- `global-codex-wrapper.sh` — installs to `~/.local/bin/codex`; checks for a Codex update on every launch, keeps the npm package in user-owned `~/.local/share/octo-codex`, and bypasses hook-trust prompts for unattended Remote Control startup.
- `global-codex-rules.rules` — managed Codex command policy. Installs to `~/.codex/rules/default.rules`; `rm` requires user confirmation while other commands use the global defaults.
- `setup/` — machine provisioning (a different job from `install.sh`: these set up the *machine*, `install.sh` sets up the *agents*). Per-platform installers (`install-linux.sh`, `install-mac.sh`, `install-wsl2.sh`, `install-windows.ps1`), the shared `install-components/`, and the SSH grant/accept pair. All machine-specific values — git identity, LAN CIDR, firewall-allowed IPs — live in `setup/.env`, which is **gitignored**; `setup/.env.example` is the committed template and `setup/load-env.sh` loads and validates it. This repo is public: never hardcode an email, IP, or hostname in a setup script — it goes in `.env`. See `setup/README.md`.
- `install.sh` — the single install path for both agents: copies `skills/*` to `~/.claude/skills/` and `~/.codex/skills/`, installs the shared prompts and settings (including the complete Codex config), derives Codex hooks from `global-settings.json`, then installs Node.js+npm and the npm-managed Codex package under `~/.local/share/octo-codex`. On macOS/Linux it also installs OpenAI's standalone package under `$CODEX_HOME/packages/standalone` (default `~/.codex/packages/standalone`). The managed launcher remains `~/.local/bin/codex`. Idempotent — always safe to run directly. Deploy any edit by running `./install.sh`, not by hand-copying files; its Node / Codex-CLI / Swift-LSP / Playwright steps are guarded no-ops when already present, and a failed dependency install warns rather than aborting.

**Hook parity policy:** only Git Sync is shared with Codex. All other hooks stay Claude-only; Codex status comes from the App Server.

## Skills

| Skill | Type | Description |
|-------|------|-------------|
| `/octo-coding-guide-code` | Reference (guide) | Code quality standards. `guide-scope: code` — source, config, build scripts |
| `/octo-coding-guide-rust` | Reference (guide) | Rust-specific conventions. `guide-scope: **/*.rs` |
| `/octo-coding-guide-doc` | Reference (guide) | Documentation bar — compact, self-contained, correct. `guide-scope: **/*.md` |
| `/octo-review` | Workflow | Code review; discovers the `octo-coding-guide-*` family, fans out parallel reviewers over the guides the diff touches, then verifies bug claims before reporting |
| `/octo-commit` | Workflow | Primary commit path: verify the CLAUDE.md workflow was followed, then write a meaningful + compact commit. Never pushes |
| `/octo-blueprint` | Blueprint | Definition of a good AI-agent-native package + a review that grades the current package and returns action items. Explicitly-invoked only; never auto-runs. One parallel sub-agent per `###` blueprint dimension |
| `/octo-memory` | Memory | Capture durable learnings in the short-term buffer |
| `octo-memory-short-term` | Memory (internal) | Append one capture to short-term; invoked by `/octo-memory`, not directly |
| `/octo-memory-long-term` | Memory (manual) | User-only consolidation of short-term captures into long-term topics |

## Skill Relationships

- The `octo-coding-guide-*` skills (`octo-coding-guide-code`, `octo-coding-guide-rust`, `octo-coding-guide-doc`, …) are a **family of scoped review guides**. Each declares a `guide-scope` in frontmatter (which changed files it covers) and holds one or more `##` review domains. Scopes may overlap (a `.rs` change is reviewed by both the coding guide and the Rust guide); Markdown is reviewed by the doc guide only, never the code guides. Keep each guide to its own scope — don't duplicate another guide's rules.
- `/octo-review` is **structure-driven by the guide family**: it discovers every skill with a `guide-scope` frontmatter key, keeps the guides whose scope the diff touches, and fans out read-only reviewer sub-agents over their `##` domains — one per domain on large diffs, one per guide on small ones (criteria partitioned, no overlap). Findings that claim a runtime failure are then checked together by at most one independent verifier sub-agent before reporting. Adding a `##` domain to a guide — or adding a whole new `octo-coding-guide-*` skill — grows the review with no edit to `/octo-review`. Keep `##` domains coherent and their `*Review focus:*` line accurate.
- `/octo-commit` is **structure-driven by CLAUDE.md's `## Workflow`**: it verifies every workflow step (e.g. `/octo-review`, `/octo-memory`) was followed before committing, and stops + hands back if one was skipped. Add a step to the workflow and `/octo-commit` enforces it with no edit here. It is the primary commit path and never pushes.
- `/octo-memory` orchestrates only the internal `octo-memory-short-term` capture skill. `/octo-memory-long-term` is slash-only (`disable-model-invocation: true`): a human invokes consolidation explicitly, and agents never start it automatically.
- `/octo-blueprint` is **explicitly-invoked only** — enforced by the `disable-model-invocation: true` frontmatter flag (the agent can't auto-invoke it; a human runs `/octo-blueprint`), so it is never part of the `## Workflow`. It is self-contained: it carries the package blueprint (organized as `###` dimensions under *The Blueprint*) and the review that turns gaps into action items. Like `/octo-review` it is **structure-driven**, but by its own `###` dimensions rather than the coding guide: each dimension is one grading domain graded by one dedicated sub-agent (partitioned, no overlap), so adding a `###` dimension adds a grading agent with no edit to the steps. Where `/octo-review` grades a code diff against the `octo-coding-guide-*` family, this grades a whole package against the blueprint; dimensions are filled in over time as `###` sections.

## Editing Skills

Edit skills in `skills/<name>/SKILL.md`, then run `./install.sh` to deploy. Do not edit copies in `~/.claude/skills/` — they get overwritten on install.
