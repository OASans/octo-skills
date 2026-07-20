---
name: knowledge-skill-authoring
description: >
  Authoring/shipping a SKILL.md: `disable-model-invocation: true` = slash-only (agent
  can't auto-invoke); `user-invocable: false` = agent-only/hidden; deploy via ./install.sh.
  Load when creating or editing a skill.
user-invocable: false
---

# Skill Authoring & Deployment (octo-skills)

## What
Two **independent** SKILL.md frontmatter flags decide *who* can invoke a skill (both verified present in the Claude Code binary — grep it to confirm, per `knowledge-claude-code-settings`):

- **`disable-model-invocation: true`** → the **model can't auto-invoke** it. Claude Code filters it out of the model's tool list and blocks it at call time ("user-invocable-only" / `skill_invoke_model_disabled`). A **human can still run it** via `/<name>`. This is THE way to make a slash-only skill; Claude Code's own builtin slash commands use `disableModelInvocation:true + userInvocable:true`.
- **`user-invocable: false`** → hidden from the slash menu, but the **model can still auto-invoke** it. Used for internal sub-skills (`octo-memory-long/short-term`) and `knowledge-*` topics (auto-loaded by description, invoked by name).

They are orthogonal — one gates the human (slash menu), the other gates the agent (model invocation). Defaults: user-invocable true, model-invocation enabled. **There is no global-settings.json knob for this** — it's per-skill frontmatter only. A description that says "never auto-invoke" is a *soft* guard the model can ignore; the flag is the hard one.

## How to Apply
- **Slash-only (user yes, agent no):** set `disable-model-invocation: true`; leave `user-invocable` default. Don't rely on description wording.
- **Internal/orchestrated (agent yes, hidden from user):** set `user-invocable: false`.
- **Validate against the target host:** Codex's bundled `skill-creator/scripts/quick_validate.py` accepts only portable Agent Skills keys (`name`, `description`, `license`, `allowed-tools`, `metadata`). It rejects valid host extensions such as `user-invocable`; an `Unexpected key` result is not proof that Claude Code or Codex rejects the key. Keep platform-specific keys and verify them against the installed agent binary or native loader.
- **Deploy** any skill edit by running `./install.sh` (idempotent). No manifest: it mirror-copies every `skills/*/` → **both** `~/.claude/skills/<name>/` and `~/.codex/skills/<name>/` (Codex uses the same standard) and **prunes** installed skills no longer in `skills/`; it also installs `global-settings.json`, `global-CLAUDE.md` (as Claude `CLAUDE.md` + Codex `AGENTS.md`), and the jq-derived Codex `hooks.json`. Never hand-edit the installed copies — overwritten on install.
- **Body conventions:** open with a one-sentence restatement of the description; action skills use a `## Steps` section; structure-driven skills (e.g. `octo-coding-guide`) declare a `> Structure contract` blockquote where each `##`/`###` is the fan-out unit.

## Key Files
- `skills/<name>/SKILL.md` — source of truth; `name` matches the dir, `description` is a folded `>` block.
- `install.sh` — `install_skills` mirror-copy+prune (dual-target), `install_file`/`write_if_changed` for settings/CLAUDE.md/AGENTS.md/hooks.
- installed binary — resolve via `which claude`, then grep to confirm a flag/setting is real.

<!-- Last verified: 2026-07-20, commit: b8d853c -->
