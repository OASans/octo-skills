---
name: octo-simplify
description: >
  Simplify code while preserving behavior. Use only when explicitly asked to simplify, clean up, deduplicate, or shrink code; never as an automatic workflow step.
---

Simplify code for the same behavior: less duplication, clearer ownership, flatter logic. The main agent scopes and tracks coverage, assigns bounded file groups, verifies findings, applies what is safe, and proposes the rest.

**Only on explicit request.** This skill deletes code: run it when the user asks for a simplification, never on your own initiative or as a step of another workflow.

Rules that hold in every step:

- **Same behavior.** Only how the code works changes, never what it does. A finding whose fix alters observable behavior is not a simplification.
- **Internal boundaries can move.** Update in-scope callers and tests to use the new owner instead of preserving redundant wrappers or re-exports. Preserve external contracts; an unknown consumer is not proof that a boundary is internal.
- **The coding guide judges.** Every finding cites a rule from the `octo-coding-guide-*` family; *Clarity Over Brevity* is the tie-breaker, so a nested ternary or dense one-liner never counts as a win.
- **Numbers measure, they don't decide.** Line and file counts are reported before and after; a change is kept because it is simpler, not because the count went down.
- **A check leaves only with proof.** Removing a guard, fallback, error path, or validation needs a cited reason it cannot trigger — the type, the invariant, or the boundary that already validated it.

## Steps

### 1. Scope — main agent, cheap commands only

Throughout the skill the main agent never reads code bodies or guide bodies; sub-agents find, verify, and edit. Only paths, numbers, and findings enter the main context.

1. **Target.** No argument: changed files — `git diff HEAD --name-only` plus `??` lines from `git status --porcelain`; both empty → `git diff @{upstream}...HEAD --name-only` (no upstream → `HEAD~1..HEAD`). With a path argument: every code file under it. Drop Markdown, binaries, generated output, lockfiles, gitignored files, and symlinks. Nothing left → reply `Nothing to simplify.` and stop.
2. **Baseline.** Record file count, `wc -l` total, and the largest file. If `lizard`, `radon`, or `cargo clippy` is installed and applies to the target language, record its complexity figure too; never install a tool.
3. **Guides.** Discover `guide-scope` guides from the Codex skill catalog, using source copies when editing this package; keep those matching a target file and pass their paths to every finder.
4. **Gate.** Take the build and test commands from the project's AGENTS.md; if it names none, use what the repo has — test scripts, `bash -n` and JSON/TOML parse checks over the target files. Establish a passing baseline, reusing successful checks from this session when the relevant code has not changed; preserve existing edits. No gate at all → apply nothing; every finding is proposed and the report says so.
5. **Groups and coverage.** Group related files by concern, keeping likely reuse candidates together; size groups by source volume rather than file count. Aim for at most about 40 KiB of source per finder, leaving room for guides, callers, and findings; split larger groups and inspect an oversized file in bounded sections.

Track each target path as `pending`, `partial`, or `inspected` in a project-local scratch manifest, with its assigned group and any unread sections. Use one finder for a small scope that fits the reading budget.

### 2. Find — all angles per file group

Spawn one read-only finder per group, concurrently within the host limit, using general agents with an explicit available model appropriate to the task, including Astra or Sol. Use self-contained assignments with no history inheritance and the selected model in each agent name; give each the base prompt, all **Angles**, guide paths, assigned files, coverage manifest location, and the diff command when the scope is a diff.

Collect coverage alongside findings; truncated output or search-only inspection never counts as a full read. Redispatch only unread files or sections in smaller groups until the target is covered, or report the concrete blocker and remaining scope.

After multiple groups finish, give one finder their compact findings and reusable-pattern summaries for a targeted cross-group reuse check. It searches the named patterns and reads their definitions and callers, without rereading the whole target.

**Base prompt (all finders):**

