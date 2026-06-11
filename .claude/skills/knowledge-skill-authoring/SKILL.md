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
- **Deploy** any skill edit by running `./install.sh` (idempotent). No manifest: it mirror-copies every `skills/*/` → `~/.claude/skills/<name>/` and **prunes** installed skills no longer in `skills/`; it also overwrites `~/.claude/settings.json` and `~/.claude/CLAUDE.md`. Never hand-edit the `~/.claude/skills/` copies — overwritten on install.
- **Body conventions:** open with a one-sentence restatement of the description; action skills use a `## Steps` section; structure-driven skills (e.g. `octo-coding-guide`) declare a `> Structure contract` blockquote where each `##`/`###` is the fan-out unit.

## Key Files
- `skills/<name>/SKILL.md` — source of truth; `name` matches the dir, `description` is a folded `>` block.
- `install.sh` — mirror-copy + prune (~L30-50); settings/CLAUDE.md overwrite (~L66-99).
- installed binary — resolve via `which claude`, then grep to confirm a flag/setting is real.

<!-- Last verified: 2026-06-11, commit: 7b1e74b -->
