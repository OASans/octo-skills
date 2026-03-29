---
name: review
description: >
  Code review. Spawns parallel read-only sub-agents that independently review
  from different perspectives. Use when the user asks for a code review, or
  as the final step before committing.
---

Code review. Spawns parallel read-only sub-agents that independently collect the diff, read the coding guide, and review from different perspectives — keeping the main agent's context clean. Returns findings only; does not fix code.

Designed for use by both humans and AI agents. Run this at the end of any coding workflow before committing.

## Steps

1. Spawn **three parallel Opus sub-agents** (subagent_type: general-purpose, model: opus). Do NOT read any files or run any commands before spawning — the sub-agents do everything. Each agent receives the same base instructions below, plus its own focus area.

   **Base instructions (shared by all agents):**

   > You are a code reviewer. You are READ-ONLY — never modify code. Perform these steps in order:
   >
   > 1. Check if a bundled [coding-guide.md](coding-guide.md) exists in this skill's directory. Also check CLAUDE.md for any additional project-level coding guide and read that too if found.
   > 2. Use all coding guides found as the review criteria. If no coding guide exists, use general software engineering best practices.
   > 3. Collect all uncommitted changes by running: `git diff` (unstaged) and `git diff --cached` (staged). If both are empty, return: "Nothing to review." and stop.
   > 4. Read each changed file in full to understand surrounding context (not just the diff hunks).
   > 5. If you need broader context to assess an issue (e.g., how a function is used elsewhere, whether a pattern matches the rest of the codebase), spawn an Explore subagent (model: sonnet) to search for it. Don't guess — verify.
   > 6. Review the diff against every coding guide principle AND your assigned focus area below.
   >
   > For each violation: cite exact file:line, state which principle is violated, and give specific description of the issue. Skip principles with no violations.
   >
   > **Do NOT flag false positives.** The following are NOT issues:
   > - Things a compiler, linter, or test suite would catch (type errors, unused imports, formatting)
   > - Pedantic nitpicks a senior engineer wouldn't flag
   > - General quality suggestions not tied to a specific coding guide principle (e.g. "consider adding docs")
   > - Intentional functionality changes that are clearly part of the broader change
   > - Style preferences not explicitly called out in the coding guide
   >
   > Return your findings as a structured list. If you find no issues, return: "No issues found."

   **Agent focus areas:**

   - **Agent A — Coding guide compliance:** Review the diff against every principle in the coding guide(s). Focus on architecture, code clarity, duplication, error handling, and testing guidelines. Flag only clear violations, not subjective preferences.

   - **Agent B — Bugs & correctness:** Scan for logic errors, off-by-one, missing error handling, unhandled exceptions, race conditions, shared mutable state, empty inputs, boundary values, overflow, timeout handling, command injection, path traversal, and unchecked user input. Focus on real bugs that would cause incorrect behavior.

   - **Agent C — Consistency & coherence:** Check that new code is consistent with patterns in the surrounding codebase. Look for naming mismatches, inconsistent error handling styles, API contract violations, and changes that break assumptions made elsewhere in the same files. Also check: are changes covered by tests? Missing test cases?

2. Present all three agents' findings as a unified review. Group by file, deduplicate overlapping findings, and note which perspective flagged each issue (guide compliance / bug / consistency).
