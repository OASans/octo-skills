---
name: octo-simplify
description: >
  Run a full simplification audit of a project or requested tree through browser GPT-6 Pro and return an evidenced, ranked cleanup plan. Not for focused cleanup, local-agent audits, or implementation.
---

Audit the entire requested scope for meaningful simplification. This skill produces a read-only cleanup plan; applying it is a separate task. Use `octo-coding-guide-code` and relevant specialist guides as the shared quality rules. Run only on an explicit full-audit request or skill invocation.

## Scope and coverage

1. **Inventory.** Default to the whole current project, or the paths the user names; never narrow to a diff. Include first-party code, tests, build/config files, and behavior-defining prompts. Record excluded generated, vendor, binary, and sensitive files with reasons.
2. **Plan.** Split a large target by responsibility into scopes that can be read completely. Keep coupled definitions and callers together; include relevant callers outside the target as context. Save the file inventory, scope assignments, and coverage under a project-local `.simplify-workspace/` run directory. Record each file as pending, partial, inspected, or skipped with a reason; partial files name unread sections.
3. **Read.** Read every included file fully and trace actual call paths and contracts. Search and symbol tools may locate context, but their output alone never establishes coverage. Report unread files and missing callers; split unread work into smaller scopes rather than declaring it inspected.

## Execution

Use only browser GPT-6 Pro through the sibling [ChatGPT Pro analysis workflow](../octo-chatgpt-analysis/SKILL.md). It owns browser connection/model verification, uncertain-submission recovery, attachment verification, report collection, and tab cleanup. Local-agent audits are unsupported; unavailable browser access or GPT-6 Pro is a reported blocker, never a local/API fallback.

1. **Package.** For each planned scope, ZIP its source files, relevant callers/tests, build/config and behavioral instructions, guide rules, and file inventory. Preserve repository-relative paths. Include all files needed to evaluate its contracts; identify missing context. Keep credentials, `.env`, vendor code, generated output, and prior run artifacts out. Collect files and ZIP them directly; do not build a bundling framework.
2. **Request.** Write one self-contained prompt asking for full-file coverage, actual call paths, ranked candidates, deletion evidence, and counterarguments using the criteria below. Require every included file to be read completely, even after findings emerge; sampling, spot checks, and stopping after a few findings are insufficient. Require per-file read status and a brief purpose/contract observation. Completion requires the whole inventory accounted for, with unread sections explicitly marked incomplete; do not impose a findings quota. Include an attachment-specific verification question whose answer is in the ZIP rather than the prompt. Each scope gets one fresh chat and one response; do not send follow-ups or resubmit the same analysis.
3. **Run.** Read the analysis workflow and its shared browser instructions, then use its helper in `analysis` mode with the prompt and ZIP. Choose a fresh project-local `.chatgpt-workspace/` run directory. Wait for completion and collect that same run; a sending timeout is recovered with `collect`, never another `start`.

```bash
python3 <skills-root>/octo-chatgpt-images/scripts/browser.py start analysis --prompt <prompt.txt> --attach <scope.zip> --run <project>/.chatgpt-workspace/<unique-run>
python3 <skills-root>/octo-chatgpt-images/scripts/browser.py collect --run <project>/.chatgpt-workspace/<unique-run>
```

Check the attachment answer and reported file coverage against the inventory. Verifying one fact from the attachment does not prove every file was read. Record omissions as partial or pending; never present an incomplete response as a complete audit. Save the browser response and conversation link and confirm its owned tab was closed. Record the browser-reported inspected/total file count and displayed work time; say unavailable if no duration is exposed. Label it work time, not pure thinking time. These two metrics suffice for process reporting; do not add an intermediate-activity audit.

## Candidate criteria and final audit

- Look for dead code, unnecessary wrappers, redundant abstractions, duplicated responsibilities, obsolete paths, and confusing control flow. Each candidate names the simpler form and its maintenance gain; lower line counts alone are insufficient.
- Identify one-time experiments, comparison harnesses, diagnostic helpers, and new top-level directories committed without an explicitly requested ongoing role, including their dedicated fixtures/tests. Trace their callers and workflow gates; self-created wiring does not establish a maintenance requirement. Recommend removing the whole temporary path while preserving regression tests for supported behavior. Missing approval history alone does not prove an established directory is unnecessary.
- Treat a test as removable only when it proves no meaningful behavior or duplicates another test's evidence. Identify the behavior and coverage that remain; never delete tests to reach a quota.
- Trace consumers before calling code dead, including configuration, dynamic registration, and external contracts. Before proposing removal of a check or error path, establish why it is redundant or unreachable. Distinguish behavior-preserving cleanup from behavior changes needing a decision.
- Verify each returned candidate locally against the necessary source, callers, and tests, including shared owners across scope boundaries. The main agent may delegate bounded groups to fresh local agents for verification only. Check whether the evidence and maintenance gain support the proposed change; do not repeat the full audit or search for new findings locally.

Give every candidate one final verdict: **Change** or **Do not change**, with a brief source-backed reason. Unsupported findings, missing context, and unsettled behavior decisions mean Do not change now, not a tentative recommendation. For a mixed candidate, separate the supported change from the rejected part so each has one verdict.

Save the verified plan alongside the coverage record. Rank Change items by maintenance gain, behavior risk, and effort; give paths/lines, current implementation → proposed change, concrete gain, call-path/test evidence, and relevant verification after implementation. List Do not change items with their reasons. Report the browser-reported inspected/total count, displayed work time, material coverage gaps, and report links. Zero recommended changes is valid; no implementation occurs in this workflow.

When the user separately authorizes implementation, follow the project workflow and report the resulting simplification: lines added/deleted and net change, before/after line totals and percentage reduction `(before - after) / before × 100`, files removed/added/moved and before/after total file counts, plus concrete maintenance gains such as fewer wrappers, duplicated owners, or deployed resources. State the counted scope and starting revision; count moved files once. Report an increase as an increase. Metrics describe the result, never set a reduction quota.
