---
name: plan-refactor
description: >
  Tech lead pass: analyze codebase, refresh refactoring backlog. Use when the
  user asks to find refactoring opportunities, clean up code, or refresh the
  refactor tracker.
model: opus
---

Tech lead pass: analyze codebase, refresh refactoring backlog. Read-only on source, write-only on tracker.

Downstream: consumed by `/yz-batch`. Items must be self-contained, exact file paths, single atomic change that builds+tests independently.

## Rules

- Do NOT modify source code. Only modify `ai-doc/refactor/tracker.md`.
- Item format: `- **#N** \`path\` (N lines) — action description`
- Numbers stable, never reused. New items get max existing + 1.
- Right-size: ~200-300 lines of changes per item. Group small fixes in same file; split large refactorings into independent stages.

## Steps

1. Invoke the `/coding-guide` skill to get the coding guide. Also check CLAUDE.md for any additional project-level coding guide and read that too if found. All coding guides drive the scan.
2. Read tracker if exists. Note highest item number. Verify each item — delete if file missing or issue resolved, update if line count changed.
3. Scan codebase via parallel Explore subagents (model: sonnet). Derive categories from coding guide principles (file size, error handling, duplication, large types, test coverage, dead code, etc.). Collect their findings — the main agent (opus) synthesizes them into the tracker.
4. Write `ai-doc/refactor/tracker.md`: header with `/yz-batch ai-doc/refactor/tracker.md` usage, then sections grouped by `###` principle headers. Each section has a **Context** block before its items — like a plan mode brief so the subagent doesn't research from scratch. Context includes: which coding guide points apply to this section, the planning agent's analysis of the problem (what's wrong, why it matters), and suggested approach for fixing (key files read, patterns observed, specific refactoring strategy). Share your findings — the subagent should be able to start implementing immediately.
5. Report summary: items deleted, items added, top principles.
