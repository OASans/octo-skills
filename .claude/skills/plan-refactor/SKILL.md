---
---

Tech lead pass: analyze codebase, refresh refactoring backlog. Read-only on source, write-only on tracker.

Downstream: consumed by `/batch`. Items must be self-contained, exact file paths, single atomic change that builds+tests independently.

## Rules

- Do NOT modify source code. Only modify `ai-doc/refactor/tracker.md`.
- Item format: `- [ ] **#N** \`path\` (N lines) — action description`
- Numbers stable, never reused. New items get max existing + 1.
- Right-size: ~200-300 lines of changes per item. Group small fixes in same file; split large refactorings into independent stages.

## Steps

1. Read CLAUDE.md. Find coding guide / code quality principles. If none found, tell user and stop.
2. Read the coding guide. These principles drive the scan.
3. Read tracker if exists. Note highest item number. Verify each `[ ]` item — delete if file missing or issue resolved, update if line count changed.
4. Scan codebase via parallel `Task` subagents. Derive categories from coding guide principles (file size, error handling, duplication, large types, test coverage, dead code, etc.).
5. Write `ai-doc/refactor/tracker.md`: header with `/batch ai-doc/refactor/tracker.md` usage, **Context** section (what the subagent should do: read source file, read the coding guide, apply the refactoring, run build/test/lint/fmt, preserve existing behavior, "do NOT change unrelated code"; project guidance from CLAUDE.md + analysis: build commands, coding conventions, testing patterns), **Backlog** section (items grouped by `###` principle headers).
6. Report summary: items deleted, items added, top principles.
