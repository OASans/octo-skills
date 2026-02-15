# Coding Guide

## General Principles

## File Size
Files under 500 lines. One responsibility per file.

## Dependency Hierarchy
Child modules consumed only by parent. Shared types at shared level, not buried in sibling modules.

## Testability
Code must be testable. If untestable, fix architecture first.

## Unit Test Coverage
Target 100% coverage. If code is hard to test, the architecture needs fixing — not the test strategy.

## Meaningful Function Extraction
Functions must encapsulate real logic, not just forward to another function. Names should make architecture self-documenting at every level — reading call sites should explain the flow without comments.

## Eliminate Duplication
Repeated patterns should be extracted into helpers. One place to change, one place to break.

## Consolidate Constants
No magic strings or hardcoded values scattered across files. Centralize into constants.

## Split Large Types
Types mixing config, runtime state, and tracking into one blob should be split by concern.

## Consistent Error Handling
Pick one strategy per layer. Don't mix error handling styles arbitrarily. Add context to errors — a bare I/O error without "what failed" is unhelpful. Every error must be logged before propagating or handling.

## No Premature Abstraction
Don't extract a helper until the same pattern appears 3+ times. Inline duplication is better than a wrong abstraction.

## Minimal Public API
Export the minimum needed. Every public function/type is a maintenance burden.

## Fail Fast
Validate at system boundaries (user input, external APIs). Don't add defensive checks deep in internal code.

## No Dead Code
No commented-out code, unused imports, or unreachable branches. Delete it.

## General
Reduce coupling. Simplify complex functions.

---

## Rust-Specific

- Extract into submodules, re-export from parent.
- Prefer references and `&str` over `.clone()`/`.to_string()` where ownership isn't needed.
- Don't mix `unwrap`/`expect`/`Box<dyn Error>`/custom error types arbitrarily within a layer.
- Add context to errors — bare `io::Error` without "what failed" is unhelpful.
- Testability strategies: CLI flags for test modes, trait interfaces for mocking, modular design for in-component testing.
