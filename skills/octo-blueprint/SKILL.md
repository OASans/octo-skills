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

**The blueprint drives the fan-out.** Each `###` dimension in **The Blueprint** is one grading domain handled by one dedicated sub-agent, and the agent count tracks the blueprint: add a `###` dimension and one more agent spawns automatically, with no edit to the steps. A dimension is the unit of parallelism because its rules share one artifact (a file, a folder) — a single agent reads that artifact once and grades every rule against it, where splitting finer would only re-read the same thing. Each agent grades **only** its dimension, so domains are partitioned with no overlap; the main agent never inspects the package, it just fans out and merges. To parallelize a heavy dimension further, split it into two `###` dimensions — each then runs as its own agent for free.

## Steps

1. **Pick the target.** The current project root by default, or a path the user named with the invocation.
2. **Load the blueprint and list its dimensions.** Read **The Blueprint** below and collect its `###` dimension headings. If it defines no dimensions yet (the skeleton state), there is nothing to grade — report *"The blueprint is not yet defined."* and stop.
3. **Grade dimensions in parallel — one sub-agent per `###` dimension.** Spawn one read-only Sonnet 4.6 sub-agent per dimension (subagent_type: general-purpose, model: sonnet), all in a single message so they run concurrently. Each receives the shared base instructions below, plus the target path and exactly one `###` dimension — its heading, *what good looks like* line, and every rule and nested criterion, verbatim — as its assigned domain.

   **Base instructions (shared by all agents):**

   > You grade one dimension of a package against a blueprint. You are READ-ONLY — you propose work, you never edit the package. Do these in order:
   >
   > 1. Your criteria are **only the rules in your assigned `###` dimension** (given below) — every rule and every nested criterion. Do not grade against other dimensions; another agent owns each of those.
   > 2. Inspect the target package at the given path. **Verify each rule against the real artifact** — open the script, run its `--help`, `wc -l` the file — never trust a name or a doc line. If you need broader context, spawn an Explore sub-agent (model: sonnet) to search; don't guess.
   > 3. Grade each rule **met / partial / unmet / N/A**. Use N/A only when the rule's precondition doesn't hold (e.g. a Rust-only rule in a repo with no Rust), and say why.
   > 4. For every *partial* or *unmet* rule, draft one action item: a suggested priority (P0 blocking · P1 important · P2 polish), a one-line imperative title, the gap (what the rule wants vs. what the package has — name the path), and a concrete **Do** the next agent can act on without re-deriving the rule.
   >
   > Return a structured list headed by your dimension name: every rule's verdict, then the drafted action item for each gap.
4. **Merge and prioritize.** Collect all agents' results into one report: compute the met/total tally across every dimension, order the action items P0 → P1 → P2 (using each agent's suggested priority, normalized across dimensions), and deduplicate where two dimensions flag the same path (keep the higher-priority item).
5. **Report.** Output the prioritized action-item list per the format below. This skill is **read-only**: it proposes the work; it never edits the package. Implementing the items is a separate step (the user, or another agent).

## Output — action items

Lead with a one-line verdict: the met/total tally — N/A rules drop out of the denominator, noted separately — plus the action-item count (e.g. `12/15 rules met (3 N/A) — 6 action items`).

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
  - **Steps as a bullet list, not prose** — within each subsection the gates are listed one per line as bullets, in run order (a bullet for `ai_tools/build.sh`, then `ai_tools/test.sh`, then `ai_tools/style/`), with the loop discipline and exit condition as their own bullets — never collapsed into a prose run-on like *"run build → test → style, fix red, exit green"*. An agent ticks a checklist gate by gate; a sentence buries a gate and can't be checked off.
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

### ai_tools/

*What good looks like: the `ai_tools/` folder is the package's runnable harness — a complete set of wrapper scripts for every common task (clean, build, test, e2e) so an agent runs one short command instead of rebuilding a long one, and the script path is always the handle. (Scope: this dimension grades the folder itself; the CLAUDE.md `## AI Tools` section that catalogs the scripts is graded by the CLAUDE.md dimension.)*

**Shape — each tool is one script or one folder, same handle either way:**

