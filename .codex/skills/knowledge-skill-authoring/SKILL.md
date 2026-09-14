---
name: knowledge-skill-authoring
description: >
  Create or edit Codex skills with invocation policies and deploy through install.sh.
---

# Skill Authoring & Deployment

- Edit shared skills in `skills/<name>/SKILL.md` and project knowledge in `.codex/skills/<name>/SKILL.md`; keep `name` equal to the directory name.
- Preserve explicit-only workflows with `policy.allow_implicit_invocation: false` in `agents/openai.yaml`. Keep normal automatic selection for other skills.
- Keep entrypoints compact: purpose and essential constraints, then actionable steps. Route optional detail to references; pass only assigned criteria to each review agent.
- Run `python3 tests/skill_contract_test.py` after edits; exercise model scenarios when changing decision boundaries or model defaults.
- Run `./install.sh` to deploy shared skills and config to `CODEX_HOME` (default `~/.codex`). It mirrors `skills/*` and removes stale installed skill directories; never edit installed copies.

<!-- Last verified: 2026-09-14 -->
