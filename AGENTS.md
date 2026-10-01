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
| `/octo-coding-guide-code` | Reference (guide) | Common implementation, verification, and documentation rules. `guide-scope: all` |
| `/octo-coding-guide-rust` | Reference (guide) | Rust-specific conventions. `guide-scope: **/*.rs` |
| `/octo-review` | Workflow | One holistic reviewer when independent review is needed; one verifier for concrete failure claims |
| `/octo-commit` | Workflow | Primary commit path: verify the AGENTS.md workflow was followed, then write a meaningful + compact commit. Never pushes |
| `/octo-simplify` | Workflow (on request) | Simplify code for the same behavior using bounded file groups, verified findings, and relevant checks. Only on explicit user request |
| `/octo-blueprint` | Blueprint | Definition of a good AI-agent-native package + a review that grades the current package and returns action items. Explicitly-invoked only; never auto-runs. One parallel sub-agent per `###` blueprint dimension |
| `/octo-memory` | Memory (manual) | Audit transcripts through browser Pro and publish verified topics |
| `/octo-memory-long-term` | Memory (manual) | Compatibility entrypoint for the manual memory audit |

## Skill Relationships

- `octo-coding-guide-code` is the common entrypoint, including documentation rules. Specialist guides such as `octo-coding-guide-rust` add guidance only for their `guide-scope`; headings never determine agent count.
- `/octo-review` defaults to one reviewer across the change and relevant guidance, with at most one independent verifier for failure claims. Global instructions own review triggers and freshness.
- `/octo-commit` enforces the merged AGENTS.md workflow, completes missing authorized steps, and checks that required review/checks cover the current change. It never pushes without user authorization.
- `/octo-memory` owns explicitly requested transcript audits, global progress tracking, and verified topic publication. Existing knowledge remains available during ordinary tasks; `/octo-memory-long-term` delegates manual audits to it.
- `/octo-simplify` edits only on explicit request, using the same quality guidance as review. Its own workflow partitions work by bounded file groups; it is not an automatic development step.
- `/octo-blueprint` is explicit-only via `agents/openai.yaml`. It grades a whole package against `references/blueprint.md`, with one agent per `###` dimension; it is not part of the development workflow.

## Editing Skills

Edit skills in `skills/<name>/SKILL.md`, then run `./install.sh` to deploy. Do not edit copies in `~/.codex/skills/` — they get overwritten on install.

## Validation

- For installer/config changes, run `python3 -m unittest discover -s tests -p '*_test.py'` and `bash tests/install_codex_config_test.sh`; the installer test uses disposable local fixtures and controlled external commands.
- For skill/prompt changes, run `python3 tests/skill_contract_test.py`; run the opt-in model scenarios in `evals/` when changing decision boundaries or model defaults.
- Check shell syntax with `bash -n` for changed scripts and parse changed JSON/TOML/YAML. Rerun only affected checks after fixes.
