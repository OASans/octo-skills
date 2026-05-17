---
name: coding-guide
description: >
  Print the shared coding guide. Inline skill — no sub-agents. Use as a
  reference for code reviews, implementation decisions, and plan evaluation.
---

# Coding Guide

> **Structure contract.** Each `##` section below is a *review domain*. The
> `/review` skill spawns exactly one parallel sub-agent per `##` section, and
> that agent reviews the diff **only** against the rules in its section. Add a
> `##` section here and `/review` automatically gains an agent — no edit to the
> review skill is needed. `###` headings are rule groups within a domain. Keep
> every domain to one coherent focus so its agent stays sharp, and keep the
> `*Review focus:*` line accurate — it is the agent's mission statement.

## Design & Structure

*Review focus: is the code well-factored, clear, and free of duplication — can a new reader understand each unit from its boundary alone?*

### Module & Boundary Design

Every unit (module, struct, trait) must answer three questions: what does it do, how do you use it, what does it depend on?

- **Understandable from Outside**: A consumer should understand what a unit does from its public API alone, without reading internals. If they can't, the interface is leaking implementation details.
- **Changeable Internals**: You should be able to restructure a unit's internals without breaking consumers. If you can't, the boundary is in the wrong place.
- **Coherent Interfaces**: A public API isn't just "minimal" — it should form a coherent contract. Group related operations, hide internal state, expose capabilities not mechanisms.
- **Dependency Direction**: Dependencies flow one direction. Child modules consumed only by parent. Lower layers never import from higher layers. Shared types live at the shared level, not buried in sibling modules.
- **When to Split**: If you can't describe what a unit does in one sentence, if testing it requires mocking half the system, or if it's too large to hold in context — the boundaries are wrong. Split by concern.

### Architecture

- **File Size**: Files under 500 lines. One responsibility per file.
- **Split Large Types**: Types mixing config, runtime state, and tracking into one blob should be split by concern.
- **Minimal Public API**: Export the minimum needed. Every public function/type is a maintenance burden.
- **Reduce Coupling**: Minimize dependencies between modules. Simplify complex functions.

### Code Clarity

- **Snake Case Naming**: Directory names, file names, function names, and variable names all use `snake_case`. No `camelCase`, `PascalCase`, or `kebab-case` for these. (Types/classes follow language convention, e.g. `PascalCase` in Rust/Python.)
- **Clarity Over Brevity**: Prefer explicit, readable code over compact one-liners. If a "simplification" makes the code harder to read, it's not simpler.
- **Flat Control Flow**: Use early returns and guard clauses to reduce nesting. Prefer `match` over deeply nested `if let` chains. Deeply nested blocks signal a function doing too much.
- **Meaningful Function Extraction**: Functions must encapsulate real logic, not just forward to another function. Names should make architecture self-documenting at every level — reading call sites should explain the flow without comments.
- **One Concern Per Function**: Don't stuff multiple responsibilities into a single function to "keep it simple." Each function should do one thing well. If you need a comment to separate sections within a function, extract them.
- **Consolidate Constants**: No magic strings or hardcoded values scattered across files. Centralize into constants.

### Duplication & Abstraction

- **Eliminate Duplication**: Repeated patterns should be extracted into helpers. One place to change, one place to break.
- **No Premature Abstraction**: Don't extract a helper until the same pattern appears 3+ times. Inline duplication is better than a wrong abstraction.
- **No Dead Code**: No commented-out code, unused imports, or unreachable branches. Delete it.

## Correctness & Robustness

*Review focus: will this code behave correctly under real, adverse, and boundary inputs — and is that behavior actually proven by tests?*

### Error Handling & Debugging

- **Consistent Error Handling**: Pick one strategy per layer. Don't mix error handling styles arbitrarily. Add context to errors — a bare I/O error without "what failed" is unhelpful. Every error must be logged before propagating or handling.
- **Fail Fast**: Validate at system boundaries (user input, external APIs). Don't add defensive checks deep in internal code.
- **No Unapproved Fallback**: Don't add fallback logic ("if the real path fails, quietly use a default/alternate value or code path") without explicit user approval. Silent fallbacks mask failures and produce plausible-but-wrong behavior that's hard to detect. If a fallback is genuinely required, get the user's explicit approval first, and document the justification in a code comment.
- **No Silent Retry**: Do not add "if X fails, silently try Y" or "after process exits, start a shell" behavior. Silent retries hide bugs, make debugging harder, and are difficult to test. If a retry is truly necessary, get the user's explicit approval first, and document the justification in a code comment.
- **Debuggability**: Write code that's easy to debug and extend. Avoid opaque transformations — intermediate variables with descriptive names beat long chains. Keep valuable log statements for future debugging.

### Bug Classes

Scan for the concrete defect classes that a compiler, linter, or type checker does **not** catch:

- **Logic Errors**: off-by-one, inverted/!-flipped conditions, wrong operator, incorrect loop or slice bounds.
- **Unhandled Failure**: missing error handling, swallowed exceptions, ignored return values, unchecked `null`/`None`/`Option`/`Result`.
- **Concurrency**: race conditions, shared mutable state without synchronization, deadlock, inconsistent lock/await ordering.
- **Input Extremes**: empty input, single element, very large input, integer overflow/underflow, out-of-range or negative values.
- **Resource & Time**: missing timeouts, leaked handles/connections, unbounded growth, no backpressure.
- **Untrusted Input**: command injection, path traversal, any unchecked user input crossing a trust boundary.

Flag only real defects that would cause incorrect behavior — not hypotheticals a test would already catch.

### Testing

- **Testability**: Code must be testable. If untestable, fix architecture first.
- **Unit Test Coverage**: Target 100% coverage. If code is hard to test, the architecture needs fixing — not the test strategy.
- **No Real Dependencies in Unit Tests**: Never call tmux, shell, filesystem (outside tempdirs), network, HTTP, DBs, or system services from unit tests. They flake, corrupt dev state, and fail in CI. Mock at the boundary or split pure logic out. A "does-not-panic" test that shells out is negative value — delete it. Integration/E2E tests that need real systems must isolate (dedicated socket/tempdir) and clean up.

## Consistency & Coherence

*Review focus: does this change fit the codebase it lives in — its patterns, contracts, and the assumptions other code already makes?*

### Codebase Consistency

- **Match Surrounding Patterns**: new code follows the naming, structure, and idioms of the files and modules it lives in. No lone `camelCase` in a `snake_case` file; no new logging or config style introduced next to an established one.
- **Consistent Error-Handling Style**: use the same error strategy as the surrounding layer. Don't introduce a new error mechanism for a single call site when the rest of the layer does it differently.
- **API & Contract Adherence**: respect existing function/module contracts — signatures, invariants, return conventions, ordering guarantees. A change must not silently break assumptions made by callers, especially in the same files.
- **Change Is Covered**: behavioral changes ship with matching test updates. New code paths get new test cases; modified behavior gets updated assertions. Flag missing or now-stale coverage for **this** change specifically (general coverage goals belong to the Correctness domain).
