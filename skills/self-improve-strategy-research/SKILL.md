---
name: self-improve-strategy-research
description: >
  Run a serial octo-fin research improvement loop: one reviewed-ready idea,
  independent transcript and results analysis, evidenced workflow fixes, then the next idea.
  Use when asked to continuously improve research quality, token use and latency.
---

# Self-improve strategy research

Spend model effort on scientific thinking that adds value. Reduce repeated discovery,
boilerplate, unnecessary reads and avoidable operational failures through demonstrated
changes to existing tools and instructions. Improve quality, token use and latency together;
a faster invalid research result is not an improvement.

## Scope and concurrency

Run from an octo-fin checkout with its `strategy-research-orchestrator` skill,
canonical `.codex/agents/strategy-research-worker.toml` and
`ai_tools/research/strategy_research/assignment_execution.md`. These own research execution;
this skill adds the serial improvement cycle. If they are unavailable, report the prerequisite.

Keep research concurrency **one**. Do not overlap the next strategy researcher with the
previous research episode or its analysis/fix stage. Analysis, implementation and review
agents are not additional researchers. When another research fleet is already running,
coordinate its authorized drain before starting this mode; do not forcibly stop it.
Creating or editing this skill does not activate it or change an existing fleet.

Use only existing reviewed-ready queued ideas or authorized retained work. Reuse saved
reviews and immutable evidence; do not rerun source intake or collect new ideas. Reuse
read-only preflight and shared capacity setup while their identities remain valid.

## Repeat one round

1. **Research.** Dispatch one `gpt-6.1-sol` worker with no history inheritance and the model
   in its visible name. Give the idea ID, scope and original budget, plus necessary canonical
   runtime/environment references. The worker owns claim, workspace, supervisor, saved
   reviews, pins, scientific comparisons, implementation, checks, frozen workflow,
   screen/rank/full evaluation, artifacts and closure. Use ordinary automatic capacity
   waiting, cancellation and cleanup; no coordinator READY/GO scheduling or catalog barrier.
   Receive completion and exception notifications; use occasional checks only to unblock
   demonstrated trouble.
2. **Analyze before another researcher starts.** Delegate a bounded read-only original
   worker transcript and result-artifact review to `gpt-6.1-sol`, explicitly selected and
   named. Check the actual model/task binding. Include failed preparation and operational
   HELP episodes, not only successes. Locate concrete repeated work, unnecessary fields or
   reads, missing interface guidance, tool misuse, repeated comparisons and blockers.
   Distinguish useful science and necessary causal checks from overhead. Source/formula
   reads needed for execution are not repeated intake reviews. Do not redo scientific
   source intake or infer waste from elapsed time alone.
3. **Choose a demonstrated improvement.** Main agent owns decisions. Rank concrete failures
   and supported recurring costs by scientific quality, token/latency benefit and change
   risk. Prefer a small correction to an existing operation over repeated model work.
   For every observed operational error, identify its cause and implement verified durable
   prevention in existing tools or instructions; a one-off workaround is not a completed
   prevention fix. Preserve bounded local repairs and escalate shared bugs, unresolved
   conflicts or decisions outside authorized scope with exact retained evidence. External
   failures need bounded recovery and explicit limits, not a promise of zero recurrence.
   Scientific rejections are not operational errors. Operational failure is HELP, never a
   silent scientific rejection. If no worthwhile change is supported, record that and
   continue without manufacturing a fix.
4. **Fix and verify.** Preserve active/retained workspace and frozen runtime identities.
   Use an isolated detached worktree when needed, following project branch policy; merge
   every completed fix into the default branch. Apply focused behavior regression coverage,
   required project checks and independent `gpt-6.1-sol` review for consequential changes.
   Resolve actionable findings. Commit and push each authorized major fix promptly before
   using it in the next round; do not accumulate fixes until the loop ends.
5. **Close and restart the cycle.** Verify accepted closure and actual supervisor exit,
   cancellation and resource cleanup. For recoverable trouble, resume the same episode
   within its original budget; do not reset its claim/deadline to disguise a failure.
   Preserve unresolved HELP and exact next actions when the budget expires. Use the checked
   committed runtime and refreshed readiness evidence for the next idea. Retain unchanged
   reviews/comparisons. Never rerun an accepted terminal trial as an operational retry.

For a complex unresolved bottleneck or periodic deeper second opinion, optionally use
`octo-chatgpt-analysis` for browser GPT-6 Pro. Collect relevant original transcripts,
strategy code, settings, result artifacts and workflow documents; ZIP them and upload that
ZIP directly within the authorized scope. Preserve actual permission requirements and
follow the browser skill. Save its response and distinguish proposals from verified facts.
No sanitizer, exporter, deduplication system or reusable bundling tool.

## Evidence and quality

Use normal operation receipts, existing metrics and existing transcript accounting;
never add manual metrics or prorate transcript time into invented phases. Record:

- Idea, exact worker/runtime/data identities, scope and outcome: scientific duplicate,
  scientific rejection, VERIFIED or operational HELP. These are report categories, not
  new lifecycle statuses.
- Automatic elapsed and available setup, capacity wait, evaluation, publication and
  closure intervals; comparison counts, catalog refreshes, actual restarts and repairs.
- Final cumulative worker token usage and available analysis/fix/review usage separately,
  using the existing accounting reader. Cached input is a subset of input; do not sum
  cumulative snapshots or double count nested sessions. Missing usage or phase attribution
  stays unknown.
- Evidence of quality: valid causal checks, reproducibility, provenance, retained warnings,
  preserved admission rules and complete closure. A valid rejection is useful research;
  admission count alone does not measure work quality.
- Concrete friction, changed files/commit, checks/review and the next round's observations.
  Compare compatible scope and complexity; a single faster run does not establish causality.

Preserve canonical ownership per distinct hypothesis, frozen declarations, causal/PIT
checks, provenance, trial accounting, admission gates, mandatory **raw IS Sharpe ≥0.7** and
visible data warnings. Closest mechanism/timing/trading-construction comparisons may prove
scientific equivalence through the existing immutable duplicate-completion path; names,
hashes or correlation alone cannot. Catalog freshness is recoverable without resetting
startup or discarding unchanged judgments. Do not weaken scientific gates to improve speed.
Honor deferred work, including snapshot/index optimization, unless separately authorized.

Keep one compact round report in the existing research artifact area; reuse durable
receipts rather than scanning the full archive each round. Continue until the user stops,
an explicit limit is reached, executable supply is dry, or a required outside-scope decision
prevents further authorized work. Checkpoint retained work and report the concrete reason;
do not silently treat operational blocks as completed research. This is a host-driven loop,
not an unattended dispatcher promised after the conversation ends.
