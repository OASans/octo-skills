# Coding Guide

## Architecture

- **File Size**: Files under 500 lines. One responsibility per file.
- **Dependency Hierarchy**: Child modules consumed only by parent. Shared types at shared level, not buried in sibling modules.
- **Split Large Types**: Types mixing config, runtime state, and tracking into one blob should be split by concern.
- **Minimal Public API**: Export the minimum needed. Every public function/type is a maintenance burden.
- **Reduce Coupling**: Minimize dependencies between modules. Simplify complex functions.

## Code Clarity

- **Clarity Over Brevity**: Prefer explicit, readable code over compact one-liners. If a "simplification" makes the code harder to read, it's not simpler.
- **Flat Control Flow**: Use early returns and guard clauses to reduce nesting. Deeply nested blocks signal a function doing too much.
- **Meaningful Function Extraction**: Functions must encapsulate real logic, not just forward to another function. Names should make architecture self-documenting at every level.
- **One Concern Per Function**: Don't stuff multiple responsibilities into a single function. Each function should do one thing well.
- **Consolidate Constants**: No magic strings or hardcoded values scattered across files. Centralize into constants.

## Duplication & Abstraction

- **Eliminate Duplication**: Repeated patterns should be extracted into helpers. One place to change, one place to break.
- **No Premature Abstraction**: Don't extract a helper until the same pattern appears 3+ times. Inline duplication is better than a wrong abstraction.
- **No Dead Code**: No commented-out code, unused imports, or unreachable branches. Delete it.

## Error Handling & Debugging

- **Consistent Error Handling**: Pick one strategy per layer. Don't mix styles arbitrarily. Add context to errors — a bare error without "what failed" is unhelpful.
- **Fail Fast**: Validate at system boundaries (user input, external APIs). Don't add defensive checks deep in internal code.
- **Debuggability**: Write code that's easy to debug. Avoid opaque transformations — intermediate variables with descriptive names beat long chains.

## Testing

- **Testability**: Code must be testable. If untestable, fix architecture first.
- **Unit Test Coverage**: Target high coverage. If code is hard to test, the architecture needs fixing — not the test strategy.
