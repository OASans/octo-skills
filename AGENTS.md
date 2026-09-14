# OctoSkills

Codex skills and config, available in ALL projects once installed.

## Repo layout

- `skills/<name>/SKILL.md` — one directory per skill. This is the source of truth.
- `AGENTS.md` — project instructions; edit this regular file directly.
- `.codex/skills/` — project knowledge skills maintained by the memory workflows; this is a real directory and the source of truth.
- `global-codex-hooks.json` — Codex SessionStart Git Sync hook; installs directly to `$CODEX_HOME/hooks.json`. Codex status comes from its App Server.
- `global-AGENTS.md` — global instructions; installs to `$CODEX_HOME/AGENTS.md`. Edit the source, not the installed copy.
- `global-codex-config.toml` — shared Codex defaults; `scripts/render_codex_config.py` preserves host-local project and hook trust from the installed config. `install.sh` honors `CODEX_HOME` (default `~/.codex`); Python 3.11+ or an older Python with `tomli`/pip supplies TOML parsing.
- `global-codex-rules.rules` — managed Codex command policy. Installs to `~/.codex/rules/default.rules`; `rm` requires user confirmation while other commands use the global defaults.
- `setup/` — machine provisioning (a different job from `install.sh`: these set up the *machine*, `install.sh` sets up the *agents*). Per-platform installers (`install-linux.sh`, `install-mac.sh`, `install-wsl2.sh`, `install-windows.ps1`), the shared `install-components/`, and the SSH grant/accept pair. All machine-specific values — git identity, LAN CIDR, firewall-allowed IPs — live in `setup/.env`, which is **gitignored**; `setup/.env.example` is the committed template and `setup/load-env.sh` loads and validates it. This repo is public: never hardcode an email, IP, or hostname in a setup script — it goes in `.env`. See `setup/README.md`.
- `install.sh` — deploys `skills/*`, global instructions, hooks, config, rules, and review agents to `CODEX_HOME` (default `~/.codex`), and installs OpenAI's standalone Codex package. `~/.local/bin/codex` points directly to the official executable. Normal installs preserve the running daemon; `--restart` updates and restarts it.

## Skills

| Skill | Type | Description |
|-------|------|-------------|
| `/octo-coding-guide-code` | Reference (guide) | Code quality standards. `guide-scope: code` — source, config, build scripts |
| `/octo-coding-guide-rust` | Reference (guide) | Rust-specific conventions. `guide-scope: **/*.rs` |
| `/octo-coding-guide-doc` | Reference (guide) | Documentation bar — compact, self-contained, correct. `guide-scope: **/*.md` |
| `/octo-review` | Workflow | Code review; discovers the `octo-coding-guide-*` family, fans out parallel reviewers over the guides the diff touches, then verifies bug claims before reporting |
| `/octo-commit` | Workflow | Primary commit path: verify the AGENTS.md workflow was followed, then write a meaningful + compact commit. Never pushes |
| `/octo-simplify` | Workflow (on request) | Simplify code for the same behavior: fans out finders over its `###` angles, verifies removal claims, applies safe changes under the build/test gate, proposes risky ones for approval. Only on explicit user request; never auto-runs |
| `/octo-blueprint` | Blueprint | Definition of a good AI-agent-native package + a review that grades the current package and returns action items. Explicitly-invoked only; never auto-runs. One parallel sub-agent per `###` blueprint dimension |
| `/octo-memory` | Memory | Capture durable learnings in the short-term buffer |
| `/octo-memory-long-term` | Memory (manual) | User-only consolidation of short-term captures into long-term topics |

## Skill Relationships

- The `octo-coding-guide-*` skills (`octo-coding-guide-code`, `octo-coding-guide-rust`, `octo-coding-guide-doc`, …) are a **family of scoped review guides**. Each declares a `guide-scope` in frontmatter (which changed files it covers) and holds one or more `##` review domains. Scopes may overlap (a `.rs` change is reviewed by both the coding guide and the Rust guide); Markdown is reviewed by the doc guide only, never the code guides. Keep each guide to its own scope — don't duplicate another guide's rules.
- `/octo-review` is **structure-driven by the guide family**: it discovers every skill with a `guide-scope` frontmatter key, keeps the guides whose scope the diff touches, and fans out read-only reviewer sub-agents over their `##` domains — one per domain on large diffs, one per guide on small ones (criteria partitioned, no overlap). Findings that claim a runtime failure are then checked together by at most one independent verifier sub-agent before reporting. Adding a `##` domain to a guide — or adding a whole new `octo-coding-guide-*` skill — grows the review with no edit to `/octo-review`. Keep `##` domains coherent and their `*Review focus:*` line accurate.
- `/octo-commit` is **structure-driven by AGENTS.md's `## Workflow`**: it verifies every workflow step (e.g. `/octo-review`, `/octo-memory`) was followed before committing, and completes missing authorized steps before committing. Add a step to the workflow and `/octo-commit` enforces it with no edit here. It is the primary commit path and never pushes.
- `/octo-memory` owns selective capture and corrections to encountered stale topics. `/octo-memory-long-term` owns recurrence-based promotion and maintenance, and runs only when explicitly invoked by a human.
- `/octo-simplify` is the **fixing counterpart of `/octo-review`**: both judge against the `octo-coding-guide-*` family, but review reports and simplify edits. Because it deletes code it runs only on explicit user request (stated in its description, so an agent can invoke it when asked) and stays out of the `## Workflow`; its output is reviewed by `/octo-review` like any other change. Structure-driven by its own `###` angles — one finder each on a large target, one finder for all on a small one.
- `/octo-blueprint` is **explicitly-invoked only** — configured by `agents/openai.yaml` policy (the agent can't auto-invoke it; a human runs `/octo-blueprint`), so it is never part of the `## Workflow`. Its entrypoint carries the workflow and routes graders to `references/blueprint.md`, organized as `###` dimensions. Like `/octo-review` it is **structure-driven**, but by its own `###` dimensions rather than the coding guide: each dimension is one grading domain graded by one dedicated sub-agent (partitioned, no overlap), so adding a `###` dimension adds a grading agent with no edit to the steps. Where `/octo-review` grades a code diff against the `octo-coding-guide-*` family, this grades a whole package against the blueprint; dimensions are filled in over time as `###` sections.

## Editing Skills

Edit skills in `skills/<name>/SKILL.md`, then run `./install.sh` to deploy. Do not edit copies in `~/.codex/skills/` — they get overwritten on install.

## Validation

- For installer/config changes, run `python3 -m unittest discover -s tests -p '*_test.py'` and `bash tests/install_codex_config_test.sh`; the installer test uses disposable local fixtures and controlled external commands.
- For skill/prompt changes, run `python3 tests/skill_contract_test.py`; run the opt-in model scenarios in `evals/` when changing decision boundaries or model defaults.
- Check shell syntax with `bash -n` for changed scripts and parse changed JSON/TOML/YAML. Rerun only affected checks after fixes.
