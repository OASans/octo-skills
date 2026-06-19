---
name: octo-review
description: >
  Code review. Spawns parallel read-only sub-agents that independently review
  from different perspectives. Use when the user asks for a code review, or
  as the final step before committing.
---

Code review. Spawns parallel read-only sub-agents that independently collect the diff, read their assigned guide, and review from different perspectives — keeping the main agent's context clean. Returns findings only; does not fix code.

Designed for use by both humans and AI agents. Run this at the end of any coding workflow before committing.

**The guide family drives the fan-out.** Review criteria live in a family of scoped guide skills (`octo-*-guide` — e.g. `octo-coding-guide`, `octo-rust-guide`, `octo-doc-guide`). Each guide declares a `guide-scope` in its frontmatter (which changed files it covers) and contains one or more `##` review domains. This skill discovers the guides, keeps the ones whose scope the diff actually touches, and spawns one read-only sub-agent per `##` domain within them. Each agent reviews **only** its one domain, so domains are partitioned with no overlap. Add a `##` domain to a guide, or add a whole new guide skill, and the fan-out grows automatically — no edit here.

The result: a change is reviewed only against the guides that fit it. A `.rs` change is reviewed by `octo-coding-guide` (general code) **and** `octo-rust-guide`; a `.md` change is reviewed by `octo-doc-guide` only — code-correctness rules never fire on prose. Scope matching is by file category/glob, never a guess about whether a violation is likely, so no applicable domain is ever dropped.

## Steps

1. **Discover the guides.** Search `~/.claude/skills/*/SKILL.md` and the project's `.claude/skills/*/SKILL.md` for files whose frontmatter contains a `guide-scope:` key — each is a guide. For each, note its `guide-scope` value and its top-level `##` domain headings (ignore the `#` title and every `###` sub-heading). Before spawning, the main agent does **only** this read plus the file detection in Step 2 — do **not** collect the full diff or read project files yourself; the sub-agents do all of that.

2. **Detect and classify changed files (paths only, not diff content)** with `git diff --name-only` and `git diff --cached --name-only`. Keep the list with each file's category; Step 3 matches it against each guide's `guide-scope`.

   - **No changes at all** → return `Nothing to review.` and stop.
   - **Classify each changed file by purpose, not extension:**
     - *doc* — Markdown and prose documents (`*.md`, `*.txt`, `*.rst`), whatever their job (README, design/handover doc, `SKILL.md`, `CLAUDE.md`).
     - *code* — anything that changes program, tool, or build behavior: source in any language; config and manifests (`Cargo.toml`, `package.json`, `*.toml/yaml/yml/json`, lockfiles, `Dockerfile`); CI/build/scripts (`.github/`, `Makefile`, `*.sh`).
     - *asset* — binary or generated artifacts no guide reviews (images, fonts, compiled output).
     - When unsure between *code* and *asset*, classify as *code*.

3. **Match guides to the change, then spawn one parallel Sonnet 4.6 sub-agent per `##` domain of every applicable guide** (subagent_type: general-purpose, model: sonnet), all in a single message so they run concurrently.

   **Match first.** A guide is applicable if its `guide-scope` matches at least one changed file:
   - scope keyword `code` → matches any file in the *code* category.
   - scope glob (e.g. `**/*.rs`, `**/*.md`) → matches files whose path matches the glob.

   Guides may overlap — a `.rs` file matches both `octo-coding-guide` (`code`) and `octo-rust-guide` (`**/*.rs`); that is intended. Spawn agents only for the `##` domains of applicable guides; silently skip the rest.

   - **No guide is applicable** (e.g. only *asset* files changed) → return `Skipped: no reviewable files — nothing matches any guide scope.`, list the changed files, and stop.

   Each agent is given exactly one `##` domain (its heading, `*Review focus:*` line, and all `###` groups/bullets, verbatim) plus the **in-scope files** for its guide (the changed files its guide's scope matched) and the shared base instructions below.

   **Base instructions (shared by all agents):**

   > You are a code reviewer. You are READ-ONLY — never modify anything. Perform these steps in order:
   >
   > 1. Your review criteria are **only the rules in your assigned `##` domain** (given to you below) — including every `###` group and bullet within it. Do not review against other domains; another agent owns each of those. Also check the project's CLAUDE.md for any project-level rules that fall in your domain, and include those too.
   > 2. Collect the uncommitted changes: `git diff` (unstaged) and `git diff --cached` (staged). Review only your in-scope files (listed for you below); ignore changes to files outside your guide's scope — another agent or guide owns those.
   > 3. Read each in-scope file in full to understand surrounding context (not just the diff hunks).
   > 4. If you need broader context to assess an issue (e.g. how a function is used elsewhere, whether a pattern matches the rest of the codebase), spawn an Explore subagent (model: sonnet) to search for it. Don't guess — verify.
   > 5. Review the in-scope changes against every rule in your assigned domain.
   >
   > For each violation: cite exact file:line, name the violated principle (domain + bullet name), and give a specific description of the issue. Skip principles with no violations.
   >
   > **Do NOT flag false positives.** The following are NOT issues:
   > - Things a compiler, linter, or test suite would catch (type errors, unused imports, formatting)
   > - Pedantic nitpicks a senior engineer wouldn't flag
   > - General quality suggestions not tied to a specific guide principle (e.g. "consider adding docs")
   > - Intentional functionality changes that are clearly part of the broader change
   > - Style preferences not explicitly called out in the guide
   >
   > Return your findings as a structured list headed by your assigned domain name. If you find no issues, return: "No issues found."

4. Present all agents' findings as a unified review. Group by file, deduplicate overlapping findings, and label each issue with the domain (the `##` heading) and guide that flagged it.

## Writing large results to a file

If the unified review is too large to comfortably fit in the chat (more than ~50 findings, or you need to preserve the raw output from all agents verbatim), write it to a file **inside the current project directory** — not `/tmp`. Files under `/tmp` sit outside the working directory and require a user approval prompt to re-read later, which defeats the purpose of caching the result.

Good path: `./review-result.md` or `./.claude/review-<timestamp>.md` in the current project.
Bad path: `/tmp/review.md`, `~/review.md`, or any absolute path outside the current repo.

When writing to a file, still print a short summary (top findings + path to the file) in chat so the user doesn't have to open the file to see the headline results.
