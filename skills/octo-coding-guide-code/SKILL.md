---
name: octo-coding-guide-code
guide-scope: all
description: >
  Guide implementation, documentation, and review with compact shared quality rules. Read inline; load language-specific guidance only when relevant. No subagents.
---

# Coding Guide

Apply the rules relevant to the changed behavior or prose. For Rust, also read [Rust guidance](../octo-coding-guide-rust/SKILL.md); discover other specialist guides by their `guide-scope` when needed. Scopes select guidance, never agent count.

## Scope and design

- Preserve the authorized behavior and caller contracts. Keep unrelated cleanup, renaming, and hypothetical hardening out of the change.
- Keep responsibilities coherent, dependencies directional, and public interfaces understandable without reading internals. Shared rules and schemas have one authoritative owner.
- Extract functions, constants, or shared construction when they clarify a boundary or prevent meaningful divergence; do not extract just to meet a size, repetition, or style threshold.
- Prefer readability over brevity, with clear names, explicit control flow, and surrounding conventions. Remove dead code within the changed scope; avoid premature abstractions.
- Match robustness to actual consequences and operating conditions. Easy local recovery can justify less machinery; reverting code cannot undo destructive or external effects.

## Correctness

- Check changed contracts and relevant callers, including return values, ordering, errors, and compatibility. Skill and policy instructions also change behavior, regardless of file extension.
- Investigate concrete failure mechanisms: incorrect logic, realistic boundary inputs, lost errors, races, resource leaks, and untrusted input crossing a boundary. Do not invent requirements for hypothetical conditions.
- Validate at system boundaries, preserve useful error context, and report failures where they can be handled. Avoid defensive checks throughout trusted internals.
- Make fallback behavior observable and consistent with the contract. Retry only safely repeatable operations with a bound and visible final failure; resolve unknown external outcomes before repeating effects.
- Keep temporary artifacts in a project-owned path, with explicit creation and cleanup.

## Verification

- Test changed behavior, boundaries, and relevant failure cases; avoid tests that merely mirror the implementation. Use coverage to locate gaps, not to force unrelated refactoring.
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
