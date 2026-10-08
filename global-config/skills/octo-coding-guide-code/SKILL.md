---
name: octo-coding-guide-code
description: >
  Guide implementation, documentation, and review with compact shared quality rules. Read inline; load language-specific guidance only when relevant. No subagents.
---

# Coding Guide

Apply the common rules below to all implementation, documentation, and review. Before changing or reviewing Rust code (`*.rs`), read [Rust instructions](languages/rust.md). Language-specific instructions live in `languages/` within this skill; read the relevant file rather than loading a separate language skill.

## Scope and simplicity

- Solve current requirements; do not design for imagined future needs.
- Preserve the authorized behavior and caller contracts. Keep unrelated cleanup, renaming, and hypothetical hardening out of the change.
- Keep responsibilities coherent, dependencies directional, and public interfaces understandable without reading internals. Shared rules and schemas have one authoritative owner.
- Prefer direct, readable code. Add abstractions only when they clarify a responsibility or remove meaningful duplication; size, repetition, or style thresholds alone do not justify them.
- Add or retain compatibility layers only when compatibility is an explicit requirement. Update affected callers together.
- Fix the underlying implementation and remove obsolete paths within the authorized scope; do not hide them behind wrappers, adapters, or fallbacks.
- Judge simplification by clearer behavior and lower maintenance cost, not line counts. Removing supported behavior is a behavior change and needs authorization.
- Keep one-time comparisons, benchmarks, and diagnostic helpers in ignored project workspaces. Do not commit their harnesses, fixtures, or results, or make them permanent workflow gates, unless the user explicitly requests maintained infrastructure. Run model/prompt performance comparisons only when requested.
- Get explicit user approval before creating a new tracked top-level directory. State its purpose and maintenance role; a request naming that directory already provides approval. Use existing project structure and ignored workspaces for routine changes and temporary work.

## Correctness

- Check changed contracts and relevant callers, including return values, ordering, errors, and required compatibility. Skill and policy instructions also change behavior, regardless of file extension.
- Investigate concrete failure mechanisms: incorrect logic, realistic boundary inputs, lost errors, races, resource leaks, and untrusted input crossing a boundary. Match error handling to actual consequences and operating conditions; do not invent requirements for hypothetical conditions. Reverting code cannot undo destructive or external effects.
- Validate at system boundaries, preserve useful error context, and report failures where they can be handled. Avoid defensive checks throughout trusted internals.
- Make fallback behavior observable and consistent with the contract. Retry only safely repeatable operations with a bound and visible final failure; resolve unknown external outcomes before repeating effects.
- Keep temporary artifacts in a project-owned path, with explicit creation and cleanup.

## Verification

- Keep a test only when it answers: “What realistic wrong outcome would this catch?” Protect required behavior or a concrete regression; use coverage to locate gaps, not impose quotas or test every function.
- Place tests beside the code they exercise, such as `scripts/browser_test.py`; do not create a separate root test directory.
- Assert observable results rather than internal call sequences or copies of prose and configuration defaults. Avoid overlapping tests and large mock setups; delete tests when their supported behavior is removed.
- Use the cheapest reliable check of the observable contract: unit tests for logic, isolated integration tests for boundaries, and E2E checks for important workflows not established below. Do not duplicate evidence across layers or require a test for every function or path.
- For bug fixes, verify that the failure is resolved. Reuse or strengthen existing tests first; add a focused regression test when existing checks would miss the wrong outcome. Simple wiring or configuration fixes may need only direct verification.
- Keep unit tests independent of live services and developer state. Integration/E2E checks using real systems must isolate their resources and clean up.
- Do not maintain tests for shell scripts, including regression tests; use syntax checks and temporary direct verification. Retire existing shell-test harnesses and gates rather than retaining compatibility exceptions.
- Refactor only as needed to verify the authorized behavior. Rerun affected checks after changes; broaden only for changed behavior, failures, or unresolved concerns.

## Documentation

- Use compact, plain language and meaningful structure. State each rule or fact once; avoid preambles, recaps, decorative formatting, and duplicated instructions.
- Make purpose and essential constraints understandable at the entrypoint. Link optional detail instead of loading or repeating it everywhere.
- Give procedures ordered steps and rule collections a flat list. Keep rules short; omit the incident that motivated them unless it is needed to understand the rule.
- Keep claims, commands, examples, links, and terminology accurate and consistent. Keep implementation details with their owner rather than copying them into general policy.
- Check behavioral instructions against their actual effects and contracts; a prose-only correction needs only the relevant documentation checks.
