---
name: coding-guide
description: >
  Print the shared coding guide. Inline skill — no sub-agents. Use as a
  reference for code reviews, implementation decisions, and plan evaluation.
---

# Coding Guide

## Module & Boundary Design

Every unit (module, struct, trait) must answer three questions: what does it do, how do you use it, what does it depend on?

- **Understandable from Outside**: A consumer should understand what a unit does from its public API alone, without reading internals. If they can't, the interface is leaking implementation details.
- **Changeable Internals**: You should be able to restructure a unit's internals without breaking consumers. If you can't, the boundary is in the wrong place.
- **Coherent Interfaces**: A public API isn't just "minimal" — it should form a coherent contract. Group related operations, hide internal state, expose capabilities not mechanisms.
- **Dependency Direction**: Dependencies flow one direction. Child modules consumed only by parent. Lower layers never import from higher layers. Shared types live at the shared level, not buried in sibling modules.
- **When to Split**: If you can't describe what a unit does in one sentence, if testing it requires mocking half the system, or if it's too large to hold in context — the boundaries are wrong. Split by concern.

## Architecture

- **File Size**: Files under 500 lines. One responsibility per file.
- **Split Large Types**: Types mixing config, runtime state, and tracking into one blob should be split by concern.
- **Minimal Public API**: Export the minimum needed. Every public function/type is a maintenance burden.
- **Reduce Coupling**: Minimize dependencies between modules. Simplify complex functions.

## Code Clarity

- **Clarity Over Brevity**: Prefer explicit, readable code over compact one-liners. If a "simplification" makes the code harder to read, it's not simpler.
- **Flat Control Flow**: Use early returns and guard clauses to reduce nesting. Prefer `match` over deeply nested `if let` chains. Deeply nested blocks signal a function doing too much.
- **Meaningful Function Extraction**: Functions must encapsulate real logic, not just forward to another function. Names should make architecture self-documenting at every level — reading call sites should explain the flow without comments.
- **One Concern Per Function**: Don't stuff multiple responsibilities into a single function to "keep it simple." Each function should do one thing well. If you need a comment to separate sections within a function, extract them.
- **Consolidate Constants**: No magic strings or hardcoded values scattered across files. Centralize into constants.

## Duplication & Abstraction

- **Eliminate Duplication**: Repeated patterns should be extracted into helpers. One place to change, one place to break.
- **No Premature Abstraction**: Don't extract a helper until the same pattern appears 3+ times. Inline duplication is better than a wrong abstraction.
- **No Dead Code**: No commented-out code, unused imports, or unreachable branches. Delete it.

## Error Handling & Debugging

- **Consistent Error Handling**: Pick one strategy per layer. Don't mix error handling styles arbitrarily. Add context to errors — a bare I/O error without "what failed" is unhelpful. Every error must be logged before propagating or handling.
- **Fail Fast**: Validate at system boundaries (user input, external APIs). Don't add defensive checks deep in internal code.
- **No Silent Retry**: Do not add "if X fails, silently try Y" or "after process exits, start a shell" behavior. Silent retries hide bugs, make debugging harder, and are difficult to test. If a retry is truly necessary, get the user's explicit approval first, and document the justification in a code comment.
- **Debuggability**: Write code that's easy to debug and extend. Avoid opaque transformations — intermediate variables with descriptive names beat long chains. Keep valuable log statements for future debugging.

## Testing

- **Testability**: Code must be testable. If untestable, fix architecture first.
- **Unit Test Coverage**: Target 100% coverage. If code is hard to test, the architecture needs fixing — not the test strategy.
