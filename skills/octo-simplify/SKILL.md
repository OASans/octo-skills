---
name: octo-simplify
description: >
  Simplify code without changing what it does: delete dead and impossible code,
  merge duplicates, collapse one-use abstractions, shrink file count and size,
  flatten logic. Fans out one read-only finder sub-agent per angle, verifies every
  removal claim, applies safe changes under a green build/test gate, and proposes
  risky ones for approval. Run `/octo-simplify` (changed files) or
  `/octo-simplify <path>` (a directory or the whole project).
disable-model-invocation: true
---

Simplify code for the same behavior: fewer lines, fewer files, flatter logic, easier to maintain. The main agent scopes and measures, fans out finders, has removal claims verified, applies what is safe, and proposes the rest.

**Explicitly invoked only.** `disable-model-invocation: true` keeps a skill that deletes code out of the agent's tool list; a person runs it.

Rules that hold in every step:

- **Same behavior.** Only how the code works changes, never what it does. A finding whose fix alters observable behavior is not a simplification.
- **The coding guide judges.** Every finding cites a rule from the `octo-coding-guide-*` family; *Clarity Over Brevity* is the tie-breaker, so a nested ternary or dense one-liner never counts as a win.
- **Numbers measure, they don't decide.** Line and file counts are reported before and after; a change is kept because it is simpler, not because the count went down.
- **A check leaves only with proof.** Removing a guard, fallback, error path, or validation needs a cited reason it cannot trigger — the type, the invariant, or the boundary that already validated it.

## Steps

### 1. Scope — main agent, cheap commands only

Throughout the skill the main agent never reads code bodies or guide bodies; sub-agents find, verify, and edit. Only paths, numbers, and findings enter the main context.

1. **Target.** No argument: changed files — `git diff HEAD --name-only` plus `??` lines from `git status --porcelain`; both empty → `git diff @{upstream}...HEAD --name-only` (no upstream → `HEAD~1..HEAD`). With a path argument: every code file under it. Drop Markdown, binaries, generated output, and lockfiles. Nothing left → reply `Nothing to simplify.` and stop.
2. **Baseline.** Record file count, `wc -l` total, and the largest file. If `lizard`, `radon`, or `cargo clippy` is already installed, record its complexity figure too; never install a tool.
3. **Guides.** `grep -l "^guide-scope:" ~/.claude/skills/*/SKILL.md .claude/skills/*/SKILL.md`, keep the guides whose scope matches a target file, and pass their paths to every finder.
4. **Gate.** Take the build and test commands from the project's CLAUDE.md. Without a test command, only the Safe tier may be applied and the report says so.

### 2. Find — one finder per angle

Spawn one read-only sub-agent per `###` angle under **Angles** below, all in one message (`subagent_type: general-purpose`, `model: sonnet`). Give each: the base prompt, its angle text, the guide paths, the target file list, and the diff command when the scope is a diff.

**Base prompt (all finders):**

> You find simplifications for one angle. READ-ONLY — never modify anything.
>
> 1. Read the guide files; they are the rulebook. Your angle text says which kind of simplification you hunt.
> 2. Read every target file in full. For each candidate, Grep callers and definitions before claiming anything is unused, duplicated, or unreachable.
> 3. Report a candidate only when you can name the simpler form and its cost today (what is duplicated, dead, deeper than needed, or spread across more files than needed). No nameable gain, no finding.
> 4. Tier each finding: **safe** — behavior provably identical and the change stays inside the target files; **approval** — removes a guard, fallback, error path, or validation; deletes or merges a file; changes a public signature; or touches files outside the target. An approval finding must include its proof: the type, invariant, guard, or caller that makes the code unnecessary.
>
> Never flag: style not written in a guide; a check at a system boundary (user input, external API, file, network); code a linter or compiler already reports; a pattern seen fewer than three times as duplication.
>
> Return at most 10 findings, largest gain first, each as `file:line — [tier] [<Guide rule>] current → simpler form — gain — proof (approval only)`. If nothing, return exactly: `No simplifications found.`

### 3. Verify — one verifier maximum

Dedup findings on the same lines or mechanism. Bundle every **approval** finding, plus any safe finding a second finder disputed, into one read-only verifier (`general-purpose`, `model: sonnet`; tell it not to spawn sub-agents). It returns per finding **CONFIRMED** (quotes the proof in the code), **PLAUSIBLE** (mechanism real, proof incomplete), or **REFUTED** (the code can reach that path, or behavior would change). Keep only CONFIRMED in the approval tier; drop the rest and count them.

### 4. Apply the safe tier

Hand each file's findings to one worker sub-agent (`general-purpose`, `model: sonnet`) with the findings, the gate commands, and the revert rule: apply the file's findings, run the build and tests; green → keep; red → revert that file's changes and report the finding as `reverted`. Run workers one at a time so each gate result belongs to one file.

### 5. Propose the approval tier

List every CONFIRMED approval finding with its proof and wait for the user to pick. Apply the picked ones exactly as in step 4. More than ~15 items → write the full list to `./simplify-plan.md` in the project and print the top items plus the path.

### 6. Report

One report: before → after numbers from step 1, then `applied`, `reverted`, `proposed`, `dropped` (with REFUTED/PLAUSIBLE counts). A clean target is a valid outcome — never invent findings.

## Angles

Each `###` below is one finder. Add an angle here and one more finder spawns with no edit to the steps.

### Dead & impossible

Unused functions, types, imports, parameters, and config; unreachable branches; error handling for conditions the types or an earlier check already exclude; re-validation of data validated at the boundary; redundant conversions, copies, caching, or wrapping that add nothing.

### Duplication & reuse

The same pattern three or more times → one helper; near-duplicate functions merged into one with a parameter; new code that re-implements a helper the codebase already has. Name the helper to call or create.

### Structure

Tiny files merged into their only consumer; files over 500 lines split by concern; one-use abstractions collapsed — an interface with a single implementation, a factory that builds one thing, a function that only forwards to another; deep nesting flattened with early returns. Name the resulting file layout.

### Altitude

A special case layered onto shared code → generalize the mechanism instead; an abstraction that fits its callers badly → inline it and keep the duplication. Name the mechanism that makes the special case disappear.
