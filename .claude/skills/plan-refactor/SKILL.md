---
---

Tech lead pass: analyze codebase, refresh refactoring backlog. Read-only on source, write-only on tracker.

Downstream: tracker is consumed by `/batch` skill for automated execution. Optimize items for batch: self-contained (no implicit dependencies on other items), exact file paths, single atomic change that builds+tests independently.

## Rules

- Do NOT modify source code. Only modify `ai-doc/refactor/tracker.md`.
- Every item needs: file path, line count, specific action, principle category.
- Item format: `- [ ] **#N** \`path\` (N lines) — action description`
- Numbers are stable, never reused. New items get max existing + 1.
- Right-size items for batch subagents: each item should be ~200-300 lines of changes. Too small (a few lines) wastes subagent overhead; too large overwhelms context. Group related small fixes in the same file into one item. Split large refactorings into independent stages.

## Steps

1. Read CLAUDE.md. Find a reference to a coding guide or code quality principles document. If CLAUDE.md does not reference any coding guide or quality principles, tell user and stop.
2. Read the coding guide found in step 1. These principles drive the scan.
3. Read tracker if it exists. Note highest item number. Verify each existing `[ ]` item — Glob the file path. Delete if file missing or issue fully addressed. Update if line count changed.
4. Scan codebase using `Task` subagents in parallel. Derive scan categories from the coding guide principles (e.g., file size limits, error handling, duplication, large types, test coverage, dead code). Use language-appropriate patterns for each category.
5. Write new items grouped by `###` principle headers. Right-size each item: group related small findings in the same file into one item; split large changes into independent stages. Aim for items a subagent can complete in one focused pass (~200-300 lines of changes).
6. Write updated tracker to `ai-doc/refactor/tracker.md`. Structure:
   - Header with `/batch ai-doc/refactor/tracker.md` usage note.
   - **Task** section — tells batch subagents what to do: read source file, read the coding guide, apply the refactoring described, verify with the project's build/test/lint/fmt commands (found in CLAUDE.md), ensure existing behavior is preserved. This section is critical — without it, batch subagents won't know the tracker is about refactoring.
   - **Tips for Subagents** section — populated from CLAUDE.md and codebase analysis. Include: build/test/lint commands, coding conventions, testing patterns, any project-specific guidance batch subagents need to execute without exploring the codebase.
   - **Backlog** section — items grouped by `###` principle headers, using the item format from Rules.
7. Report summary: items deleted, items added, top principles.
