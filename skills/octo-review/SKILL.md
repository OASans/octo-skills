---
name: octo-review
description: >
  Review consequential or uncertain changes, or an explicitly requested review, with one holistic read-only reviewer and independent bug verification.
---

Return actionable findings only; never implement fixes or invent findings. AGENTS.md owns when independent review is required. An explicit review request always runs this workflow.

## Steps

1. **Scope.** Inspect `git diff HEAD` and `git status --short`, including task-related untracked files. For a requested post-commit review, use the requested range, otherwise `@{upstream}...HEAD` (without an upstream, `HEAD~1..HEAD`); if empty, report `Nothing to review.` Record the exact range/files, task intent, and any user focus. For a later review, scope the substantial unreviewed delta and necessary context.
2. **Select guidance.** Read `octo-coding-guide-code` and relevant specialist guides from the skill catalog (`guide-scope: all` always applies; glob scopes select matching files). Use source copies when reviewing this package. Judge the effects of instructions/configuration as well as source code; file extensions do not determine consequence.
3. **Review.** Default to one fresh-context reviewer covering the whole change and relevant guidance. Split only genuinely independent work that one reviewer cannot cover coherently; keep interacting contracts together. Headings and line counts do not create agents.
4. **Verify.** Deduplicate concrete failure claims and send them together to at most one independent verifier, as described below. Clean or quality-only reviews need no verifier.
5. **Report.** Present confirmed bugs, plausible bugs with their uncertainty, then material in-scope quality findings. Include file/line evidence and concrete consequences; omit refuted claims and optional cleanup. A clean result is `No issues found.`

## Reviewer dispatch

Use the model, effort, and read-only instructions from the configured `octo-reviewer` agent (source `codex-agents/` in this package). Select the custom role when its advertised settings match; otherwise use a general agent with the configured settings explicitly. Use no history inheritance and include the actual model in the agent name.

Give the reviewer the exact diff command, tracked/untracked file scope, guide paths, task intent, and this prompt:

> Read-only review; do not edit or spawn agents. Read the supplied diff, relevant guidance, and necessary enclosing code or prose. Follow changed contracts through their callers and check that required behavior survives deletions or replacements. Read outside the changed files only for necessary context.
>
> Report introduced or worsened defects and material in-scope quality problems. Name the triggering inputs/state and wrong outcome for a bug, or the concrete maintenance cost for a quality finding. Surface supported failure mechanisms even when the trigger needs verification; drop uncertain quality opinions. Do not report unrelated pre-existing defects, hypothetical hardening, stylistic preferences, intentional behavior changes, or issues already established by completed checks.
>
> Return concise findings, most severe first: `file:line — rule — consequence and evidence`. If none, return `No issues found.`

## Independent verification

Use the configured `octo-review-verifier` settings with the same role-resolution and naming rules. Give it all failure claims, the diff command, and relevant file paths; no history inheritance or further delegation. Verify runtime failures and broken instructions, paths, commands, or examples; pure quality findings do not need verification.

Return one verdict per claim:

- **CONFIRMED** — concrete trigger and wrong outcome, with supporting code or instruction evidence.
- **PLAUSIBLE** — real mechanism but uncertain trigger; state what would confirm it.
- **REFUTED** — evidence proves the claim wrong, impossible, or already guarded.

Drop refuted findings. Keep plausible findings visibly uncertain; the implementing agent investigates them before deciding a fix is warranted.