> You find simplifications across all angles in your assigned file group. READ-ONLY — never modify anything.
>
> 1. Read the guide files; they are the rulebook. Check every angle below within your assigned group.
> 2. Read assigned files in bounded chunks; report any unread files or sections before exhausting context. For each candidate, Grep callers and definitions before claiming anything is unused, duplicated, or unreachable; related caller reads do not expand your assigned coverage.
> 3. Report a candidate only when you can name the simpler form and its cost today (what is duplicated, dead, deeper than needed, or spread across more files than needed). No nameable gain, no finding; a helper that replaces one-liners and leaves the code longer is not a gain.
> 4. Tier each finding: **safe** — behavior and external contracts are provably identical and the change stays within the authorized scope; **approval** — requires an unresolved behavioral decision, expands scope, or risks an externally visible effect. File merges or removal of proven unreachable code can be safe, but require independent verification before application. An approval finding must include its proof: the type, invariant, guard, or caller that makes the code unnecessary.
>
> Never flag: style not written in a guide; a check at a system boundary (user input, external API, file, network); code a linter or compiler already reports; a pattern seen fewer than three times as duplication.
>
> Return at most 10 findings, largest gain first, each as `file:line — [tier] [<Guide rule>] current → simpler form — gain — evidence`. With no findings, say `No simplifications found.`; always append inspected/partial/pending paths and a short list of reusable patterns with locations for the cross-group check.

### 3. Verify — one verifier maximum

Dedup findings on the same lines or mechanism; two findings with one gain but different mechanics both go to the verifier, and the CONFIRMED one with the smaller change wins. Bundle every **approval** finding, every safe finding that spans more than one file or removes a guard, fallback, error path, validation, or file, and any safe finding a second finder disputed into one read-only verifier (use the model selection from step 2; tell it not to spawn subagents). It returns per finding **CONFIRMED** (quotes the proof in the code), **PLAUSIBLE** (mechanism real, proof incomplete), or **REFUTED** (the code can reach that path, or behavior would change). Keep only CONFIRMED findings; drop the rest and count them. A REFUTED finding that exposes a real defect (the code is wrong, not merely redundant) is recorded as `bug noticed`, never fixed here.

### 4. Apply the safe tier

Group coupled findings into one coherent change and assign all affected files to one worker, using the model selection from step 2. Tell the worker it is not alone: preserve others' edits, apply the whole change, then run affected checks and required gates; green → keep, red → revert only that change's own edits and report it. Process groups sequentially so intermediate file states do not invalidate a correct multi-file change.

### 5. Propose the approval tier

List every CONFIRMED approval finding with its proof and ask only for the unresolved authorization; reuse choices already made in this task; running as a sub-agent with no user to ask, list them and stop. Apply the picked ones exactly as in step 4. More than ~15 items → write the full list to `./simplify-plan.md` in the project and print the top items plus the path.

### 6. Report

Lead with maintenance gains: duplicate implementations removed, clearer owners, or simpler control flow; then give before → after numbers from step 1. Include `applied`, `reverted`, `proposed`, `dropped` (with REFUTED/PLAUSIBLE counts), and `bugs noticed` for the user to take to `/octo-review`.

Report inspected/total files and remaining scope separately from findings handled; complete coverage does not mean every possible simplification was found. A clean target is a valid outcome — never invent findings.

## Angles

Every finder checks each `###` angle below within its assigned group. Add an angle here and it is covered with no edit to the steps.

### Dead & impossible

Unused functions, types, imports, parameters, and config; unreachable branches; error handling for conditions the types or an earlier check already exclude; re-validation of data validated at the boundary; redundant conversions, copies, caching, or wrapping that add nothing.

### Duplication & reuse

The same pattern three or more times → one helper; near-duplicate functions merged into one with a parameter; new code that re-implements a helper the codebase already has. Name the helper to call or create.

### Structure

Tiny files merged into their only consumer; files over 500 lines split by concern; one-use abstractions collapsed — an interface with a single implementation, a factory that builds one thing, a function that only forwards to another; deep nesting flattened with early returns. Name the resulting file layout.

### Altitude

A special case layered onto shared code → generalize the mechanism instead; an abstraction that fits its callers badly → inline it and keep the duplication. Name the mechanism that makes the special case disappear.
