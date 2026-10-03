# OctoSkills

Codex skills and config, available in ALL projects once installed.

## Repo layout

- `skills/<name>/SKILL.md` — one directory per skill. This is the source of truth.
- `AGENTS.md` — project instructions; edit this regular file directly.
- `.codex/skills/` — project knowledge skills maintained by the memory workflows; this is a real directory and the source of truth.
- `global-codex-hooks.json` — Codex SessionStart Git Sync hook; installs directly to `$CODEX_HOME/hooks.json`. Codex status comes from its App Server.
- `global-AGENTS.md` — global instructions; installs to `$CODEX_HOME/AGENTS.md`. Edit the source, not the installed copy.
- `global-codex-config.toml` — shared Codex defaults; `scripts/render_codex_config.py` preserves host-local project and hook trust from the installed config. `install.sh` honors `CODEX_HOME` (default `~/.codex`); Python 3.11+ is required for TOML parsing.
- `global-codex-rules.rules` — managed Codex command policy. Installs to `$CODEX_HOME/rules/default.rules` (default `~/.codex/rules/default.rules`); `rm` requires user confirmation while other commands use the global defaults.
- `setup/` — machine provisioning (a different job from `install.sh`: these set up the *machine*, `install.sh` sets up the *agents*). Linux/macOS installers (`install-linux.sh`, `install-mac.sh`), the shared `install-components/`, and the SSH grant/accept pair. All machine-specific values — git identity, LAN CIDR, firewall-allowed IPs — live in `setup/.env`, which is **gitignored**; `setup/.env.example` is the committed template and `setup/load-env.sh` loads and validates it. This repo is public: never hardcode an email, IP, or hostname in a setup script — it goes in `.env`. See `setup/README.md`.
- `install.sh` — deploys `skills/*`, global instructions, hooks, config, rules, and review agents to `CODEX_HOME` (default `~/.codex`), and installs OpenAI's standalone Codex package. `~/.local/bin/codex` points directly to the official executable. Normal installs preserve the running daemon; `--restart` updates and restarts it.

## Skills

| Skill | Type | Description |
|-------|------|-------------|
| `/octo-coding-guide-code` | Reference (guide) | Common rules and language-specific instructions in `languages/` |
| `/octo-review` | Workflow | One holistic reviewer when independent review is needed; one verifier for concrete failure claims |
| `/octo-commit` | Workflow | Primary commit path: verify the AGENTS.md workflow was followed, then write a meaningful + compact commit; pushes only when authorized |
| `/octo-simplify` | Audit (on request) | Full simplification audit through browser GPT-6 Pro; coverage and ranked cleanup plan, no implementation |
| `/octo-memory` | Memory (manual) | Audit transcripts through browser Pro and publish verified topics |

## Skill Relationships

- `octo-coding-guide-code` is the single coding-guide entrypoint, including documentation rules. Its `languages/` directory holds language-specific instructions, starting with Rust.
- `/octo-review` defaults to one reviewer across the change and relevant guidance, with at most one independent verifier for failure claims. Global instructions own review triggers and freshness.
- `/octo-commit` enforces the merged AGENTS.md workflow, completes missing authorized steps, and checks that required review/checks cover the current change. It never pushes without user authorization.
- `/octo-memory` owns explicitly requested transcript audits, global progress tracking, and verified topic publication. Existing knowledge remains available during ordinary tasks.
- `/octo-simplify` audits the whole requested scope through `/tool-chatgpt-analysis`; it records coverage and proposes cleanup without implementing it. Browser GPT-6 Pro is its only execution route.

## Editing Skills

Edit skills in `skills/<name>/SKILL.md`, then run `./install.sh` to deploy. Do not edit copies in `~/.codex/skills/` — they get overwritten on install.

## Validation

- Tests live beside their scripts. Run the affected `*_test.py` files directly with Python. For all Python tests: `for test in scripts/*_test.py skills/*/scripts/*_test.py; do python3 "$test" || exit; done`.
- For skill/prompt changes, check skill names against their directories, referenced paths, and changed invocation policies directly. Model/prompt comparisons follow the common coding guide's temporary-work rule.
- Check shell syntax with `bash -n` for changed scripts and parse changed JSON/TOML/YAML. Rerun only affected checks after fixes.
