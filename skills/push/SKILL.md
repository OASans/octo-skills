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

### Phase 1: Pre-flight checklist

Re-read the Workflow section in CLAUDE.md (if it exists). Walk through every step (verify, regression tests, etc.) and self-assess: was each one completed? For each gate, report DONE or SKIPPED (with reason).

If any gate is incomplete — **stop here**. Report what's missing and go back to finish it. Do NOT proceed to Phase 2.

### Phase 2: Push

Only after all gates pass:

1. Check `git status`. If there are uncommitted changes, commit them first (stage specific files, conventional commit message, new commit).
2. Run `git pull --rebase` to sync with remote. Do this **before** memory so that any long-term memory consolidation already done upstream is picked up — avoids redoing the work and avoids rebase conflicts on memory files.
3. If the project has a memory skill (`/yz-memory` or `/memory`), run it now — **memory must run before push** so any memory changes are included in this push. If memory files changed, commit them (new commit).
4. If CLAUDE.md defines a build command (ai-tool:build or similar), run it to verify the build passes.
5. If the project uses a version field (package.json version, Cargo.toml version, etc.), bump the patch version. Use the Edit tool.
6. If version was bumped, rebuild to verify, then stage the version files and amend into last commit with `git commit --amend --no-edit`.
7. Run `git push`.
8. If CLAUDE.md defines a clean command (ai-tool:clean or similar), run it to free disk space.
