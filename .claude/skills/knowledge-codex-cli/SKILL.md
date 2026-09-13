---
name: knowledge-codex-cli
description: >
  Configure or troubleshoot the shared Codex installation, Git Sync hooks, and native app-server ownership.
user-invocable: false
---

# Shared Codex Installation

- Codex uses `AGENTS.md` for instructions and `config.toml` for settings; Claude Code's JSON settings are not interchangeable with TOML. The installer honors `CODEX_HOME`, defaulting to `~/.codex`.
- Only Git Sync is shared with Codex: `install.sh` derives `hooks.json` as `{"hooks":{"SessionStart":…}}` from `global-settings.json`. Activity, model-selection, and skill-logging hooks remain Claude-only; Codex status comes from its App Server.
- Hook trust is bound to the exact hook definition and path. The installer preserves this host's project trust and `hooks.state` from its existing config; it never copies another machine's approvals or approves changed hooks.
- `global-codex-config.toml` owns shared defaults; `scripts/render_codex_config.py` preserves local trust when rendering them. Python 3.11+ supplies the TOML parser; older Python needs `tomli` or pip's bundled parser.
- On macOS/Linux, `install.sh` updates OpenAI's standalone package and points `~/.local/bin/codex` directly to its executable. The launcher does not modify arguments or bypass hook trust.
- Let Codex's native daemon own Remote Control; do not add a second systemd app-server with the same `CODEX_HOME`. The installer removes obsolete Octo services only after a replacement native server is available.
- Config reload updates the running server's configuration; verify effective model selection in a new session rather than assuming existing sessions change models.

<!-- Last verified: 2026-09-13 -->
