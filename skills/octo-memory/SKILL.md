---
name: octo-memory
description: >
  Capture reusable, non-obvious project knowledge or an explicit remember request.
  Correct encountered stale knowledge; never start long-term consolidation.
---

Capture knowledge that will change a future decision and would be expensive to rediscover.

## Steps

1. Decide whether anything qualifies: a project-specific constraint, decision rationale, recurring trap, or explicit user request to remember something. If nothing qualifies, stop quietly.
2. Check the relevant code, tests, and authoritative documentation before recording factual claims. Investigate conflicts; a file's existence or a repeated claim does not prove its behavior.
3. If an encountered `knowledge-*` topic is wrong, correct the affected guidance and verify it against its owner. Capture a reusable correction when it meets the same admission bar; leave unrelated topics alone.
4. Write qualifying knowledge to the local capture buffer using the procedure below. Record an independent rediscovery even if an earlier session may have captured it; consolidation uses recurrence as evidence.

## Admission

- State the future decision the knowledge changes, its scope, and any non-obvious reason. Preserve explicit user preferences as preferences rather than inferred implementation facts.
- Skip progress reports, generic coding advice, copied architecture inventories, and facts cheaply recovered from ordinary source or documentation lookup. A concise discovery pointer qualifies when finding the owner itself was difficult.
- Let commits and regression tests own bug histories; capture only the reusable constraint or rationale they do not make easy to discover. Keep exact commands or literals only when their spelling is essential.

## Capture

The buffer is machine-local, shared across checkouts of the same origin repo name, and never loaded into development sessions. Committed long-term topics live at `.claude/skills/knowledge-<slug>/SKILL.md`; their descriptions provide discovery cues and their bodies load when selected.

Set `memory_skill_dir` to the directory containing this skill, then run in Bash from the target repository:

```bash
. "$memory_skill_dir/store-path.sh"
capture_dir="$store/short_term/$(date +%F)"
mkdir -p "$capture_dir"
capture_file="$capture_dir/$(date +%H%M%S)-$$-$RANDOM.md"
(set -C; : > "$capture_file") || exit 1
```

Reuse that file for the rest of this session; append one `## <topic>` heading and a few concise sentences per topic. Include a stable file or symbol pointer for verification, and tag the heading `(user-asked)` when the user explicitly requested the capture.

Do not scan previous sessions' captures during development. Only a human invoking `/octo-memory-long-term` starts consolidation; never run its collection, due-check, or watermark scripts from this skill.
