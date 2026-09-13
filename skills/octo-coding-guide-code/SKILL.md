---
name: octo-coding-guide-code
guide-scope: code
description: >
  Review source and config quality, or guide implementation decisions. Read inline when changing code; no subagents.
---

# Coding Guide

> **Guide family.** This is one guide in a family of scoped guides (`octo-coding-guide-*`),
> each carrying a `guide-scope` in its frontmatter that says which changed files it
> covers. This guide's scope is `code` — source in any language, plus config, manifests,
> and build/CI scripts. Sibling guides cover other change kinds (e.g. `octo-coding-guide-rust`
> for `**/*.rs`, `octo-coding-guide-doc` for `**/*.md`). A change is reviewed against every
> guide whose scope its files touch, so scopes may overlap (a Rust file gets this guide
> *and* the Rust guide). Keep each guide to its own scope — do not duplicate another
> guide's rules here.
>
> **Structure contract.** Each `##` section below is a self-contained *review
> domain*: a single coherent focus, reviewable **only** against the rules within it,
> with no overlap onto another domain. `###` headings are rule groups inside a domain.
> Keep the `*Review focus:*` line accurate — it states the domain's one job in a
> sentence. A consumer (e.g. a review skill) may treat each `##` section as an
> independent unit, so domains must stay self-contained and non-overlapping.

## Design & Structure

*Review focus: is the code well-factored, clear, and free of duplication — can a reader understand each unit from its boundary, and can a behavior change stay with its owner?*

### Module & Boundary Design

Every unit (module, struct, trait) must answer three questions: what does it do, how do you use it, what does it depend on?

- **Understandable from Outside**: A consumer should understand what a unit does from its public API alone, without reading internals. If they can't, the interface is leaking implementation details.
- **Changeable Internals**: Internal changes stay local to their module. If restructuring internals requires consumer edits, the boundary is leaking implementation details and must be corrected.
- **Coherent Interfaces**: A public API isn't just "minimal" — it should form a coherent contract. Group related operations, hide internal state, expose capabilities not mechanisms.
- **Dependency Direction**: Dependencies flow one direction. Child modules consumed only by parent. Lower layers never import from higher layers. Shared types live at the shared level, not buried in sibling modules.
- **When to Split**: If you can't describe what a unit does in one sentence, if testing it requires mocking half the system, or if it's too large to hold in context — the boundaries are wrong. Split by concern.

### Change Locality

- **One Owner for Shared Rules**: Resolve shared behavior in one module. Consumers use its result rather than repeat its inputs or rules.
- **Centralized Shared Construction**: Construct large shared structures through constructors and reusable test fixtures. Callers specify only the fields relevant to them.
- **Contracts Declared Once**: Maintain one authoritative schema and dependency declaration. Generate repetitive clients, registrations, and documentation where practical, and keep correctness checks independent of implementation logic.
- **Change Radius Reveals Boundaries**: When a small behavior change requires widespread mechanical edits, investigate the missing boundary before propagating those edits.

### Architecture

- **File Size**: Keep files focused on one responsibility; investigate files over 500 lines as a design signal. Follow any stricter project-enforced limit.
- **Split Large Types**: Types mixing config, runtime state, and tracking into one blob should be split by concern.
- **Minimal Public API**: Export the minimum needed. Every public function/type is a maintenance burden.
- **Reduce Coupling**: Minimize dependencies between modules. Simplify complex functions.

### Code Clarity

- **Naming**: Follow the language, repository, and public API conventions. Prefer `snake_case` where those leave the choice open; do not rename unrelated code to impose it.
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

- **Consistent Error Handling**: Use one strategy per layer and add enough context to explain what failed. Log at the responsible boundary rather than every propagation point.
- **Fail Fast**: Validate at system boundaries (user input, external APIs). Don't add defensive checks deep in internal code.
- **Explicit Fallbacks**: Do not hide failures behind plausible defaults; make fallback behavior observable and consistent with the authorized contract. Ask only when choosing the fallback requires an unresolved product decision or permission.
- **Bounded Retries**: Retry only failures that can safely be retried, with a limit and a visible final failure. Reuse existing authorization; ask when a retry could repeat an external effect whose outcome is unknown.
- **Debuggability**: Write code that's easy to debug and extend. Avoid opaque transformations — intermediate variables with descriptive names beat long chains. Keep valuable log statements for future debugging.

### Temporary Artifacts

- **Project-Local Temp**: In code and tests, never write temporary artifacts to the global system temp directory; use a project-owned path under the project root and manage its creation and cleanup explicitly.

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

- **Testability**: Keep changed behavior testable through appropriate boundaries. Refactor only as needed to verify the authorized change.
- **Meaningful Coverage**: Test changed behavior, boundaries, and relevant failure cases; avoid tests that merely mirror the implementation. Use coverage to locate gaps, not to force unrelated refactoring.
- **No Real Dependencies in Unit Tests**: Never call tmux, shell, filesystem (outside tempdirs), network, HTTP, DBs, or system services from unit tests. They flake, corrupt dev state, and fail in CI. Mock at the boundary or split pure logic out. A "does-not-panic" test that shells out is negative value — delete it. Integration/E2E tests that need real systems must isolate (dedicated socket/tempdir) and clean up.
- **Shell Verification**: Run shell workflows as isolated integration tests with disposable fixtures and controlled external commands. Keep substantial pure logic in testable code instead of mocking individual shell statements.
- **Regression Test for Bug Fixes**: Every bug fix ships with a regression test that fails before the fix and passes after, pinning the specific defect so it cannot silently return. No regression test, no bug fix.

## Consistency & Coherence

*Review focus: does this change fit the codebase it lives in — its patterns, contracts, and assumptions — while staying focused on the task?*

### Codebase Consistency

- **Match Surrounding Patterns**: new code follows the naming, structure, and idioms of the files and modules it lives in. No lone `camelCase` in a `snake_case` file; no new logging or config style introduced next to an established one.
- **Consistent Error-Handling Style**: use the same error strategy as the surrounding layer. Don't introduce a new error mechanism for a single call site when the rest of the layer does it differently.
- **API & Contract Adherence**: respect existing function/module contracts — signatures, invariants, return conventions, ordering guarantees. A change must not silently break assumptions made by callers, especially in the same files.
- **Change Is Covered**: behavioral changes ship with matching test updates. New code paths get new test cases; modified behavior gets updated assertions. Flag missing or now-stale coverage for **this** change specifically (general coverage goals belong to the Correctness domain).

### Change Scope

- **Focused Feature Changes**: Keep feature work separate from unrelated cleanup, renaming, and restructuring.
