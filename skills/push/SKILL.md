---
name: push
description: >
  Push workflow: pull, verify, push. Use when the user asks to push code to remote.
---

Push workflow with pre-flight checklist. Read CLAUDE.md for project-specific build/test commands.

If in plan mode, exit it first — this skill does not need planning.

Context:
- Branch: `!git branch --show-current`
- Unpushed commits: `!git log --oneline @{upstream}..HEAD 2>/dev/null || echo "no upstream"`

## Steps

### Phase 0: Triage — simple or full?

Inspect the diff (`git diff @{upstream}..HEAD` plus uncommitted). Classify as **simple** if ALL hold:
- Only docs/config/comments/typos, or a localized change under ~20 lines
- No code logic, public API, dependency, or schema changes
- No new files of substance (skill READMEs, tracker tweaks, etc. are fine)

Otherwise, treat as **full**. When in doubt, choose full.

For **simple** changes: skip the review gate in Phase 1. Report `SKIPPED (simple change)`. Still run pull, build, version bump, and push.

For **full** changes: run the entire workflow below.

Memory is **not** governed by simple/full. Decide per-conversation: if the discussion with the user surfaced anything worth remembering (decisions, gotchas, new patterns, preferences) — run memory, even on a simple change. If the conversation was purely mechanical with nothing learned — skip memory, even on a full change. Report `SKIPPED (nothing to remember)` or run the skill.

### Phase 1: Pre-flight checklist

Re-read the Workflow section in CLAUDE.md (if it exists). Walk through every step (verify, regression tests, etc.) and self-assess: was each one completed? For each gate, report DONE or SKIPPED (with reason — `simple change` is a valid reason for the review gate only).

If any required gate is incomplete — **stop here**. Report what's missing and go back to finish it. Do NOT proceed to Phase 2.

### Phase 2: Push

Only after all gates pass:

1. Check `git status`. If there are uncommitted changes, commit them first (stage specific files, conventional commit message, new commit).
2. Run `git pull --rebase` to sync with remote. Do this **before** memory so that any long-term memory consolidation already done upstream is picked up — avoids redoing the work and avoids rebase conflicts on memory files.
3. Memory: judge whether this conversation produced anything worth remembering (see Phase 0). If yes, run the project's memory skill (`/yz-memory` or `/memory`) now — **memory must run before push** so any memory changes are included in this push. If memory files changed, commit them (new commit). If no, report `SKIPPED (nothing to remember)` and continue.
4. If CLAUDE.md defines a build command (ai-tool:build or similar), run it to verify the build passes.
5. If the project uses a version field (package.json version, Cargo.toml version, etc.), bump the patch version. Use the Edit tool.
6. If version was bumped, rebuild to verify, then stage the version files and amend into last commit with `git commit --amend --no-edit`.
7. Run `git push`.
8. If CLAUDE.md defines a clean command (ai-tool:clean or similar), run it to free disk space.
