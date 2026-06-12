---
name: octo-blueprint
description: >
  The definition of a good AI-agent-native package, plus a review that grades the
  current package against it and returns a prioritized list of action items to
  close the gaps. Run it on demand with `/octo-blueprint` (optionally naming a path).
disable-model-invocation: true
---

# Octo Blueprint

`/octo-blueprint` is the team's definition of a good **AI-agent-native package** — and a review that measures a package against it and returns a list of action items.

**Why a blueprint, not a template.** You can't keep a new package good by copying files from a model package: the exemplar's files drift, so every copy is stale the day after. Rules migrate where files can't. Encode *what good looks like* once — here — and any package can be graded against it on demand. Writing the code to satisfy a rule is cheap; an agent can do it — **as long as it knows the precise, concrete feedback**. This skill produces that feedback.

**Explicitly invoked only.** This is enforced, not just convention: the `disable-model-invocation: true` frontmatter flag keeps the skill out of the model's tool list, so the agent can never auto-invoke it — not via `/octo-commit`, `/octo-review`, `/octo-memory`, or context. It stays user-invocable, so a person runs it on demand with `/octo-blueprint` (optionally naming a target path).

## Steps

1. **Pick the target.** The current project root by default, or a path the user named with the invocation.
2. **Load the blueprint.** Read **The Blueprint** below. If it defines no dimensions yet (the skeleton state), there is nothing to grade — report *"The blueprint is not yet defined."* and stop.
3. **Grade every rule.** Walk each rule in each `###` dimension. For each, inspect the package (read files, run quick checks) and mark it **met / partial / unmet / N/A**.
4. **Turn gaps into action items.** For every *partial* or *unmet* rule, write one action item per the format below — each with a concrete "Do" the next agent can act on without re-deriving the rule.
5. **Report.** Output the prioritized action-item list. This skill is **read-only**: it proposes the work; it never edits the package. Implementing the items is a separate step (the user, or another agent).

## Output — action items

Lead with a one-line verdict: the met/total tally and the action-item count (e.g. `12/18 rules met — 6 action items`).

Then a prioritized checkbox list, one item per *partial* or *unmet* rule:

```
- [ ] P0 — <imperative title>   ·   <dimension>
      Gap: <what the rule wants vs. what the package has — name the path>
      Do:  <the concrete change that satisfies the rule>
```

- Order **P0 → P1 → P2** (blocking → important → polish).
- No item without a concrete **Do** — a finding the next agent can't act on isn't an action item.
- Cite paths so the fix is locatable; keep each item to a few lines.

## The Blueprint

> **Structure contract.** Each `###` below is one **dimension** of a good
> AI-agent-native package (e.g. its docs, tests, CI, agent affordances, memory,
> packaging). The review above walks every rule in every dimension and emits one
> action item per gap. Add a dimension by adding a `###` here; keep each dimension
> to a single coherent concern. Write each rule as a top-level bullet (its name
> and essence) with the checkable criteria as nested sub-bullets.
>
> **Status: in progress.** Dimensions are filled in over time — the list below is
> not yet exhaustive.

### CLAUDE.md

*What good looks like: CLAUDE.md is the agent's front door — whoever opens it grasps what the project is and how to work in it fast, without wading through detail that belongs in code or other docs.*

**Sections — in the order they appear in the file:**

- **Project summary** — **opens the file**. Recommended heading: **`Project Summary`**.
  - A short, high-level summary of what the project is and who or what it's for.
  - **≤5 sentences**, plain language, answering *"what is this?"* not *"how is it built?"*.
  - **No technical detail, paths, or file names** — those belong lower in the file or in code.
- **Goals & tenets** — **comes next**. Recommended heading: **`Goals & Tenets`**.
  - The project's north star: the problem it solves and what it optimizes for, as **≤5 compact bullet points**.
  - These are the tenets that steer every product and design decision, so pitch them as direction, not features or implementation.
- **AI Tools index** — an `## AI Tools` section is the package's complete **catalog** of wrapper **scripts** under the root `ai_tools/` — the menu an agent selects from for *any* task, so it runs one short command instead of rebuilding a complex one; the scripts double as the harness.
  - **The full inventory, not just the gates** — lists *everything runnable*: each gate plus its variants (a build per language or component) and the utilities Workflow never names (clean, single-test). That's its value over Workflow — Workflow names only the tools that *must* run; this section carries the invocation detail (path, flags, inputs) for *all* of them so the agent selects freely. They complement; they don't overlap.
  - **Open with this exact line, verbatim and identical in every package:** *ALWAYS prefer these scripts over the equivalent manual command.* — enforcement only, no rationale and no per-project rewording.
  - **Scripts only, never skills** (a skill is heavier; if a command or script does the job, it belongs here).
  - **Lead each entry with the runnable script path** (e.g. `ai_tools/build.sh`) so it runs as-is, then a one-line purpose **plus the flags or inputs it takes**, if any — no internals, and no alias layer (`ai-tool:build`); the path is the handle and can't drift from itself.
  - **Verify every line — don't trust the text**: read each script (or run its `--help`) and confirm the path exists and the purpose, flags, and inputs still match what it actually does; the folder has no script the section omits, and nothing listed is stale or renamed.
  - *Scope: the `ai_tools/` folder's own quality is a separate dimension; here, just check the section is scripts-only, path-led, accurate, in sync, and compact.*