- **A tool is either a flat `<tool>.sh` or a `<tool>/` folder fronted by `index.sh`** — pick by how much the task fans out; the caller invokes the same path regardless.
  - Single-step, single-language task → one script (e.g. `ai_tools/clean.sh`).
  - Fans out per language or component → a folder: `ai_tools/build/index.sh` does everything, with one runnable `build_<lang>.sh` beside it per source (`build_rs.sh`, `build_ts.sh`, `build_py.sh`).
  - **`index.sh` is the front door** — it runs the whole set so the caller never needs to know which sub-scripts exist; each per-source script stays individually runnable for a single-language pass.
  - **`index.sh` fails fast** — when any sub-script exits non-zero it aborts there and propagates that exit code (e.g. `set -e`); it never swallows the error or runs on to the next source, so a failed build can't read as green.

**Required tools — every package ships these four:**

- **`build.sh`** (or `build/`) — builds all sources from one handle.
  - Polyglot repos use the folder form: one `build_<lang>.sh` per source (`build_rs.sh`, `build_ts.sh`), each independently runnable, with `index.sh` chaining them all.
- **`test.sh`** (or `test/`) — runs the full unit-test suite from one handle; fans out per language like build when the repo is polyglot.
- **`style/`** (always a folder) — `index.sh` runs format, lint, and a file-size check over every source.
  - **Always a folder, never a flat `style.sh`** — it bundles several concerns (format, lint, file-size check, and their per-language variants), too many for one script.
  - Covers `format.sh` and `lint.sh`, or language-oriented `format_rs.sh`/`format_py.sh` and `lint_rs.sh`/`lint_py.sh` when polyglot, all chained by `index.sh`.
  - **Both format and lint auto-fix, then fail on the remainder** — each runs in write/fix mode to apply every fix it can, then exits non-zero if anything unfixable is left, so style problems surface as a hard failure instead of silent drift.
  - **`file_size_check.sh` caps non-test source files at 500 lines** — it hard-fails (exit non-zero), not an informational report, on any non-test service-code file (`.rs`, `.ts`, …) over the cap; large files are slow and costly for an agent to edit, so going over usually signals the architecture needs splitting or a refactor. Test files are exempt.
  - **Rust tests live in separate files from service code (when the project has Rust)** — a `style/` check fails if test code sits inline in a service file; Rust tests go in their own `*_tests.rs` files beside the code they cover, never `#[cfg(test)]` blocks inside the service file. Keeping tests out of service files holds those files under the size cap and leaves room to grow service coverage. N/A when the project has no Rust.
- **`e2e_test.sh`** (or `e2e_test/`) — runs the full end-to-end suite from one handle, kept separate from the unit suite (different runtime and cost).

**Recommended tools — ship when useful, not enforced:**

- **`clean.sh`** (or `clean/`) — removes build artifacts and bundles for *every* language in the package, not just one. **Recommended, not forced for now** — its absence is **not** a gap (mark N/A); grade the criteria below only when the package actually ships it.
  - Covers each language present: Rust `target/` and binaries, Python `__pycache__`/`*.pyc`/`.venv`, Node `node_modules`/`dist`, plus any other generated output the repo produces.
  - **Verify by reading the script, not the name** — open it and confirm it actually deletes each language's artifacts the repo contains; a package with a Python source but a clean that only sweeps Rust is a gap.

**Language-specific tools — shipped when that language is present:**

- **`clean_rust_old_binaries.sh`** (Rust only) — prunes *stale* Rust build artifacts older than a day, and runs itself after every commit so `target/` doesn't grow without bound between full cleans. Distinct from a full `clean.sh`: that wipes all artifacts on demand; this drops only the old ones, automatically.
  - **Sweeps by age, keeps today's** — runs `cargo sweep --time 1` at the project root: deletes build artifacts older than one day while keeping anything built or touched today. It is not a full clean and touches no other language.
  - **Wired to the post-commit hook** — the git post-commit hook (e.g. `.cargo-husky/hooks/post-commit`) invokes it after every commit, fire-and-forget (backgrounded, off the commit path) so cleanup is automatic and never delays the commit. Verify by reading the hook that it actually calls the script, not merely that the script exists.
  - **Never installs on the commit path** — the hook guards on `cargo-sweep` already being present and skips silently when it's absent, so a commit can't trigger a `cargo install`; the script itself auto-installs `cargo-sweep` only on a manual run.
  - **N/A when the project has no Rust.**

<!--
TEMPLATE — copy per new dimension; write each rule as a bullet with nested criteria:

### <Dimension name>

*What good looks like: <one-line focus for this dimension>.*

- **<Rule name>** — <one-line essence; recommended section heading if it maps to one>.
  - <checkable criterion>.
  - <checkable criterion>.
-->
