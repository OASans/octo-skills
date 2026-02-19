---
---

Analyze documentation gaps, produce batch-compatible tracker. Read-only on source, write-only on tracker.

Usage: `/plan-doc <path-to-doc-guide>`

The doc guide defines what documents the project needs — each with a purpose (onboarding, debugging, knowledge sharing, etc.), high-level goals, description, target audience, and target path. This skill reads the guide, compares against existing docs, and produces a tracker of gaps.

Downstream: consumed by `/batch`. Items must be self-contained with exact file paths for zero-context subagents.

## Rules

- Do NOT modify source or doc files. Only write `ai-doc/doc/tracker.md`.
- Item format: `- [ ] \`target-path\` — description (source: \`path1\`, \`path2\`)`
- Right-size items: one focused doc change per item, ~100-300 lines of output.
- Tracker regenerated fresh each run.

## Writing Guidance (include in Context section)

- Dual audience: AI agents (exact paths) + humans (conceptual clarity).
- Accuracy over completeness. Short+correct > long+stale.
- Compact: tables over prose, ASCII diagrams, no filler.
- Repo-relative paths in backticks. Target 100-300 lines per doc, split at 400.
- Cross-reference other docs, don't duplicate. Current state only.
- Verify every path/struct/claim against source after writing.

## Steps

1. Read `$ARGUMENTS` as doc guide path. If missing, tell user: "Provide a doc guide path — a file defining what docs the project needs (purpose, goals, descriptions, target paths)." Stop.
2. Read the doc guide. Extract each required document's metadata: purpose, goals, description, target path, related source areas.
3. Scan existing docs against the guide: which exist, which are missing/stale/incomplete.
4. For each gap, scan relevant source via parallel `Task` subagents.
5. Write `ai-doc/doc/tracker.md`: header with `/batch ai-doc/doc/tracker.md` usage, **Context** section (what the subagent should do: read source files, write/update target doc, "only add/modify docs, do NOT change source"; include the doc guide's goals/descriptions for each doc so subagents understand the purpose; project conventions and writing guidance from above), **Backlog** section (items grouped by `###` category headers matching doc guide categories).
6. Report summary: files analyzed, total items, categories.