- **Workflow** — the project-specific gates an agent runs before review, layered on the global workflow and split by cost into a fast loop and a slow verification pass. Recommended heading: **`Workflow`**.
  - **Doesn't restate the global workflow** (already in the global `~/.claude/CLAUDE.md`): no `git pull` at start, no `/octo-review`, no `/octo-memory` at end. Reference the global as given and add only what's project-specific — e.g. open with *"Project-specific gates, on top of the global workflow:"*.
  - **Exactly two subsections, split by cost — and only these two.** The cheap gates get rerun constantly while the expensive ones run once, so the split keeps a slow suite from blocking fast iteration. Any other one-off gate (version bump, dependency-manifest update) folds into the nearer subsection or the file's notes — never a third subsection.
    - **`Dev loop`** — the fast, cheap gates (build → unit tests → lint/format) as a tight loop: edit → run them in order → fix what's red → rerun, never advancing past a red gate. Rerun on every change; state the exit condition plainly as *every fast gate green*.
    - **`Verification`** — the expensive, slow gates (E2E, integration, coverage), run once the dev loop is green. It's the final pre-review check and what proves the change *meets its requirement*, not merely that the harness is healthy. Conditional gates name their trigger (e.g. a suite that runs only when its subsystem changed).
  - **Gates run through the package's `ai_tools/` harness** — name the must-run gate by its `ai_tools/` handle, not raw commands; don't re-document it or list its variants — which concrete script(s) a gate maps to lives in the AI Tools catalog.
  - **Exit = ready for review** — both subsections green means the change satisfies the harness and meets its requirement; only then does it hand off to the global review-and-commit. The section sits before that approval step and doesn't restate it.
- **Module map** — a directory-level map of *only* the major, most-valuable paths, so a cold agent finds the places that matter without searching. Recommended heading: **`Module Map`**.
  - **Capped and selective — ≤10 lines, one path per line.** List the handful an agent navigates to or touches often: the top source roots, and in a polyglot repo the root per language or component (Rust here, Python there). Drop the long tail — leaf dirs, generated/vendor/config folders, anything trivially discoverable or rarely touched.
  - **Directory-level, not a file listing** — each line a directory plus a few words on what's inside; a specific file only when it's a real landmark. This is what keeps it short and slow to rot.
  - **Re-verified against the live tree every run — the fastest-drifting section.** Read the actual layout (`git ls-files`, or the top two levels) and confirm every listed path exists and isn't renamed or moved, no *major* root is missing, and it hasn't crept past the cap into the long tail.
- **Debug** — the few entry points every dev session needs to *start* debugging from, so an agent isn't lost the moment something breaks. Recommended heading: **`Debug`**.
  - **≤5 bullets, entry points not a manual** — each is a place to look or a thing to run: where the project emits logs/state (a file or dir, or a cloud sink like a CloudWatch log group); how to turn logging up (config flag, env var); for a deployed service, where its logs and metrics live and how to reach them (deploy step, AWS console, dashboard); the one tool you run to debug (the runnable lives in AI Tools — here just name it).
  - **Every-session essentials only — the one place always-loaded beats a skill.** Include a line only if *most* dev tasks need it. The deep dive (full log routing, every query idiom, archive behavior) stays conditional → a `knowledge-*` skill.
- **Additional notes** — a capped catch-all for the rare project-specific must-know that fits no section above. Recommended heading: **`Additional notes`**.
  - **≤5 bullet points, hard** — each a single project-specific rule with no better home (e.g. *"update `scripts/install_deps.sh` when adding a dependency"*).
  - **Overflow is a signal, not room to grow** — past five, don't expand it: the overflow either is a recurring concern that earns its own section (a deliberate edit to this blueprint) or is conditional knowledge → a `knowledge-*` skill. The cap forces the choice.

**Whole-file discipline:**

- **Only the sections this blueprint names — a closed set.** A CLAUDE.md contains exactly the sections above and no ad-hoc ones; an unlisted heading is itself a finding. Growing the set is a deliberate edit to *this blueprint*, never a one-off in a package.
  - Content that fits no section goes in **Additional notes** (capped at five); when that overflows, the overflow earns its own section here or moves to a `knowledge-*` skill — the file never sprouts an unsanctioned heading.
- **No knowledge, no doc index** — CLAUDE.md holds operational essentials an agent needs early and often; it's never a place for knowledge or a catalogue of where knowledge lives.
  - Per-topic knowledge belongs in on-demand `knowledge-*` skills — their descriptions self-index every session, their bodies load only when relevant — so don't inline knowledge here, and don't list skills or docs as a reference shelf (CLAUDE.md is always-loaded; conditional content is the wrong fit).
  - Pointing the agent at a skill *as a workflow step* is fine; cataloguing knowledge for browsing is not.
- **No markdown tables** — the reader is an agent, not a human.
  - No `|`-delimited tables anywhere in CLAUDE.md.
  - Use nested bullets or short prose instead — they parse and diff cleaner and don't misalign when edited.

<!--
TEMPLATE — copy per new dimension; write each rule as a bullet with nested criteria:

### <Dimension name>

*What good looks like: <one-line focus for this dimension>.*

- **<Rule name>** — <one-line essence; recommended section heading if it maps to one>.
  - <checkable criterion>.
  - <checkable criterion>.
-->
