---
name: octo-memory-long-term
description: >
  Sub-step of `/octo-memory`: the daily consolidation pass that promotes
  short-term captures into `knowledge-*` skills and prunes stale ones. Gated
  and driven by the orchestrator.
user-invocable: false
---

Consolidate short-term memory into long-term. `/octo-memory` runs this once per day via its consolidation gate (`consolidation-due.sh`); it is not invoked on its own. This skill both promotes valuable knowledge and deprecates stale topics — keeping the auto-loaded knowledge set lean.

Long-term lives as **project skills**: one topic per `.claude/skills/knowledge-<slug>/SKILL.md`, committed to the repo and shared with the team. Claude Code auto-loads every skill's `name` + `description` each session (that is the always-on "index") and loads a topic body only when the skill is invoked. There is **no** `index.md` and **no** CLAUDE.md `@`-import — the descriptions are the index.

**Hot-path note**: every `knowledge-*` description is always in context (it shares the skill-listing budget), so each topic costs context every session. Bodies load on demand. Optimise for: tight descriptions, fewer-but-better topics, merge-into-existing over new-topic.

## Promotion criteria — ALL must pass

1. **Reusable across tasks**: Applies to future work, not just the task that generated it.
2. **Not obvious from code**: Reading the code alone wouldn't teach you this. Extension patterns, non-obvious dependencies, tricky ordering constraints qualify.
3. **Still accurate**: Referenced files, functions, and patterns must exist right now. Verify with Grep/Glob before promoting.
4. **Not already documented**: Check doc/, CLAUDE.md, and existing `knowledge-*` skills. If already captured, update the existing one instead.

**Default to merge, not new topic.** Each new topic adds another always-loaded description to the skill-listing budget. Before creating `knowledge-<new-slug>/`, scan existing `knowledge-*` for one the knowledge could extend — even a loose thematic match beats a near-duplicate sibling. New topic only when no existing one is a defensible home.

## What gets skipped (stays in short-term only)

- Bug fix details (captured by commits + regression tests)
- Task-specific context (what was tried/failed during one task)
- Information obvious from reading the code or doc/
- Temporary workarounds that will be removed

## Topic quality guide

A good topic answers two questions: **"What is this?"** and **"How should this change my behavior?"**

Each topic should include:
- **What**: The core knowledge — what this is and why it matters.
- **How to apply**: Concrete guidance on when and how future agents should use this knowledge. Without this, a topic is trivia.
- **Key files**: File paths relevant to this topic.

Bad example (trivia):
> "The scheduler runs every 30 minutes."

Good example (actionable):
> "The scheduler runs every 30 minutes via node-cron. When adding new data sources, register them in src/scheduler/jobs.ts — don't create standalone cron entries. The scheduler handles retry logic and rate limiting centrally."

## Topic = a knowledge skill

Each topic is a skill at `.claude/skills/knowledge-<slug>/SKILL.md` (project-level, committed):

```
---
name: knowledge-<slug>
description: >
  <trigger sentence — front-loaded keywords + when to load this; <=150 chars>
user-invocable: false
---

# <Topic Title>

## What
<Core knowledge — what this is and why it matters>

## How to Apply
<When and how future agents should use this knowledge>

## Key Files
<File paths relevant to this topic>

<!-- Last verified: YYYY-MM-DD, commit: <short-hash> -->
```

- `user-invocable: false` → Claude auto-loads it when relevant; it stays out of the user's slash menu.
- The `description` is **both the trigger and the index line** — it is all the model sees until the skill loads. Use a `>` folded block (handles colons).
- Body ≤60 lines. No code snippets unless the literal text is load-bearing; a `file.rs:NNN` anchor replaces them.

### Writing the description (critical)

The description is fuzzy-matched to decide whether to load the topic, and it is always in context. So:
- **Front-load specific trigger keywords**, not generic framing. GOOD: "JSON logging — add per-agent log targets, span fields, new sinks; load when touching logging/tracing." BAD: "Helpful information about logging."
- Keep it **≤150 chars**.
- Add an **exclusion** when topics are adjacent: "...for log routing, NOT log querying (see knowledge-log-queries)."

