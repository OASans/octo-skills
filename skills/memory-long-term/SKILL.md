---
name: memory-long-term
description: >
  Consolidate short-term memory into long-term. Auto-triggered once per day
  at conversation start, or invoked manually. Promotes valuable knowledge
  and deprecates stale topics.
---

Consolidate short-term memory into long-term. Auto-triggered once per day at conversation start, or invoked manually. This skill both promotes valuable knowledge and deprecates stale topics — keeping the long-term index lean enough to always read in full.

## Promotion criteria — ALL must pass

1. **Reusable across tasks**: Applies to future work, not just the task that generated it.
2. **Not obvious from code**: Reading the code alone wouldn't teach you this. Extension patterns, non-obvious dependencies, tricky ordering constraints qualify.
3. **Still accurate**: Referenced files, functions, and patterns must exist right now. Verify with Grep/Glob before promoting.
4. **Not already documented**: Check doc/, CLAUDE.md, and existing topics. If already captured, update the existing entry instead.

## What gets skipped (stays in short-term only)

- Bug fix details (captured by commits + regression tests)
- Task-specific context (what was tried/failed during one task)
- Information obvious from reading the code or doc/
- Temporary workarounds that will be removed

## Topic quality guide

A good topic answers two questions: **"What is this?"** and **"How should this change my behavior?"**

Each topic should include:
- **What**: The core knowledge — what this is and why it matters.
- **How to apply**: Concrete guidance on when and how future agents should use this knowledge. Without this, a topic is trivia — interesting but not actionable.
- **Key files**: File paths relevant to this topic.

Bad example (trivia):
> "The scheduler runs every 30 minutes."

Good example (actionable):
> "The scheduler runs every 30 minutes via node-cron. When adding new data sources, register them in src/scheduler/jobs.ts — don't create standalone cron entries. The scheduler handles retry logic and rate limiting centrally."

## Topic file format

Each topic file in `ai-memory/long-term/topics/<slug>.md` (max 60 lines):

```
<!-- Last verified: YYYY-MM-DD, commit: <short-hash> -->
<!-- Source: short-term/YYYY-MM-DD.md -->

# <Topic Title>

## What
<Core knowledge — what this is and why it matters>

## How to Apply
<When and how future agents should use this knowledge>

## Key Files
<File paths relevant to this topic>
```

Adapt section names to the topic. No code snippets unless absolutely load-bearing.

## Be concise — memory consumes context

The index is loaded into every session; topic files are read on demand. Both cost context tokens. Write the shortest content that still delivers the knowledge:

- Index description: one short sentence, not a paragraph.
- Topic body: aim well under the 60-line cap — shorter is better. Cut hedges, background, and restatements.
- File paths and function names beat prose. If a bullet list works, use bullets.
- No code snippets unless load-bearing.
- If a topic can't be stated concisely, it's probably two topics — split it.

## Steps

This skill has two independent parts. **Always run Part A.** Run Part B only if today's consolidation hasn't been done yet.

### Part A: Promote session-validated short-term entries (always run)

Short-term entries prove their value by being *used*. If an existing short-term entry (one that was already on disk before this session — NOT one you or `/memory-short-term` just wrote in this session) was consulted during this session and actually shaped the work, that's signal it deserves long-term promotion.

1. Recall which existing short-term entries you read or referenced during this session. If none, skip to Part B.
2. For each such entry:
   - **Filter out newly-added entries**: Entries written during this session stay in short-term — they'll be evaluated during normal consolidation. This part is only for entries that pre-dated the session.
   - Evaluate against the promotion criteria above (reusable / not obvious / still accurate / not already documented).
   - If it passes: promote it now — create a new topic or merge into an existing one. Follow the same topic format and verification rules as Part B.
   - If it fails: leave it in short-term untouched.
3. Report which entries were evaluated and the outcome.

### Part B: Daily consolidation (skip if already done today)

1. Read `ai-memory/long-term/tracker.md` to find `last_processed_date`. Create tracker if missing.
2. **If `last_processed_date` == today, skip Part B entirely** — consolidation has already happened for today. Report "consolidation already done today" and stop.
3. Otherwise, proceed with Phases 1–3 below.

#### Phase 1: Promote new knowledge

1. List files in `ai-memory/short-term/` newer than `last_processed_date`. If none, skip to Phase 2.
2. **Context loading**: Read short-term files from the last 5 days (not just unprocessed ones). Already-processed entries provide context for writing better long-term topics. Only *promote* entries newer than `last_processed_date`.
3. For each unprocessed `##` entry, classify:
   - **New topic**: No existing long-term topic covers this. Create topic file + add index line.
   - **Update existing**: Adds to an existing topic. Read the topic file, merge new info, update `Last verified`.
   - **Ephemeral**: No lasting value. Skip.
4. **Verify** each new/updated topic: Grep/Glob to confirm referenced files and functions still exist.

#### Phase 2: Staleness sweep

Review every existing topic in the index. For each topic:

1. **Read the topic file** and identify its key references (files, functions, patterns).
2. **Grep/Glob** for each key reference. If a reference is gone, briefly search for renames/moves (one grep, not a deep dive).
3. **Check if the pattern is still used**: If the topic describes an approach, verify the codebase still uses it.
4. **Check for redundancy**: If doc/ or CLAUDE.md now covers this knowledge, the topic adds nothing.

**Deprecate** (remove from index + delete topic file) if ANY of these are true:
- **Dead references**: Key files/functions no longer exist and weren't moved — the code was deleted or rewritten.
- **Superseded**: The pattern described has been replaced by a different approach in the codebase.
- **Documented elsewhere**: Knowledge is now fully captured in doc/, CLAUDE.md, or code comments.
- **Absorbed**: Content was merged into another topic during an earlier consolidation.

If a topic is partially stale (some references dead, core knowledge still valid), update it instead of deprecating.

#### Phase 3: Finalize

1. Update `tracker.md`: set `last_processed_date` to today, log what was processed. Keep only the last 10 log entries — delete older ones.
2. **Update the `latest.md` symlink**: point `ai-memory/short-term/latest.md` at the most recent `YYYY-MM-DD.md` file in `ai-memory/short-term/` (by filename, not mtime). Use a **relative** symlink so it survives clones and path moves: `ln -sfn <YYYY-MM-DD>.md ai-memory/short-term/latest.md`. Skip if no dated short-term files exist. CLAUDE.md `@`-references this symlink so a session always has the previous day's memory loaded.
3. Report summary: N entries processed, M new topics, K updates, J skipped, L deprecated (with reasons).

## Long-term operations reference

**Add**: Create `topics/<slug>.md` + add `- [slug](topics/slug.md) -- description` to `index.md` under appropriate category.
**Update**: Merge new info into existing topic file, bump `Last verified` date. Keep under 60 lines.
**Delete**: Remove index line + delete topic file. Log reason in tracker.
**Merge**: Combine related topics into one, delete originals, update index.

## Index format

`ai-memory/long-term/index.md` entries grouped by category:

```
# Long-Term Memory Index

## Patterns
- [slug](topics/slug.md) -- one sentence description

## Architecture
- [slug](topics/slug.md) -- one sentence description

## Debugging
- [slug](topics/slug.md) -- one sentence description

## Workflow
- [slug](topics/slug.md) -- one sentence description
```
