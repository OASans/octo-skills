---
---

Code review. Spawns a read-only sub-agent to review all uncommitted changes against the coding guide, then fixes violations.

Designed for use by both humans and AI agents. Run this at the end of any coding workflow before committing.

Context:
- Coding guide: `!cat doc/coding-guide.md`

## Steps

1. Collect all uncommitted changes: `git diff` (unstaged) + `git diff --cached` (staged). If both empty, report "nothing to review" and stop.
2. Spawn a Task sub-agent (subagent_type: general-purpose) with:
   - The full diff
   - The coding guide (from context above)
   - Instruction: review the diff against each coding guide principle AND the review checklist below. For each violation: cite exact file:line, state which principle is violated, give specific fix instructions. Skip principles with no violations. The sub-agent is read-only — it only analyzes, never modifies code.
   - Review for:
     - **Correctness:** Logic errors, off-by-one, missing error handling, panics in non-test code.
     - **Race conditions:** Shared mutable state, channel usage, thread safety.
     - **Edge cases:** Empty inputs, boundary values, overflow, timeout handling.
     - **Consistency:** Naming conventions, patterns from surrounding code, CLAUDE.md conventions.
     - **Security:** Command injection, path traversal, unchecked user input.
     - **Tests:** Are changes covered? Missing test cases?
3. Present the sub-agent's review findings.
4. Fix each violation identified.
