---
---

Design a major feature/component before coding begins. Produces a complete spec in `design/<name>/` that coding agents can implement from directly.

Usage: `/design <feature-name>`

No hardcoded project knowledge. Read CLAUDE.md at runtime to discover structure, conventions, docs.

Output directory: `design/<name>/` (kebab-case from `$ARGUMENTS`). Files:
- `overview.md` — problem statement, goals, non-goals, constraints, open questions
- `user-experience.md` — user journey, ASCII UI mocks, interaction patterns
- `architecture.md` — component diagram, module layout, interface definitions
- `technical-details.md` — threads, data structures, protocols, state management
- `error-handling.md` — failure modes, recovery strategies (skip if trivial)
- `testing-strategy.md` — unit/integration/E2E plan, mock boundaries
- `implementation-plan.md` — ordered PRs/commits in dependency order
- `tracker.md` — checkbox tracker for `/batch` execution (see format below)

Design principles:
- Interface-driven: code-style type signatures, not prose descriptions. Match project language.
- ASCII diagrams over prose for anything spatial (UI, architecture, state machines).
- Every interface cross-checked against architecture diagram.
- Reference existing code by exact file path.
- Each design file under 500 lines.
- No code implementation — design only. Output is a spec.
- Multiple question rounds mandatory — never skip, never assume.

Steps:

1. Parse `$ARGUMENTS` for feature name. Derive kebab-case directory name.
2. Read CLAUDE.md. Understand project structure, conventions, relevant docs. Read any docs referenced that relate to the feature.
3. Explore existing codebase for related code via Glob/Grep/Task. Understand integration points.
4. Ask the user 5-8 targeted questions: goal, target users, scope boundaries (in/out), success criteria, constraints, prior art/inspiration.
5. Ask follow-up questions based on answers. Minimum 2 question rounds before proceeding. Dig into ambiguities.
6. Ask about the complete user workflow: trigger, steps, completion, edge cases. If the feature has visual components, ask about each state (loading, active, error, empty).
7. Produce ASCII UI mocks for each state if visual. Document interaction patterns (keyboard, mouse, CLI, API — whatever applies). User confirms or revises.
8. Ask about integration with existing modules. Propose ASCII component diagram: processes, threads, data flow, module boundaries. User confirms or revises.
9. Define new interfaces/types as code-style signatures in the project's language. Cross-check against the component diagram.
10. Deep dive: thread/concurrency model (ownership, channels, shutdown), key data structures (fields and types), protocol/communication (message formats, lifecycle, retries), state management (transitions, triggers, locking), configuration (new fields, defaults, validation, backwards compat).
11. Enumerate failure modes. For each: detection method, recovery strategy, user-facing message. Skip this file if error handling is trivial.
12. Define testing strategy: unit test boundaries, integration test scope, E2E scenarios, mock points.
13. Write ordered implementation plan: each item lists files to create/modify, what it produces, and what it unblocks.
14. Generate `tracker.md` from the implementation plan. Format:
    ```
    # <Feature Name> — Implementation Tracker

    Source: `design/<name>/implementation-plan.md`

    - [ ] **Step N: <title>** — <one-line goal>. Files: <key files to create/modify>. Commit: `<conventional commit message>`.
    ```
    One checkbox per implementation step. Each item must be self-contained enough for `/batch` to create a meaningful task from it — include the goal, key files, and a commit message. Reference the full plan for details.
15. Write all files to `design/<name>/`. Cross-check interfaces against architecture, verify all types referenced in data flow exist.
16. Present summary: component count, new files, touched files, estimated complexity. Ask if anything is missing.

Rules:
- Never skip a question round. Maximum clarity before writing.
- If a phase doesn't apply (e.g., no UI), skip it and note why in overview.md.
- Implementation plan must be dependency-ordered — each item lists what it unblocks.
- Open questions go in `overview.md`. Should be empty if questioning was thorough.
- Adapt to project language and conventions discovered from CLAUDE.md.
