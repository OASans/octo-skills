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

## Refutation gate — claims that assert cause or generalization

Criteria 1–5 are positive filters — they ask *does this deserve a slot?* They catch idiosyncrasy (one session over-valuing something) but not **plausible-but-wrong**: a misconception recurs *because* it is plausible to everyone who hits it, so recurrence alone can promote a popular myth. Before promoting any candidate that states a **cause** ("X because Y") or a **generalization** ("always / never Z"), try once to falsify it:

- Is the stated mechanism the real cause, or a coincidence that happened to co-occur?
- Does the rule hold outside the one context it was seen in, or is it leakage from that setup?

Outcomes:
- **Confirmed** → promote normally.
- **Contested** — mechanism neither confirmed nor refuted → **hold**, exactly like a not-yet-recurred entry: don't spend an always-loaded slot on an unconfirmed rule; if it is real it recurs with better evidence.
- **Refuted** → drop. If the wrong claim is damaging *and* recurring, promote its **correction** as an anti-pattern topic ("X looks true but isn't — actually Y") so recurrence can't resurrect the myth. The correction may take its mechanism from a CONTEXT twin — that is not "promoting a CONTEXT entry on its own" (the refuted PROMOTE entries carry the recurrence); it is recording why they are wrong.

Pure factual or locational captures ("config lives in `config.ts`") assert no cause — they skip this gate; criterion 3's existence-check is enough.

## What makes a good topic

A topic answers two questions — **what is this** and **how should it change my behavior** — plus a third when it asserts a cause or a rule: **why is it true (the mechanism)**. The second separates knowledge from trivia (no concrete "when/how to apply" → don't promote). The third lets a future agent judge whether the rule still holds in a new context, and it is what the Refutation gate checks — a rule with no stated mechanism can be neither applied safely nor attacked. Fold the *why* into What or How to Apply; don't add a section. (Body structure — What / How to Apply / Key Files — is in the template below.)

Bad (trivia):
> "The scheduler runs every 30 minutes."

Good (actionable):
> "The scheduler runs every 30 minutes via node-cron. Register new data sources in src/scheduler/jobs.ts — don't add standalone cron entries; the scheduler centralizes retry and rate limiting."

Its closing clause is the *why*: "centralizes retry and rate limiting" is the mechanism — how a future agent knows when the rule applies and when it doesn't.

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

## Usage telemetry

Every knowledge-topic load is logged by a global PostToolUse hook to `~/.octo-memory/<key>/usage.log` (machine-local, shared across checkouts). Each topic dir also carries a **script-owned sidecar** `usage.md` (`last-loaded:` + `loads:`, committed) — retention evidence, not knowledge: never hand-edit it, never cite it in a topic body. `usage-stats.sh` prints per-topic totals (Phase 2 reads this); `usage-stats.sh --stamp` folds new log lines into the sidecars and trims the log (Phase 3 runs this). After a one-time bootstrap (`loads: 0`), a sidecar changes only when its topic is actually loaded — a long-unchanged sidecar is itself the disuse signal. Only Skill-tool loads are counted (direct file Reads aren't), so treat `loads` as a coarse signal and judge retention on `last-loaded`.

## Steps

Consolidation is a **daily** pass. `octo-memory` already gated it via `consolidation-due.sh` and loads this skill **only on DUE** — whether to run today is already decided, so there is no skip-check here. Each script below resolves its own paths from the `origin` remote, so there is nothing to set up. Promotion is criteria-based only — short-term is not loaded into sessions, so there is no "promote what I used this session" step.

#### Phase 1: Promote new knowledge

1. Run `bash ~/.claude/skills/octo-memory/collect-captures.sh`. It emits one blob with two sections: **PROMOTE** (captures in `[last_processed_date, today)` — the exactly-once promote set) and **CONTEXT** (the prior ~5 already-processed capture-days — the recurrence lookback, plus context for writing better topics). The script owns the date range so you never re-derive it by hand — see its header for why the bounds are `>= watermark` and `< today`. If PROMOTE is empty, skip to Phase 2.
2. For each `##` entry in **PROMOTE**, classify against the promotion criteria. Scan PROMOTE and CONTEXT for twins — another independent capture of the same knowledge makes the entry *recurred*. Never promote a CONTEXT entry on its own; when a recurred PROMOTE entry earns a topic, folding supporting detail from its twins into the body is fine. If the entry asserts a cause or generalization, run it through the **Refutation gate** before promoting.
   - **New topic**: confirmed (or non-causal), recurred (or an exempt lane), and no existing `knowledge-*` covers it → create `.claude/skills/knowledge-<slug>/SKILL.md`.
   - **Update existing**: extends an existing topic → read that skill, merge, bump `Last verified`.
   - **Hold**: passes criteria 1–4 but hasn't recurred, or the gate left it **contested** → do nothing; the file stays in the buffer and resurfaces as CONTEXT next run.
   - **Refuted**: the gate disproved the claim → skip; promote its correction as an anti-pattern topic only when the myth is damaging and recurring.
   - **Ephemeral**: fails 1–4, no lasting value → skip.
3. **Verify** each new/updated topic with Grep/Glob — referenced files/functions must exist.

#### Phase 2: Staleness sweep

Run `bash ~/.claude/skills/octo-memory/usage-stats.sh` once — per-topic `loads` + `last-loaded` (see *Usage telemetry*). Then review every existing `.claude/skills/knowledge-*` skill:
1. Read the skill body; identify its key references (files, functions, patterns).
2. Grep/Glob each reference. If gone, one quick search for a rename/move.
3. Check the pattern is still used, and that it is not now covered by doc/ or CLAUDE.md.

**Deprecate** (delete the `knowledge-<slug>/` folder) if ANY hold:
- **Dead references**: key files/functions gone and not moved.
- **Superseded**: the pattern was replaced.
- **Documented elsewhere**: now fully covered in doc/, CLAUDE.md, or code.
- **Absorbed**: merged into another topic.

**Unused** (usage-based, gentler than deletion): `last-loaded: never` or >90 days ago, on a topic that has had its chance (created >30 days ago per git). The knowledge may still be accurate, so don't just delete the slot — **merge** its one load-bearing rule into a sibling topic, or **demote**: append its distilled entry as a normal capture file in today's short-term folder, then delete the topic; if it matters again it recurs and re-earns the slot. Keeping an unused topic is allowed (e.g. rare-but-damaging release knowledge) — justify it in the report. Recently-loaded topics are never deprecated on usage grounds; the other Deprecate criteria still apply to them, though frequent loads warrant a harder rename-search before concluding a reference is dead.

If partially stale (some refs dead, core still valid), update instead of deleting.

#### Phase 3: Finalize

1. Stamp usage: `bash ~/.claude/skills/octo-memory/usage-stats.sh --stamp` — folds the load log into each topic's `usage.md` sidecar and trims the log. No model writes sidecars by hand.
2. Stamp the watermark: `bash ~/.claude/skills/octo-memory/mark-consolidated.sh` — it writes `last_processed_date: <today>` (the file's only line). No model writes the tracker by hand.
3. Report **in-session** (not to the file): N entries processed, M new topics, K updates, H held (awaiting recurrence or left contested), R refuted, J skipped, L deprecated (with reasons), U unused topics handled (merged / demoted / kept-with-reason).
