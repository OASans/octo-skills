---
name: octo-memory-short-term
description: >
  Sub-step of `/octo-memory`: append one capture to the local short-term
  buffer. Driven by the orchestrator — run `/octo-memory`, not this directly.
user-invocable: false
---

Write reusable knowledge to the project's short-term memory — a **local** capture buffer in a per-project home store (never committed, not loaded into any session's context). Low barrier — write often. This is the capture step; `octo-memory-long-term` later reads it to consolidate the valuable parts into long-term. Most captures are evidence, not memory yet — a brand-new long-term topic normally requires the same knowledge to be captured again by a later session, so write freely and let recurrence decide.

## What to capture

If it took significant work to learn, it belongs here — takeaways from subagent/Explore runs, hard-won exploration, a gotcha the user just taught you. Concretely:

- Implementation patterns others would need to replicate or extend
- Non-obvious gotchas, debugging insights, or tricky integration points (how X connects to Y)
- Architecture decisions and their rationale

## What to skip

- Task progress or status, and anything self-evident from reading the code
- Anything a commit message or regression test already captures — especially **bug-fix post-mortems** (one bug's symptom→cause→fix: the commit + test ARE the memory; don't write it just because debugging was hard)
- **Session/subagent narrative** ("Agent B caught X", "Phase A shipped with…") — describe the rule, not the session that produced it
- Temporary workarounds that will be removed

## Steps

Short-term lives in a **per-project home store**, shared across every checkout of this repo on this machine and **never committed**. Resolve the location first (errors if there's no `origin` remote — fix that first, the store must be keyed per project):

```
url=$(git remote get-url origin 2>/dev/null)
key=${url##*/}; key=${key%.git}
[ -n "$key" ] || { echo "ERROR: no git 'origin' remote; set one (git remote add origin <url>) so memory can be keyed per project"; exit 1; }
dir="$HOME/.octo-memory/$key/short_term/$(date +%F)"
mkdir -p "$dir"
```

1. Write each capture to a **new, uniquely-named file** in `$dir` (e.g. `$dir/$(date +%H%M%S)-$$-$RANDOM.md`). One file per capture means concurrent agents in sibling checkouts never clobber each other — no locks needed.
2. Use the entry format below. If you capture several related things this session, reuse the file you just created (its path is in your context) and append more `## <topic>` blocks to it.

```
## <Topic Title>

<Free-form content. Include file paths, function names, patterns, gotchas.
Keep it concise but complete enough to be useful months later.>
```

3. Each entry starts with `## <topic>` on its own line — append `(user-asked)` to the heading when the user explicitly told you to remember this; consolidation promotes tagged entries without waiting for recurrence. No YAML, no other metadata. Just knowledge.

## Be concise

Short-term is **not** loaded into sessions — `octo-memory-long-term` reads it once at consolidation. So compress for *signal*: aim for **≤1 line per fact**. A busy day legitimately produces many entries — fine; what's not fine is one entry bloated to 15 lines off a four-paragraph template. Tight entries consolidate cleanly; bloated ones bury the rule.

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

### Rules

- Lead with the knowledge — not preamble or a restatement of the task that produced it ("X does Y when Z", not "I learned that…").
- **State the why for a causal claim** — if the capture asserts "X because Y" or "always/never Z", put the mechanism on the same line. It seeds consolidation's refutation gate, and a claim with no reason is the one most likely to be coincidence.
- **No code blocks** — a `file.rs:NNN` anchor replaces them (full path at first mention, short anchor like `mouse.rs:320` after). Sole exceptions: env-var names, exact wire field names, escape sequences whose literal characters matter.
- **Drop narrative and framing scaffolds** — no "we tried…, then realized…", no **Symptom:/Cause:/Fix:/Verified on:** subsections. Keep the conclusion; fold any load-bearing detail into prose. One closing `**Rule:**` is fine, don't sprinkle three. The urge to write Symptom→Cause→Fix usually means a bug-fix post-mortem — the commit is the memory; don't write it.
- **Merge within your session**: append related insights under one `##` heading in the file you already created (see Steps); cross-session dedup is `octo-memory-long-term`'s job.
- **Recapture across sessions**: never skip a capture because an earlier session probably wrote the same thing — you can't see the buffer, and an independent re-capture is exactly the recurrence evidence that promotes knowledge to long-term. Only same-session insights merge; independent sessions count separately.

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
