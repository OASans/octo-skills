---
name: knowledge-octo-blueprint
description: >
  Editing octo-blueprint: dimension→rule→nested-criteria structure, scope, and
  rule-writing conventions. Load before editing skills/octo-blueprint/SKILL.md.
user-invocable: false
---

# Editing the octo-blueprint Skill

## What
`octo-blueprint` defines a good **AI-agent-native package** and reviews a target package against it, emitting prioritized action items. **Explicitly-invoked only** (`disable-model-invocation: true`) — never auto-runs.

`skills/octo-blueprint/SKILL.md` has three parts:
- **Steps** — the review fans out **one read-only Sonnet 4.6 sub-agent per `###` dimension** (parallel, like `/octo-review`): each grades its dimension's rules met/partial/unmet/N-A and drafts an action item per gap; the main agent only merges + prioritizes. Read-only (proposes, never edits).
- **Output** — P0/P1/P2 action-item list.
- **The Blueprint** — the rules, as `###` **dimensions** (e.g. `### CLAUDE.md`), governed by a `> Structure contract` blockquote. Each dimension is graded by its own sub-agent against every rule it holds.

## How to Apply
- **Add a dimension**: new `###` + a `*What good looks like:*` focus line; one coherent concern. A dimension is also the **fan-out unit** — each `###` = one review sub-agent, so split a heavy dimension to add an agent (don't shard rules).
- **Rule format**: top-level bullet (`**Name** — essence`) with checkable criteria as **nested sub-bullets**. Group rules within a dimension when kinds differ (the CLAUDE.md dimension splits *Sections — in order* vs *Whole-file format*).
- **Scope**: governs a package's **project-level `CLAUDE.md`**, NOT the global `~/.claude/CLAUDE.md` (different logic — exempt).
- **Conventions to reuse** (set in the CLAUDE.md dimension): prefer runnable paths over alias layers; hardcode shared **verbatim** boilerplate lines across packages for fixed directives; **verify each claim against the real artifact** (read the script / run `--help`), don't trust the text; name commit by the **action word, never the skill name** (skills may be renamed).
- **Deploy**: edit the source `skills/octo-blueprint/SKILL.md`, then `./install.sh`; never hand-edit `~/.claude/skills/`.

## Key Files
- `skills/octo-blueprint/SKILL.md` — the skill; `### CLAUDE.md` and `### ai_tools/` are the worked examples to copy (both split kinds within one dimension via bold rule-group headers).

<!-- Last verified: 2026-06-11, commit: e12b26c -->
