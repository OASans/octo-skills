---
name: review
description: >
  Code review. Spawns parallel read-only sub-agents that independently review
  from different perspectives. Use when the user asks for a code review, or
  as the final step before committing.
---

Code review. Spawns parallel read-only sub-agents that independently collect the diff, read the coding guide, and review from different perspectives — keeping the main agent's context clean. Returns findings only; does not fix code.

Designed for use by both humans and AI agents. Run this at the end of any coding workflow before committing.

**The coding guide drives the fan-out.** Each `##` major section in `/coding-guide` is one review domain reviewed by one dedicated sub-agent. The number of agents tracks the guide: add a `##` section there and this skill spawns one more agent automatically, with no edit here. Each agent reviews **only** its assigned section, so domains are partitioned with no overlap.

## Steps

1. **Determine the review domains.** Run `/coding-guide` and list its top-level `##` section headings — ignore the `# Coding Guide` title and every `###` sub-heading. Each `##` section is one review domain. Before spawning, the main agent does **only** this read plus the file-name detection in Step 2 — do **not** collect the full diff or read project files yourself; the sub-agents do all of that.

2. **Detect changed files; skip if documentation-only.** List changed paths only — *not* diff content — with `git diff --name-only` and `git diff --cached --name-only`.

   - **No changes at all** → return `Nothing to review.` and stop. Do not spawn agents.
   - **Classify each changed file by purpose, not extension:**
     - *Documentation* — human-facing prose whose change alters no program, tool, skill, or build behavior (e.g. `README`, `CHANGELOG`, `CONTRIBUTING`, `LICENSE`, prose under `docs/`).
     - *Code* — anything that changes behavior: source in any language; **skill definitions and prompt files such as `skills/**/SKILL.md` (here markdown *is* the deliverable, not docs)**; config and manifests (`Cargo.toml`, `package.json`, `*.toml/yaml/yml/json`, lockfiles, `Dockerfile`); CI/build/scripts (`.github/`, `Makefile`, `*.sh`).
     - When unsure, classify as code. Skipping is the exception; the default is to review.
   - **Every changed file is documentation** → return `Skipped: documentation-only change — no code files modified.`, list the changed files, and stop. Do **not** spawn agents.
   - **Any code file is present** → proceed to Step 3. The change is reviewed normally (agents still see the full diff, doc files included).

3. **Spawn one parallel Sonnet 4.6 sub-agent per `##` section** (subagent_type: general-purpose, model: sonnet), all in a single message so they run concurrently. Each agent receives the shared base instructions below plus exactly one `##` section (its heading, `*Review focus:*` line, and all `###` groups/bullets, verbatim) as its assigned domain.

   **Base instructions (shared by all agents):**

   > You are a code reviewer. You are READ-ONLY — never modify code. Perform these steps in order:
   >
   > 1. Run `/coding-guide` to load the shared coding guide. Also check CLAUDE.md for any additional project-level coding guide and read that too if found.
   > 2. Your review criteria are **only the rules under your assigned `##` section** (given to you below) — including every `###` group and bullet within it. Do not review against other sections; another agent owns each of those. If a project-level CLAUDE.md adds rules that fall in your domain, include those too. If no coding guide exists, fall back to general software engineering best practices for your domain only.
   > 3. Collect all uncommitted changes by running: `git diff` (unstaged) and `git diff --cached` (staged). If both are empty, return: "Nothing to review." and stop.
   > 4. Read each changed file in full to understand surrounding context (not just the diff hunks).
   > 5. If you need broader context to assess an issue (e.g., how a function is used elsewhere, whether a pattern matches the rest of the codebase), spawn an Explore subagent (model: sonnet) to search for it. Don't guess — verify.
   > 6. Review the diff against every rule in your assigned section.
   >
   > For each violation: cite exact file:line, name the violated principle (section + bullet name), and give a specific description of the issue. Skip principles with no violations.
   >
   > **Do NOT flag false positives.** The following are NOT issues:
   > - Things a compiler, linter, or test suite would catch (type errors, unused imports, formatting)
   > - Pedantic nitpicks a senior engineer wouldn't flag
   > - General quality suggestions not tied to a specific coding guide principle (e.g. "consider adding docs")
   > - Intentional functionality changes that are clearly part of the broader change
   > - Style preferences not explicitly called out in the coding guide
   >
   > Return your findings as a structured list headed by your assigned section name. If you find no issues, return: "No issues found."

4. Present all agents' findings as a unified review. Group by file, deduplicate overlapping findings, and label each issue with the domain (the `##` section name) that flagged it.

## Writing large results to a file

If the unified review is too large to comfortably fit in the chat (more than ~50 findings, or you need to preserve the raw output from all agents verbatim), write it to a file **inside the current project directory** — not `/tmp`. Files under `/tmp` sit outside the working directory and require a user approval prompt to re-read later, which defeats the purpose of caching the result.

Good path: `./review-result.md` or `./.claude/review-<timestamp>.md` in the current project.
Bad path: `/tmp/review.md`, `~/review.md`, or any absolute path outside the current repo.

When writing to a file, still print a short summary (top findings + path to the file) in chat so the user doesn't have to open the file to see the headline results.