## Be concise — descriptions cost context

Every `knowledge-*` description is always loaded; bodies load on demand. Both cost tokens.
- **Description**: one tight trigger sentence (≤150 chars). It is on the hot path of every session.
- **Body**: aim for 20–30 lines; 60-line hard cap. Cut hedges, background, restatements.
- File paths and function names beat prose; use bullets where they work.
- **No code blocks** unless the literal text is load-bearing (env var, wire field, escape sequence). A `file.rs:NNN` anchor replaces illustrative snippets.
- Drop session/debugging narrative — the rule is the memory, not the path that found it.
- If a topic cannot be stated concisely, it is probably two topics — split. If two overlap, merge and delete the loser.

## Steps

Consolidation is a **daily** pass, gated per machine. Promotion is criteria-based only — short-term is no longer loaded into sessions, so there is no "promote what I used this session" step.

### Resolve paths

```
url=$(git remote get-url origin 2>/dev/null)
key=${url##*/}; key=${key%.git}
[ -n "$key" ] || { echo "ERROR: no git 'origin' remote; set one so memory can be keyed per project"; exit 1; }
st="$HOME/.octo-memory/$key/short_term"      # local short-term buffer (read-only here)
flag="$HOME/.octo-memory/$key/tracker.md"    # last_processed_date — per machine
```

### Gate (skip if already done today)

1. Read `last_processed_date` from `$flag` (create `$flag` if missing).
2. **If `last_processed_date` == today, stop** — consolidation already ran on this machine today. Report "already done today".
3. Otherwise proceed.

#### Phase 1: Promote new knowledge

1. List capture files under `$st/` in date folders newer than `last_processed_date` (`$st/YYYY-MM-DD/*.md`). If none, skip to Phase 2.
2. **Context loading**: read the last ~5 days of captures (already-processed ones give context for better topics). Only *promote* entries newer than `last_processed_date`.
3. For each `##` entry, classify against the promotion criteria:
   - **New topic**: no existing `knowledge-*` covers it → create `.claude/skills/knowledge-<slug>/SKILL.md`.
   - **Update existing**: extends an existing topic → read that skill, merge, bump `Last verified`.
   - **Ephemeral**: no lasting value → skip.
4. **Verify** each new/updated topic with Grep/Glob — referenced files/functions must exist.

#### Phase 2: Staleness sweep

Review every existing `.claude/skills/knowledge-*` skill:
1. Read the skill body; identify its key references (files, functions, patterns).
2. Grep/Glob each reference. If gone, one quick search for a rename/move.
3. Check the pattern is still used, and that it is not now covered by doc/ or CLAUDE.md.

**Deprecate** (delete the `knowledge-<slug>/` folder) if ANY hold:
- **Dead references**: key files/functions gone and not moved.
- **Superseded**: the pattern was replaced.
- **Documented elsewhere**: now fully covered in doc/, CLAUDE.md, or code.
- **Absorbed**: merged into another topic.

If partially stale (some refs dead, core still valid), update instead of deleting.

#### Phase 3: Finalize

1. Stamp the watermark: `bash ~/.claude/skills/octo-memory/mark-consolidated.sh` — it writes `last_processed_date: <today>` (the file's only line). No model writes the tracker by hand.
2. Report **in-session** (not to the file): N entries processed, M new topics, K updates, J skipped, L deprecated (with reasons).

## Long-term operations reference

- **Add**: create `.claude/skills/knowledge-<slug>/SKILL.md` (frontmatter + body). Its description joins the auto-loaded index automatically — nothing else to edit.
- **Update**: merge into the existing skill body, bump `Last verified`. Keep ≤60 lines.
- **Delete**: remove the `knowledge-<slug>/` folder.
- **Merge**: fold related topics into one skill, delete the others.
