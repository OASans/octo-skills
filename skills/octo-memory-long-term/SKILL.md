---
name: octo-memory-long-term
description: >
  Manually consolidate short-term captures into verified knowledge topics and
  prune stale or duplicated guidance. Run only when the user explicitly invokes it.
disable-model-invocation: true
---

Consolidate only when a human explicitly invokes `/octo-memory-long-term`; never start from capture, startup, workflow completion, or inferred need.

## Steps

Resolve `memory_dir` to the sibling `octo-memory` skill directory and run its scripts from the target repository. Scripts own the date ranges and watermark; leave capture files and tracker contents unchanged by hand.

1. Run `bash "$memory_dir/consolidation-due.sh"`. On DONE (exit 0), stop; on DUE (exit 1), continue; on any other status, resolve the error before proceeding.
2. Run `bash "$memory_dir/collect-captures.sh"`. Classify entries in PROMOTE; use CONTEXT only as supporting evidence for a PROMOTE entry, never as a promotion source by itself.
3. Apply the promotion criteria below, merging into an existing topic when the same task would need both pieces of knowledge. Hold unconfirmed or not-yet-recurred entries without editing their capture files; skip entries with no durable value.
4. Review existing topics for stale or duplicated guidance during this explicitly requested maintenance pass. Verify affected claims against their actual owners; update partially stale topics, merge overlapping rules, and remove guidance that is superseded or cheaply recoverable from its authoritative source.
5. After all changes are verified, run `bash "$memory_dir/mark-consolidated.sh"`. Report counts of promoted, updated, held, skipped, refuted, merged, and removed topics, with reasons for removals.

## Promotion criteria

- Require a concrete future use, meaningful rediscovery cost, current factual support, and a clear home. Keep undocumented rationale and hard-to-find constraints; avoid copied implementation summaries.
- Verify behavior in the implementation and relevant tests, plus authoritative documentation where needed. When sources disagree, investigate before asserting a rule; existence checks alone are insufficient.
- For causal claims and generalizations, try to falsify the mechanism or scope. Hold contested claims and discard refuted ones; a damaging recurring misconception may warrant a verified correction.
- New topics normally require the same knowledge in at least two independent session captures, matched by meaning across PROMOTE and CONTEXT. Different files from one session are not independent recurrence.
- Preserve the recurrence exceptions: explicit `(user-asked)` captures and updates to existing topics need no second occurrence. A first occurrence may also qualify when losing it risks serious damage or rework and the event is too rare to recur in the lookback window; explain that exception in the report.

PROMOTE contains complete capture days from the watermark through yesterday; CONTEXT contains up to five earlier capture-days. Held entries remain available in that lookback until they age out; short-term storage is not an always-available development memory.

## Topic shape

Use one `.claude/skills/knowledge-<slug>/SKILL.md` per coherent topic:

```markdown
---
name: knowledge-<slug>
description: >
  <Specific task cues and when this topic should be loaded.>
user-invocable: false
---

# <Topic>

- <Scoped constraint or decision, with its non-obvious reason when needed.>
- <How it changes work; point to the authoritative owner for implementation detail.>

<!-- Last verified: YYYY-MM-DD, commit: <short-hash> -->
```

- Keep descriptions concise and specific; retain the words a future task would use to discover the topic. Bodies should usually fit in 20–40 lines, but preserve necessary constraints rather than satisfying a mechanical cap.
- Keep each rule self-contained and normally within two sentences. Prefer stable file or symbol pointers to copied inventories, drifting line numbers, and historical incident narratives.
- Merge by shared use, not merely a loose thematic match; unrelated rules under a broad title make retrieval less precise. Keep one owner for a shared contract and only the relevant consumer-specific cue elsewhere.
- Retain topics for verified decision value. Do not infer disuse from missing load counts or last-loaded dates; the retired telemetry missed Codex and direct file reads.
