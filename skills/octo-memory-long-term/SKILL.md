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
5. **Recurred** (gates **new topics** only): the same knowledge appears in ≥2 independent captures — different capture files, matched by meaning not wording, both in PROMOTE or one in PROMOTE + a twin in CONTEXT. One session deeming something important is a weak signal; the same lesson independently resurfacing is the proof it's load-bearing — and a new topic is the expensive move (another always-loaded description). Two lanes skip this criterion:
   - **User-asked** — heading tagged `(user-asked)`: the user explicitly said to remember it; their judgment outranks recurrence.
   - **Update to an existing topic**: the slot already earned its place; keeping it accurate is maintenance, not promotion.

   Escape hatch (rare): promote a first occurrence only when losing it risks real damage or rework **and** the situation is too rare to recur within the CONTEXT window (e.g. a release-process landmine). Justify it in the report.

Fails 1–4 → it **stays in short-term only**: bug-fix details (commits + tests own those), one-task context, anything obvious from code or doc/, temporary workarounds. Passes 1–4 but not 5 → **hold**: leave the capture file untouched — it resurfaces as CONTEXT on later runs and promotes the day a twin arrives; if it never recurs it silently ages out of the window. That decay is the noise filter working, not a loss.

**Default to merge, not new topic.** Each new topic adds another always-loaded description to the skill-listing budget. Before creating `knowledge-<new-slug>/`, scan existing `knowledge-*` for one the knowledge could extend — even a loose thematic match beats a near-duplicate sibling. New topic only when no existing one is a defensible home.

## What makes a good topic

A topic answers two questions: **what is this** and **how should it change my behavior**. The second separates knowledge from trivia — without concrete "when/how to apply" guidance, don't promote it. (The body structure — What / How to Apply / Key Files — is in the template below.)

Bad (trivia):
> "The scheduler runs every 30 minutes."

Good (actionable):
> "The scheduler runs every 30 minutes via node-cron. Register new data sources in src/scheduler/jobs.ts — don't add standalone cron entries; the scheduler centralizes retry and rate limiting."

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

## Be concise — long-term costs context

Every `knowledge-*` description is always loaded; bodies load on demand. Both cost tokens. Description rules are above (*Writing the description*); for the body:
- Aim for 20–30 lines; 60-line hard cap. Cut hedges, background, restatements.
- File paths and function names beat prose; use bullets where they work.
- **No code blocks** unless the literal text is load-bearing (env var, wire field, escape sequence). A `file.rs:NNN` anchor replaces illustrative snippets.
- Drop session/debugging narrative — the rule is the memory, not the path that found it.
- If a topic cannot be stated concisely, it is probably two topics — split. If two overlap, merge and delete the loser.

## Steps

Consolidation is a **daily** pass. `octo-memory` already gated it via `consolidation-due.sh` and loads this skill **only on DUE** — whether to run today is already decided, so there is no skip-check here. Each script below resolves its own paths from the `origin` remote, so there is nothing to set up. Promotion is criteria-based only — short-term is not loaded into sessions, so there is no "promote what I used this session" step.

#### Phase 1: Promote new knowledge

1. Run `bash ~/.claude/skills/octo-memory/collect-captures.sh`. It emits one blob with two sections: **PROMOTE** (captures in `[last_processed_date, today)` — the exactly-once promote set) and **CONTEXT** (the prior ~5 already-processed capture-days — the recurrence lookback, plus context for writing better topics). The script owns the date range so you never re-derive it by hand — see its header for why the bounds are `>= watermark` and `< today`. If PROMOTE is empty, skip to Phase 2.
2. For each `##` entry in **PROMOTE**, classify against the promotion criteria. Scan PROMOTE and CONTEXT for twins — another independent capture of the same knowledge makes the entry *recurred*. Never promote a CONTEXT entry on its own; when a recurred PROMOTE entry earns a topic, folding supporting detail from its twins into the body is fine.
   - **New topic**: recurred (or an exempt lane) and no existing `knowledge-*` covers it → create `.claude/skills/knowledge-<slug>/SKILL.md`.
   - **Update existing**: extends an existing topic → read that skill, merge, bump `Last verified`.
   - **Hold**: passes criteria 1–4 but hasn't recurred → do nothing; the file stays in the buffer and resurfaces as CONTEXT next run.
   - **Ephemeral**: fails 1–4, no lasting value → skip.
3. **Verify** each new/updated topic with Grep/Glob — referenced files/functions must exist.

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
2. Report **in-session** (not to the file): N entries processed, M new topics, K updates, H held awaiting recurrence, J skipped, L deprecated (with reasons).
