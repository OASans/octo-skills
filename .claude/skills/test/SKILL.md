---
---

Test-driven development workflow. Write failing tests first, then implement, then refactor.

Usage: `/test <description>` — describe what to test/implement

Context:
- Test status: `!cargo test-safe 2>&1 | tail -3`

Steps:

1. Parse `$ARGUMENTS` for feature/fix description.
2. Read relevant source files. Understand existing test patterns via Grep for `#[cfg(test)]` and `#[test]` in related modules.
3. **Red phase:** Write failing tests that define the expected behavior. Be explicit about edge cases. Run `cargo test-safe` to confirm they fail. If tests pass already, the feature exists — report and stop.
4. **Green phase:** Implement the minimum code to make tests pass. Run `cargo test-safe` after each change. Do not gold-plate.
5. **Refactor phase:** Clean up implementation while keeping tests green. Run `cargo test-safe` after each refactor step.
6. Final verification: `cargo dev`, `cargo clippy --all-features --quiet -- -D warnings`, `cargo fmt --check`.
7. Report: tests added (names + file paths), implementation summary, any edge cases not covered.

Rules:
- Never skip the red phase. Tests must fail before implementation.
- One test function per behavior. Descriptive names: `test_<what>_<condition>_<expected>`.
- Tests go in the same file's `#[cfg(test)] mod tests` block unless it's an integration test.
- If `$ARGUMENTS` describes a bug, write a regression test that reproduces it first.
