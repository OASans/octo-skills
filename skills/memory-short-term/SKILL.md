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
