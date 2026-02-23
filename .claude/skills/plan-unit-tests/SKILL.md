---
---

Analyze coverage gaps, produce batch-compatible unit test tracker. Read-only on source, write-only on tracker/issues.

Downstream: consumed by `/batch`. Items must be self-contained with exact file paths, uncovered line ranges, specific test cases.

## Rules

- Do NOT modify source code. Only write `ai-doc/unit-tests/tracker.md` and `ai-doc/unit-tests/issues.md`.
- Tests only: items add/modify test code only. Never refactor source. If code needs refactoring first → `issues.md`.
- Item format: `- \`path\` (N lines, M% covered) — test descriptions with line refs`
- Right-size: group small uncovered regions per file; split files with many gaps by function. Each item completable in one subagent pass.
- Each unit test must mock/stub all dependencies. If mocking isn't possible → `issues.md`.
- Tracker regenerated fresh each run.

## Steps

1. Read CLAUDE.md. Find coverage command/script. If none, tell user and stop.
2. Analyze existing tests for conventions: location pattern, framework/assertions, naming, mocking strategy, fixtures/helpers, error testing, snapshot usage.
3. Run coverage command. Parse per-file coverage and uncovered line ranges.
4. For each file with uncovered lines: read source, categorize as **testable** (can unit-test directly) or **blocked** (needs refactoring first).
5. Write `ai-doc/unit-tests/tracker.md`: header with `/batch ai-doc/unit-tests/tracker.md` usage, then sections grouped by `###` module/directory. Each section has a **Context** block before its items — the planning agent's analysis of coverage gaps, existing test conventions found in step 2, relevant mocking strategies, and suggested approach for writing the tests (key functions to cover, edge cases identified, patterns from neighboring tests). Share your findings so the subagent can start implementing immediately.
6. Write `ai-doc/unit-tests/issues.md`: header, one `###` per blocked file (path, line count, coverage %, blocking reason, affected lines, cross-ref to refactor tracker).
7. Report summary: files analyzed, total items, files blocked.
