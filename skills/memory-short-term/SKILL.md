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
- Bug fix details (the fix is in the code, the context is in the commit)
- Temporary workarounds that will be removed

## Steps

1. Determine today's date and the target file: `ai-memory/short-term/YYYY-MM-DD.md`
2. If `ai-memory/short-term/` does not exist, create it: `mkdir -p ai-memory/short-term`
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

Every entry gets loaded into future sessions. Today's short-term file is `@`-referenced from CLAUDE.md, so every line here is on the hot path. Aim for **≤10 lines per entry**, **≤1 line per fact**.

### Entry shape

```
## <Topic — specific, not generic>
**Symptom/context:** one line.
**Cause:** one line.
**Fix:** one line, with `file.rs:line` anchor.
**Rule:** one line (only if the lesson generalizes beyond this case).
```

Optional extra bullets for non-obvious detail. No code blocks unless a literal string must be preserved (key name, escape sequence, wire field). Skip sections that don't apply — don't pad.

### Rules

- Lead with the knowledge, not preamble ("X does Y when Z" — not "I learned that…").
- File paths: full path once per entry at first mention, short anchor (`mouse.rs:320`) after.
- Drop framing words: **Rule:**, **Generalizable:**, **Takeaway:**, **Lesson:**, **Net effect:** — the reader already knows they're reading rules. One `**Rule:**` line at the end is fine; don't sprinkle three.
- Drop narrative ("we tried…, then realized…") — keep only the conclusion.
- No restatement of the task that produced the memory.
- No code block if a file:line + one-line description conveys the same info.
- **Merge, don't multiply**: if the new insight extends a topic already written today, edit that entry instead of appending a new `##` header. Three entries about the same tmux-atomic-chain pattern belong under one heading.

### Before / after

Before (8 lines of prose):
> `MouseEventKind` exposes only `Down`, `Up`, `Drag`, `Moved`, `ScrollUp`, `ScrollDown` — no `DoubleClick`, no click-count field. If you need double-click detection (e.g. double-click an agent panel to zoom), implement it in software: Store `Option<PendingClick { target, at: Instant }>` on app state…

After (3 lines):
> ## crossterm 0.28 has no native double-click
> Detect in software: store `Option<PendingClick { target, at }>`, compare on next click against 400ms threshold. Clear pending on any non-matching click target.
> Pattern: `src/dashboard_ui_process/main_thread/handle_events/mouse.rs`. Keep detector pure (`(pending, target, now, threshold) -> bool`) for tests.
