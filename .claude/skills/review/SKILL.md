---
---

Code review. Spawns a read-only sub-agent to review all uncommitted changes against the coding guide, then fixes violations.

Designed for use by both humans and AI agents. Run this at the end of any coding workflow before committing.

## Steps

1. Read CLAUDE.md. Find a reference to a coding guide or code quality principles document. If CLAUDE.md does not reference any coding guide or quality principles, tell user: "No coding guide found in CLAUDE.md. This skill needs a coding guide or code quality principles document referenced in CLAUDE.md." Stop immediately.
2. Read the coding guide found in step 1.
3. Collect all uncommitted changes: `git diff` (unstaged) + `git diff --cached` (staged). If both empty, report "nothing to review" and stop.
4. Spawn a Task sub-agent (subagent_type: general-purpose) with:
   - The full diff
   - The coding guide (from step 2)
   - Instruction: review the diff against each coding guide principle AND the review checklist below. For each violation: cite exact file:line, state which principle is violated, give specific fix instructions. Skip principles with no violations. The sub-agent is read-only — it only analyzes, never modifies code.
   - Review for:
     - **Correctness:** Logic errors, off-by-one, missing error handling, panics in non-test code.
     - **Race conditions:** Shared mutable state, channel usage, thread safety.
     - **Edge cases:** Empty inputs, boundary values, overflow, timeout handling.
     - **Consistency:** Naming conventions, patterns from surrounding code, CLAUDE.md conventions.
     - **Security:** Command injection, path traversal, unchecked user input.
     - **Tests:** Are changes covered? Missing test cases?
5. Present the sub-agent's review findings.
6. Fix each violation identified.
