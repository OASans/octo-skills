---
---

Analyze coverage gaps, produce batch-compatible unit test tracker. Read-only on source, write-only on tracker/issues.

Downstream: tracker is consumed by `/batch` skill for automated execution. Optimize items for batch: self-contained, exact file paths + uncovered line ranges, specific test cases a zero-context subagent can implement.

## Rules

- Do NOT modify source code. Only write `ai-doc/unit-tests/tracker.md` and `ai-doc/unit-tests/issues.md`.
- Tests only: tracker items must only add/modify test code and test files. Never refactor, restructure, or change source code to make it testable. If code needs refactoring before it can be tested, put it in `issues.md` instead.
- Every item needs: file path, line count, current coverage %, uncovered line ranges, specific test descriptions.
- Item format: `- [ ] \`path\` (N lines, M% covered) — test descriptions with line refs`
- Items must be self-contained for batch subagents: include what to test, inputs, expected behavior.
- Right-size items for batch subagents: group small uncovered regions in the same file into one item; split files with many uncovered regions into multiple items by function/section. Each item should be completable in one focused subagent pass. Too small (one trivial test) wastes overhead; too large overwhelms context.
- Isolation: each unit test must only test its own component. All dependencies on other components must be mocked, stubbed, or avoided. If A depends on B, test A with B mocked — never import the real B. If mocking isn't possible, the code needs refactoring first — add it to `issues.md`, not the tracker.
- Tracker is regenerated fresh each run.

## Discovering Test Conventions

Before writing the tracker, analyze the codebase to populate the Tips section with project-specific guidance. Look for:

- **Test location**: co-located with source, separate test directory, or both? Note the pattern.
- **Test framework & assertion style**: which test runner, assertion macros/functions, and matcher libraries are used?
- **Naming convention**: how are test functions/methods named? (e.g., `test_<what>_<condition>_<expected>`, `should_<behavior>`, `describe/it` blocks)
- **Snapshot testing**: does the project use snapshot tests? If so, note the library and conventions. Even if not currently used, recommend snapshot tests where appropriate — config/fixture generation, serialization output, infrastructure constructs (CDK/Pulumi), large structured output, or any case where the full output matters and manual field-by-field assertions would be brittle. Include setup instructions in Tips if introducing snapshots for the first time.
- **Mocking & test doubles**: which mocking framework (if any)? Trait-based injection, dependency injection, monkey patching?
- **Fixtures & factories**: how is test data set up? Builder patterns, fixture files, factory functions?
- **Test helpers**: are there shared test utilities? Where do they live?
- **Error testing**: how are error cases tested? `should_panic`, `assert_err`, `expect().toThrow()`?

Summarize findings as concise bullet points in the tracker's Tips section so batch subagents can write consistent tests without exploring the codebase themselves.

## Steps

1. Read CLAUDE.md to find the project's coverage command/script. If no coverage tool is documented, tell user and stop.
2. Analyze existing tests in the codebase to discover conventions (see "Discovering Test Conventions" above).
3. Run the coverage command. Parse the per-file coverage table and uncovered line ranges.
4. For each file with uncovered lines, read the source file. Categorize each uncovered region:
   - **Testable**: logic can be unit-tested directly or with minor test helpers.
   - **Blocked**: needs refactoring first (tightly coupled to I/O, global state, untestable architecture). Cross-reference with refactor tracker items.
5. Create `ai-doc/unit-tests/` directory if it doesn't exist.
6. Write `ai-doc/unit-tests/tracker.md`. Structure:
   - Header with `/batch ai-doc/unit-tests/tracker.md` usage note.
   - **Task** section — tells batch subagents what to do: read source file, read existing tests, write new unit tests covering uncovered lines, follow conventions, verify with build/test/lint/fmt/coverage scripts. Must prominently state: "Only add/modify test code and test files. Do NOT refactor, restructure, or change source code. If code is untestable as-is, skip it." This section is critical — without it, batch subagents won't know the tracker is about writing unit tests.
   - **Tips for Subagents** section — populated from convention discovery. Include subsections for: Conventions, Snapshot Tests, Mocking & Isolation, General. The General subsection must include the isolation rule, the test-only restriction, and guidance on matching existing test style.
   - **Backlog** section — items grouped by `###` module/directory headers, using the item format from Rules.
7. Write `ai-doc/unit-tests/issues.md`. Structure:
   - Header explaining these are files that need refactoring before full coverage is possible.
   - One `###` section per blocked file. Each section includes: file path, line count, current coverage %, what's blocking testability (e.g., tightly coupled to I/O, global state, no dependency injection), which specific lines/functions are affected, and a cross-reference to the relevant refactor tracker item if one exists.

8. Report summary: total files analyzed, total items, files blocked in issues.
