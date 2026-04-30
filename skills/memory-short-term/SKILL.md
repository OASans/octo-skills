---
name: memory-short-term
description: >
  Write reusable knowledge to today's short-term memory file. Low barrier —
  write often. This is the capture step; consolidation into long-term happens
  separately via `/memory-long-term`.
---

Write reusable knowledge to today's short-term memory file. Low barrier — write often. This is the capture step; consolidation into long-term happens separately via `/memory-long-term`.

## When to write

- **After spawning subagents**: Findings from Agent tool research are expensive to re-discover. Capture key takeaways before they leave context.
- **After deep exploration**: If you read many files, grepped across the codebase, or used Explore agents — that effort produced knowledge worth preserving.
- **After user teaches you something non-obvious**: If the user corrects you or explains a gotcha, that's exactly the kind of knowledge future conversations need.
- **General rule**: If it took significant work to learn, it belongs in short-term memory.

## What qualifies

- Implementation patterns others would need to replicate or extend
- Non-obvious gotchas or debugging insights
- Architecture decisions and their rationale
- Integration points between modules (how X connects to Y)
- Things that took significant exploration to discover

## What does NOT qualify

- Task-specific progress or status updates
- Obvious code changes self-evident from reading the code
- Things fully captured by commit messages or regression tests
- **Bug-fix post-mortems** — if the load-bearing content is one bug's symptom→cause→fix, the commit + regression test ARE the memory. Don't write the entry just because debugging took effort.
- **Session/subagent narrative** — "Agent B caught X", "rebase conflict resolved by…", "Phase A shipped with…". Describe the rule, not the session that produced it.
- **Code blocks that paraphrase a file:line** — if `file.rs:NNN` points at the canonical version, your snippet is duplication that rots.
- Temporary workarounds that will be removed

## Steps

1. Determine today's date and the target file: `ai_memory/short_term/YYYY-MM-DD.md`
2. If `ai_memory/short_term/` does not exist, create it: `mkdir -p ai_memory/short_term`
3. If today's file does not exist, create it.
4. Append a new entry using this format:

```
## <Topic Title>

<Free-form content. Include file paths, function names, patterns, gotchas.
Keep it concise but complete enough to be useful months later.>
```

5. Each entry starts with `## <topic>` on its own line. No YAML, no metadata. Just knowledge.
6. Multiple entries per day are fine — append to the same file.

## Be concise — memory consumes context

Today's short-term file is `@`-referenced from CLAUDE.md, so every line lands in every future session. **Compress aggressively.** Aim for **≤1 line per fact**. A productive day legitimately produces more entries — that's fine; what's not fine is one entry that bloats to 15 lines because the writer leaned on a four-paragraph template.

### Entry shape

No fixed template. Two natural shapes:

**Pattern / gotcha:**
```
## <topic — specific, not generic>
<One sentence: the knowledge>. <One sentence: how to apply, with `file.rs:NNN` anchor>.
<Optional one-line **Rule:** if it generalizes>
```

**Invariant / constraint:**
```
## <X is Y, not Z>
<One sentence stating the invariant, with `file.rs:NNN` anchor>. <One sentence on what depends on it.>
```

Skip the **Symptom: / Cause: / Fix:** scaffold — it implies four paragraphs and reliably produces bloat. If you can't compress to ~5 lines, ask whether the entry is a bug-fix post-mortem in disguise (the commit is the memory; don't write it).

### Rules

- Lead with the knowledge, not preamble ("X does Y when Z" — not "I learned that…").
- **No code blocks.** A `file.rs:NNN` anchor replaces them. Sole exceptions: env-var names, exact wire field names, escape sequences whose literal characters matter. Yaml/bash/Swift/Rust illustrative snippets — all out.
- File paths: full path once per entry at first mention, short anchor (`mouse.rs:320`) after.
- Drop narrative ("we tried…, then realized…", "Agent B traced…", "Phase A shipped with…") — keep only the conclusion.
- Drop framing-word subsections: **Symptom:**, **Cause:**, **Fix:**, **Subtleties:**, **Verified on:**, **Drive-by:**, **Tests:**. Fold any load-bearing detail into prose; drop the rest. One `**Rule:**` line at the end is fine; don't sprinkle three.
- No restatement of the task that produced the memory.
- **Merge, don't multiply**: if the new insight extends a topic already written today, edit that entry instead of appending a new `##` header. Three entries on the same streaming-Whisper subsystem belong under one heading.

### Before / after

Before (typical bloat, ~12 lines with subsections):
> ## Resync windows must NOT advance the change timestamp — or they just shift the symptom
> **Symptom:** code-review subagent caught a secondary bug in the first cut of the resync fix: `poll_agents` was unconditionally setting `agent.detection.last_content_change = now` whenever `result.new_content.is_some()`. During the resync window the SIGWINCH redraw makes `new_content` Some, so the timestamp got reset every poll — meaning when the window expired, the idle-drift timer needed another full `idle_threshold` (1 s) of stable content before flipping to Idle. The spurious-Working flash moved from "during the 1.5 s window" to "during the 1.5 s window + 1 s after". Suppression theatre.
> **Fix:** `apply_content_change(detection, new_content, in_resync, now)` (`loop_impl/mod.rs`) replaces `last_content` always but only advances `last_content_change` when `!in_resync`. Sibling regression test `test_apply_content_change_in_resync_preserves_timestamp` exercises the path. Call site in `poll_agents` reduces to one helper invocation.
> **Rule:** when adding a "ignore this signal" window to a detector, audit every state-update side-effect that runs alongside the detection — not just the state flip you wanted to suppress…

After (3 lines, same knowledge):
> ## Detector suppression windows must also gate the bookkeeping side-effects
> A window that suppresses the state flip but still advances `last_change` timers just shifts the symptom in time. `loop_impl/mod.rs::apply_content_change` only advances the timer when `!in_resync`.
> **Rule:** when adding "ignore this signal" to a detector, audit every side-effect on the same path, not just the flip you wanted to suppress.

The bug story (which subagent caught it, what the original first-cut looked like) lives in the commit; the entry keeps only the rule + the anchor.
