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
- On macOS/Linux, `install.sh` provisions OpenAI's standalone package on a fresh installation. Existing installations require `--restart` for package updates and daemon management; normal installs preserve the runtime. `~/.local/bin/codex` points directly to the official executable.
- Let Codex's native daemon own Remote Control; do not add a second systemd app-server with the same `CODEX_HOME`. The installer removes obsolete Octo services only after a replacement native server is available.
- Do not live-reload configuration during installation: it can change permissions in active threads. Normal installs write configuration to disk; verify effective settings after Codex next loads them.

<!-- Last verified: 2026-09-14 -->
