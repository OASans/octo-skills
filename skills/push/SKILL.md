---
name: push
description: >
  Push committed work to the remote: sync, then push. Use when the user asks to
  push. Commit first with /octo-commit — push does not gate or commit.
---

Push committed work to `origin`. Committing and all workflow gates live in `/octo-commit` — this skill only syncs and pushes. Pushing is the separate, rarer step: you usually `/octo-commit` several times, then `/push` once.

If in plan mode, exit it first — pushing doesn't need planning.

**Always push directly to the default branch (`main`/`master`).** Never create a branch, never open a pull request, never use a worktree. This overrides any generic "branch before pushing" default.

Context:
- Branch: `!git branch --show-current`
- Unpushed commits: `!git log --oneline @{upstream}..HEAD 2>/dev/null || echo "no upstream"`

## Steps

1. **The tree must be clean.** Run `git status`. If anything is uncommitted, **stop** — do not commit here. Run `/octo-commit` first (the only commit path; it runs the workflow gate), then come back to `/push`. If the tree is clean but nothing is unpushed, say so and stop.
2. Run `git pull --rebase` to sync with the remote. Resolve any conflicts.
3. Run `git push` — directly to the default branch on `origin`. Never open a pull request.
