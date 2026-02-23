---
---

Code review. Spawns a read-only sub-agent that independently collects the diff, reads the coding guide, and reviews — keeping the main agent's context clean. Then fixes violations.

Designed for use by both humans and AI agents. Run this at the end of any coding workflow before committing.

## Steps

1. Spawn a single Task sub-agent (subagent_type: general-purpose) with the following instruction. Do NOT read any files or run any commands before spawning — the sub-agent does everything:

   > You are a code reviewer. Perform these steps in order:
   >
   > 1. Read the bundled [coding-guide.md](coding-guide.md) in this skill's directory. Also check CLAUDE.md for any additional project-level coding guide and read that too if found.
   > 2. Use all coding guides found as the review criteria.
   > 3. Collect all uncommitted changes by running: `git diff` (unstaged) and `git diff --cached` (staged). If both are empty, return: "Nothing to review." and stop.
   > 4. Read each changed file in full to understand surrounding context (not just the diff hunks).
   > 5. Review the diff against every coding guide principle AND the checklist below. For each violation: cite exact file:line, state which principle is violated, and give specific fix instructions. Skip principles with no violations.
   >
   > Review checklist:
   > - **Correctness:** Logic errors, off-by-one, missing error handling, panics in non-test code.
   > - **Race conditions:** Shared mutable state, channel usage, thread safety.
   > - **Edge cases:** Empty inputs, boundary values, overflow, timeout handling.
   > - **Consistency:** Naming conventions, patterns from surrounding code, CLAUDE.md conventions.
   > - **Security:** Command injection, path traversal, unchecked user input.
   > - **Tests:** Are changes covered? Missing test cases?
   >
   > Return your findings as a structured list. You are read-only — never modify code.

2. Present the sub-agent's review findings.
3. Fix each violation identified.
