---
name: octo-coding-guide-code
guide-scope: all
description: >
  Guide implementation, documentation, and review with compact shared quality rules. Read inline; load language-specific guidance only when relevant. No subagents.
---

# Coding Guide

Apply the rules relevant to the changed behavior or prose. For Rust, also read [Rust guidance](../octo-coding-guide-rust/SKILL.md); discover other specialist guides by their `guide-scope` when needed. Scopes select guidance, never agent count.

## Scope and simplicity

- Solve current requirements; do not design for imagined future needs.
- Preserve the authorized behavior and caller contracts. Keep unrelated cleanup, renaming, and hypothetical hardening out of the change.
- Keep responsibilities coherent, dependencies directional, and public interfaces understandable without reading internals. Shared rules and schemas have one authoritative owner.
- Prefer direct, readable code. Add abstractions only when they clarify a responsibility or remove meaningful duplication; size, repetition, or style thresholds alone do not justify them.
- Add or retain compatibility layers only when compatibility is an explicit requirement. Update affected callers together.
- Fix the underlying implementation and remove obsolete paths within the authorized scope; do not hide them behind wrappers, adapters, or fallbacks.
- Judge simplification by clearer behavior and lower maintenance cost, not line counts. Removing supported behavior is a behavior change and needs authorization.

## Correctness

- Check changed contracts and relevant callers, including return values, ordering, errors, and required compatibility. Skill and policy instructions also change behavior, regardless of file extension.
- Investigate concrete failure mechanisms: incorrect logic, realistic boundary inputs, lost errors, races, resource leaks, and untrusted input crossing a boundary. Match error handling to actual consequences and operating conditions; do not invent requirements for hypothetical conditions. Reverting code cannot undo destructive or external effects.
- Validate at system boundaries, preserve useful error context, and report failures where they can be handled. Avoid defensive checks throughout trusted internals.
- Make fallback behavior observable and consistent with the contract. Retry only safely repeatable operations with a bound and visible final failure; resolve unknown external outcomes before repeating effects.
- Keep temporary artifacts in a project-owned path, with explicit creation and cleanup.

## Verification

- Test changed behavior, boundaries, and relevant failure cases; avoid tests that merely mirror the implementation. Use coverage to locate gaps; do not impose blanket coverage targets or force unrelated refactoring.
- Use the cheapest reliable check of the observable contract: unit tests for logic, isolated integration tests for boundaries, and E2E checks for important workflows not established below. Do not duplicate evidence across layers or require a test for every function or path.
- For behavioral bug fixes, add or reuse a regression test that fails before the fix and passes after. A test should pin the wrong outcome, not the implementation used to fix it.
- Keep unit tests independent of live services and developer state. Integration/E2E checks using real systems must isolate their resources and clean up.
- Do not add tests for shell scripts, including regression tests; use syntax checks and direct verification. Still run existing project-required checks.
- Refactor only as needed to verify the authorized behavior. Rerun affected checks after changes; broaden only for changed behavior, failures, or unresolved concerns.

## Documentation

- Use compact, plain language and meaningful structure. State each rule or fact once; avoid preambles, recaps, decorative formatting, and duplicated instructions.
- Make purpose and essential constraints understandable at the entrypoint. Link optional detail instead of loading or repeating it everywhere.
- Give procedures ordered steps and rule collections a flat list. Keep rules short; omit the incident that motivated them unless it is needed to understand the rule.
- Keep claims, commands, examples, links, and terminology accurate and consistent. Keep implementation details with their owner rather than copying them into general policy.
- Check behavioral instructions against their actual effects and contracts; a prose-only correction needs only the relevant documentation checks.
