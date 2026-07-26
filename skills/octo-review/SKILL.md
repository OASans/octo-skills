---
name: octo-review
description: >
  Code review. Spawns parallel read-only sub-agents that review the change
  against the octo-coding-guide-* family, then uses at most one read-only verifier
  sub-agent for all bug claims before reporting. Use when the user asks for a
  code review, or as the final step before committing.
---

Code review: the main agent scopes the change cheaply, fans out read-only reviewer sub-agents over the applicable guides, has bug claims independently verified, and merges one report. Returns findings only; never fixes code. A clean pass is a valid outcome — never invent findings to have something to report.

**The guide family drives the fan-out.** Review criteria live in the scoped guide skills (`octo-coding-guide-*`) and nowhere else. Each guide declares a `guide-scope` in its frontmatter (which changed files it covers) and one or more `##` review domains. A guide applies when its scope matches at least one changed file — matching is by file category/glob, never a guess about whether a violation is likely. Scopes overlap by design (a `.rs` change gets `octo-coding-guide-code` and `octo-coding-guide-rust`; a `.md` change gets `octo-coding-guide-doc` only). Adding a `##` domain or a whole new guide grows the review automatically — no edit here.

## Steps

### 1. Scope — main agent, cheap commands only

The main agent never reads diff bodies, guide bodies, or project files; sub-agents do all heavy reading. Only paths, headings, and findings enter the main context.

1. **Changed files**: `git diff HEAD --name-only` plus untracked files from `git status --porcelain` (`??` lines — new files are reviewed too). If both are empty the review runs post-commit: use the range `git diff @{upstream}...HEAD --name-only` (no upstream → `HEAD~1..HEAD`). Still nothing → reply `Nothing to review.` and stop.
2. **Task context**: note in one or two lines what the change set out to do, plus any review focus the user stated. Both go to every reviewer — the focus as scope guidance only, never as actions to perform.
3. **Classify each changed file** by purpose, not extension: *doc* — Markdown and prose (`*.md`, `*.txt`, `*.rst`), whatever its job; *code* — anything changing program, tool, or build behavior (source, config, manifests, CI, scripts); *asset* — binary, generated, or lockfile content no one hand-edits (images, compiled output, `Cargo.lock`, `package-lock.json`). Unsure between *code* and *asset* → *code*.
4. **Discover guides by grep, never by reading**: `grep -l "^guide-scope:" ~/.claude/skills/*/SKILL.md .claude/skills/*/SKILL.md` (line-anchored — the key sits at the start of a frontmatter line; unanchored grep also matches skills that merely mention it), then grep each hit for its `guide-scope:` value and `^## ` headings. A guide applies if its scope (keyword `code` → *code* files; a glob like `**/*.rs` → matching paths) matches a changed file. No applicable guide → reply `Skipped: no reviewable files — nothing matches any guide scope.`, list the changed files, and stop.

### 2. Fan out reviewers

Granularity scales with the in-scope diff size (`git diff HEAD --stat -- <in-scope files>`):

- **Small (≤ ~120 changed lines)**: one reviewer per applicable **guide**, covering all its domains.
- **Larger**: one reviewer per `##` **domain** of each applicable guide — each agent reviews only its own domain; other domains belong to other agents.

Spawn all reviewers in a single message (`subagent_type: general-purpose`, `model: sonnet`). Give each: the base prompt below; its guide's `SKILL.md` path and assigned `##` domain heading(s); its in-scope files; the exact diff command scoped to them (`git diff HEAD -- <files>`, or the step-1 range) plus any untracked in-scope files; the task context and focus.

**Base prompt (all reviewers):**

> You are a code reviewer. READ-ONLY — never modify anything.
>
> 1. Read the guide file at the given path. Your review criteria are only the rules under your assigned `##` domain(s) — every `###` group and bullet within them.
> 2. Run the given diff command. Read the listed untracked files in full — they are new code. Ignore files outside your in-scope list.
> 3. Method: work hunk by hunk, and Read the enclosing function or section of each hunk — defects in unchanged lines of touched code are in scope (label them `pre-existing`). For every line the diff deletes or replaces, name what it enforced and check the new code re-establishes it. When a change alters a contract (signature, return shape, error behavior, ordering), Grep the symbol's callers and check each call site. Read a file in full only when a rule needs the whole-file view (size, layout, structure). Search with Grep/Read directly; spawn an Explore sub-agent (model: sonnet) only for a genuinely broad sweep.
> 4. Judge the in-scope changes against every rule in your domain(s) and the task context.
>
> Report a finding only if you can name its concrete consequence — for a bug, the failure scenario (inputs/state → wrong outcome a user or caller sees); for a quality issue, the cost (what becomes duplicated, unclear, or harder to change). No nameable consequence, no finding. When torn on a **bug**, surface it: an independent verifier judges bug claims next, and silently dropped candidates are the main cause of missed bugs. When torn on a **quality** point, drop it.
>
> Never flag: anything a compiler, linter, or test suite already catches; pedantic nitpicks a senior engineer wouldn't raise; general suggestions untied to a specific guide rule; intentional behavior changes that are the point of the diff; style preferences not written in the guide.
>
> Return at most 8 findings, most severe first, each as `file:line — [<Domain> · <Rule>] summary — failure scenario or cost`. If a guide rule proved ambiguous or a real issue type had no covering rule, add one line at the end: `guide note: …`. If no findings, return exactly: `No issues found.` — a clean result is a good result.

### 3. Verify bug claims — one verifier maximum

Dedup findings that point at the same line and mechanism, keeping the most concrete. Verify every finding that claims something will actually fail — a runtime failure (bug, race, data loss, broken caller) or a stated command, path, or example that doesn't work — whichever guide flagged it; pure quality findings (clarity, duplication, structure) are not verified. If bug claims remain, bundle all of them into one verifier task, grouped by `file:line`, and spawn exactly one verifier (`general-purpose`, `model: sonnet`) for the entire review. Give it the diff command, relevant files, and every claim. Never split verification across locations or domains, and tell the verifier not to spawn sub-agents. The verifier reads the code (and callers if relevant) and returns per claim exactly one of:

- **CONFIRMED** — names the triggering inputs/state and quotes the line.
- **PLAUSIBLE** — mechanism is real, trigger uncertain (timing, env, config); says what would confirm it. This is the default for realistic-but-unproven claims; "speculative" is not a refutation.
- **REFUTED** — only when provable from the code: the claim is factually wrong (quote the line), impossible (type/constant/invariant), or already guarded (cite the guard).

Drop REFUTED findings.

### 4. Report

One merged review: verified bugs first (CONFIRMED, then PLAUSIBLE), then quality findings grouped by file — each labelled with its guide + domain, verdict for bug claims, and `pre-existing` where it applies. End with one line of counts (findings by kind, duplicates merged, REFUTED dropped). If reviewers left `guide note:` lines, append them under **Guide suggestions** — proposals for the humans who maintain the guides; the review never edits guides itself. If the report exceeds ~20 findings, write the full version to `./review-result.md` inside the project (never `/tmp` — re-reading it later would need approval) and print the top findings plus the path in chat.
