---
name: design
description: >
  Design a major feature/component before coding begins. Produces a complete
  spec in `design/<name>/`. Use when the user wants to plan a feature, design
  an architecture, or spec out a component before implementation.
model: opus
---

Design a major feature/component before coding begins. Produces a complete spec in `design/<name>/` that coding agents can implement from directly.

Usage: `/design <feature-name>`

No hardcoded project knowledge. Read CLAUDE.md at runtime to discover structure, conventions, docs.

Output directory: `design/<name>/` (kebab-case from `$ARGUMENTS`). Files:
- `overview.md` — problem statement, goals, non-goals, constraints, open questions
- `user-experience.md` — user journey, ASCII UI mocks, interaction patterns
- `architecture.md` — component diagram, module layout, interface definitions
- `technical-details.md` — data structures, protocols, state management
- `error-handling.md` — failure modes, recovery strategies (skip if trivial)
- `testing-strategy.md` — unit/integration/E2E plan, mock boundaries
- `tracker.md` — ordered PRs with dependency graph, checkbox tracker, and key implementation notes

Design principles:
- High-level design, not implementation details. Describe *what* and *why*, not *how* at the code level.
- No code snippets, struct definitions, function signatures, or file-change lists — unless it's a critical design decision the user must review.
- ASCII diagrams over prose for anything spatial (UI, architecture, data flow).
- Reference existing code by file path only when needed for context.
- Each design file under 500 lines.
- No code implementation — design only. Output is a spec.
- Multiple question rounds mandatory — never skip, never assume.

Steps:

1. Parse `$ARGUMENTS` for feature name. Derive kebab-case directory name.
2. Read CLAUDE.md. Understand project structure, conventions, relevant docs.
3. Explore existing codebase for related code. Spawn parallel Explore subagents (model: sonnet) to search different areas. Collect their findings — the main agent (opus) synthesizes them into the design.
4. Ask the user 5-8 targeted questions: goal, target users, scope boundaries (in/out), success criteria, constraints, prior art/inspiration.
5. Ask follow-up questions based on answers. Minimum 2 question rounds before proceeding.
6. Ask about the complete user workflow: trigger, steps, completion, edge cases.
7. Produce ASCII UI mocks for each state if visual. Document interaction patterns.
8. Ask about integration with existing modules. Propose ASCII component diagram.
9. Describe key interfaces and type boundaries in prose.
10. Deep dive: concurrency model, key data structures, protocol/communication, state management, configuration.
11. Enumerate failure modes. For each: detection method, recovery strategy. Skip if trivial.
12. Define testing strategy.
13. Generate `tracker.md` with implementation plan and progress tracking:
    ```
    # <Feature Name> — Implementation Tracker

    ## PR Dependency Graph
    <ASCII graph showing PR order>

    ## PRs
    - [ ] **PR N: <title>**
      <What it delivers, what it unblocks. Key new modules/files. Verification method.>
    ```
14. Write all files to `design/<name>/`. Cross-check consistency.
15. Present summary. Ask if anything is missing.

Rules:
- Never skip a question round. Maximum clarity before writing.
- If a phase doesn't apply (e.g., no UI), skip it and note why.
- Tracker PRs must be dependency-ordered.
- Open questions go in `overview.md`. Should be empty if questioning was thorough.
- Adapt to project language and conventions discovered from CLAUDE.md.
