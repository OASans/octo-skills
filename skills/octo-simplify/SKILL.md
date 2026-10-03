---
name: octo-simplify
description: >
  Run a full simplification audit of a project or requested tree and return an evidenced, ranked cleanup plan. Use browser GPT-6 Pro by default, or local agents when explicitly requested. Not for focused cleanup or implementation.
---

Audit the entire requested scope for meaningful simplification. This skill produces a read-only cleanup plan; applying it is a separate task. Use `octo-coding-guide-code` and relevant specialist guides as the shared quality rules. Run only on an explicit full-audit request or skill invocation.

## Scope and coverage

1. **Inventory.** Default to the whole current project, or the paths the user names; never narrow to a diff. Include first-party code, tests, build/config files, and behavior-defining prompts. Record excluded generated, vendor, binary, and sensitive files with reasons.
2. **Plan.** Split a large target by responsibility into scopes that can be read completely. Keep coupled definitions and callers together; include relevant callers outside the target as context. Save the file inventory, scope assignments, and coverage under a project-local `.simplify-workspace/` run directory. Record each file as pending, partial, inspected, or skipped with a reason; partial files name unread sections.
3. **Read.** Read every included file fully and trace actual call paths and contracts. Search and symbol tools may locate context, but their output alone never establishes coverage. Report unread files and missing callers; split unread work into smaller scopes rather than declaring it inspected.

## Execution

Choose browser mode unless the user explicitly requests local agents. Keep that choice throughout the audit; unavailable browser access or GPT-6 Pro is a reported blocker, never a silent local/API fallback.

### Browser GPT-6 Pro — default

Use the sibling [ChatGPT Pro analysis workflow](../octo-chatgpt-analysis/SKILL.md). For each planned scope, prepare one self-contained request and ZIP with its files, relevant callers/tests, guide rules, and inventory. Ask for full-file coverage, call-path evidence, candidates, and counterarguments using the criteria below. Each scope gets one fresh chat and one response; do not send follow-ups or resubmit the same analysis. Follow that workflow's submission recovery, attachment verification, saved reports, and tab cleanup.

Check the reported file coverage against the inventory. Verifying a fact from the attachment does not prove every file was read. Record omissions as partial or pending; never present an incomplete response as a complete audit.

### Local agents — explicit choice

For each scope, use a fresh read-only finder, then a separate fresh read-only adversarial reviewer for its candidates. Default to `gpt-6.1-sol` at `medium` effort for finders and `high` for reviewers; honor explicit model/effort choices. Give self-contained assignments without history inheritance, following AGENTS.md naming and delegation rules. Parallelize independent scopes within host limits; keep interacting contracts together. A scope with no candidates needs no candidate reviewer.

The finder reads the complete scope and returns candidates plus file coverage. The reviewer receives the candidates, guide rules, and relevant source/callers; it tries to disprove each maintenance gain and expose behavior changes, hidden consumers, or lost test coverage. Both report unread context. Return confirmed, uncertain, or rejected with evidence; uncertainty stays visible.

## Candidate criteria and final audit

- Look for dead code, unnecessary wrappers, redundant abstractions, duplicated responsibilities, obsolete paths, and confusing control flow. Each candidate names the simpler form and its maintenance gain; lower line counts alone are insufficient.
- Treat a test as removable only when it proves no meaningful behavior or duplicates another test's evidence. Identify the behavior and coverage that remain; never delete tests to reach a quota.
- Trace consumers before calling code dead, including configuration, dynamic registration, and external contracts. Before proposing removal of a check or error path, establish why it is redundant or unreachable. Distinguish behavior-preserving cleanup from behavior changes needing a decision.
- The main agent checks every final candidate against actual source and callers, challenges deletion evidence, and examines shared owners and duplication across scope boundaries. Scope reviews alone do not establish cross-scope correctness.

Save a ranked cleanup plan alongside the coverage record. For each item give paths/lines, current implementation → proposed change, concrete gain, call-path/test evidence, confidence, and relevant verification after implementation. Rank by maintenance gain, behavior risk, and effort; keep unresolved candidates separate. Report inspected/total files, exclusions, partial/pending files, and browser report links when used. Zero findings is valid; no implementation occurs in this workflow.
