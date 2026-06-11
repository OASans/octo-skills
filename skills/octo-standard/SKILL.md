---
name: octo-standard
description: >
  The definition of a good AI-agent-native package, plus a review that grades the
  current package against it and returns a prioritized list of action items to
  close the gaps. Run it on demand with `/octo-standard` (optionally naming a path).
disable-model-invocation: true
---

# Octo Standard

`/octo-standard` is the team's definition of a good **AI-agent-native package** — and a review that measures a package against it and returns a list of action items.

**Why a standard, not a template.** You can't keep a new package good by copying files from a model package: the exemplar's files drift, so every copy is stale the day after. Rules migrate where files can't. Encode *what good looks like* once — here — and any package can be graded against it on demand. Writing the code to satisfy a rule is cheap; an agent can do it — **as long as it knows the precise, concrete feedback**. This skill produces that feedback.

**Explicitly invoked only.** This is enforced, not just convention: the `disable-model-invocation: true` frontmatter flag keeps the skill out of the model's tool list, so the agent can never auto-invoke it — not via `/octo-commit`, `/octo-review`, `/octo-memory`, or context. It stays user-invocable, so a person runs it on demand with `/octo-standard` (optionally naming a target path).

## Steps

1. **Pick the target.** The current project root by default, or a path the user named with the invocation.
2. **Load the standard.** Read **The Standard** below. If it defines no dimensions yet (the skeleton state), there is nothing to grade — report *"The standard is not yet defined."* and stop.
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

## The Standard

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
- **AI Tools index** — an `## AI Tools` section maps the project's wrapper **scripts** (build, test, lint, …) under the root `ai_tools/`, so an agent runs one short command instead of rebuilding a complex one — the scripts double as the harness.
  - **Open with this exact line, verbatim and identical in every package:** *ALWAYS prefer these scripts over the equivalent manual command.* — enforcement only, no rationale and no per-project rewording.
  - **Scripts only, never skills** (a skill is heavier; if a command or script does the job, it belongs here).
  - **Lead each entry with the runnable script path** (e.g. `ai_tools/build.sh`) so it runs as-is, then a one-line purpose **plus the flags or inputs it takes**, if any — no internals, and no alias layer (`ai-tool:build`); the path is the handle and can't drift from itself.
  - **Verify every line — don't trust the text**: read each script (or run its `--help`) and confirm the path exists and the purpose, flags, and inputs still match what it actually does; the folder has no script the section omits, and nothing listed is stale or renamed.
  - *Scope: the `ai_tools/` folder's own quality is a separate dimension; here, just check the section is scripts-only, path-led, accurate, in sync, and compact.*
- **Workflow** — project-specific gates only, layered on the global workflow. Recommended heading: **`Workflow`**.
  - Lists the steps unique to this project as an ordered pre-commit checklist — build, test, lint, E2E, version bumps, and the like.
  - **Doesn't restate the global workflow** (already in the global `~/.claude/CLAUDE.md`): no `git pull` at start, no `/octo-review`, no `/octo-memory` at end. Reference the global as given and add only what's project-specific — e.g. open with *"Project-specific gates, on top of the global workflow:"*.

**Whole-file format:**

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
