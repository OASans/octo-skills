---
---

Analyze documentation gaps, produce batch-compatible doc tracker. Read-only on source, write-only on tracker.

Downstream: tracker is consumed by `/batch` skill for automated execution. Optimize items for batch: self-contained, exact file paths, specific doc task a zero-context subagent can complete.

## Rules

- Do NOT modify source code or documentation files. Only write `ai-doc/doc/tracker.md`.
- Every item needs: target doc file path (new or existing), related source file paths, specific description of what to document.
- Item format: `- [ ] \`target-path\` — description (source: \`path1\`, \`path2\`)`
- Right-size items for batch subagents: one focused doc change per item. Too small (fix a typo) wastes overhead; too large (document entire subsystem) overwhelms context. Each item should produce ~100-300 lines of doc.
- Tracker is regenerated fresh each run.

## Writing Guidance

Include these rules in the tracker's Tips section so batch subagents follow them:

- Dual audience: AI agents + humans. Exact paths for AI, conceptual clarity for humans.
- Accuracy over completeness. Every claim verifiable against source. Short+correct > long+stale.
- Compact style. Tables over prose. ASCII diagrams. No filler.
- Source paths always repo-relative in backticks.
- Target 100-300 lines per doc file. Split at 400.
- Cross-reference other docs, don't duplicate content.
- Current state only. No historical planning content.
- After writing, verify every path/struct/claim against source.

## Steps

1. Read CLAUDE.md. Find a doc requirements section — a high-level list of what documentation the project needs (e.g., onboarding guide, quick start, debugging guide, architecture overview, API reference, configuration guide, knowledge sharing, performance testing, etc.). If CLAUDE.md does not define doc requirements or a doc plan, tell user: "No documentation requirements found in CLAUDE.md. This skill needs a high-level list of what docs the project needs (e.g., onboarding, quick start, debugging, architecture). Add a doc requirements section to CLAUDE.md and re-run." Stop immediately.
2. Also extract from CLAUDE.md: doc directory, doc conventions, style guidance, table of contents or index (if any).
3. Scan existing documentation against the requirements: which required docs exist, which are missing, which are stale or incomplete.
4. For each gap, scan relevant source code using `Task` subagents in parallel to identify what content needs to be written.
5. Create `ai-doc/doc/` directory if it doesn't exist.
6. Write `ai-doc/doc/tracker.md`. Structure:
   - Header with `/batch ai-doc/doc/tracker.md` usage note.
   - **Task** section — tells batch subagents what to do: read the source files listed, write or update the target doc file, follow writing guidance, verify all claims against source. Must state: "Only add/modify documentation files. Do NOT change source code."
   - **Tips for Subagents** section — populated from CLAUDE.md and codebase analysis. Include: doc directory structure, existing doc conventions, style rules from Writing Guidance above, any project-specific guidance.
   - **Backlog** section — items grouped by `###` category headers matching the doc requirements (e.g., Onboarding, Quick Start, Architecture, Debugging), using the item format from Rules.
7. Report summary: total doc files analyzed, total items, categories.
