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

**Don't redo work already done this session.** Before running the review gate or memory, check whether it already ran earlier in this conversation — a prior run counts only if it reflects the **current** state being pushed:
- **Review** — if `/review` (or an equivalent full code review) already ran this session **and no material code changes landed after it**, the review gate is satisfied: report `DONE (reviewed earlier this session)` and do not re-run. If code changed after that review, the prior review is stale — re-review at least the delta.
- **Memory** — if the project memory skill already ran this session and nothing new worth remembering surfaced since, report `SKIPPED (memory already run this session)` and continue; don't re-run it just to satisfy step 3.

### Phase 0: Triage — docs/skill-only, simple, or full?

Inspect the diff (`git diff @{upstream}..HEAD` plus uncommitted) **and the changed paths**. Use your own judgement; when in doubt, escalate to the stricter tier.

**docs/skill-only** (fastest path) — *every* changed path is prose documentation (README, CHANGELOG, `docs/`, code comments) and/or skill-definition files (`skills/**/SKILL.md`, `.claude/skills/**`), with **no** source, config, dependency, or schema changes mixed in:
- Skip the review gate → report `SKIPPED (docs/skill-only)`.
- Skip memory → report `SKIPPED (docs/skill-only)`. Do not run it even if the conversation surfaced learnings — but **name what went uncaptured** in the final report so the user can run `/yz-memory` deliberately.
- Just commit, sync (`git pull --rebase`), and push. Skip build and version bump.

**simple** — not docs/skill-only, but ALL hold:
- Only docs/config/comments/typos, or a localized change under ~20 lines
- No code logic, public API, dependency, or schema changes
- No new files of substance (skill READMEs, tracker tweaks, etc. are fine)

Skip the review gate in Phase 1 (report `SKIPPED (simple change)`). Still run pull, build, version bump, and push. Memory: judge per-conversation (below).

**full** — anything else. When in doubt, choose full. Run the entire workflow.

Memory (simple/full only) is **not** governed by change size. Decide per-conversation: if the discussion with the user surfaced anything worth remembering (decisions, gotchas, new patterns, preferences) — run memory, even on a simple change. If the conversation was purely mechanical with nothing learned — skip memory, even on a full change. Report `SKIPPED (nothing to remember)` or run the skill. (docs/skill-only always skips memory — see above.)

### Phase 1: Pre-flight checklist

Re-read the Workflow section in CLAUDE.md (if it exists). Walk through every step (verify, regression tests, etc.) and self-assess: was each one completed? For each gate, report DONE or SKIPPED (with reason — `simple change` or `docs/skill-only` is a valid skip reason for the review gate only). A review already completed earlier this session counts as `DONE` (see *Don't redo work already done this session* above) — do not re-run it.

If any required gate is incomplete — **stop here**. Report what's missing and go back to finish it. Do NOT proceed to Phase 2.

### Phase 2: Push

Only after all gates pass. For the **docs/skill-only** fast path, do only steps 1, 2, and 7 (commit → `git pull --rebase` → push); skip 3–6 and 8.

1. Check `git status`. If there are uncommitted changes, commit them first (stage specific files, conventional commit message, new commit).
2. Run `git pull --rebase` to sync with remote. Do this **before** memory so that any long-term memory consolidation already done upstream is picked up — avoids redoing the work and avoids rebase conflicts on memory files.
3. Memory: **docs/skill-only fast path → skip memory regardless (Phase 0); name any uncaptured learnings in the final report.** **Already run this session and nothing new worth remembering since → `SKIPPED (memory already run this session)`.** Otherwise judge whether this conversation produced anything worth remembering (see Phase 0). If yes, run the project's memory skill (`/yz-memory` or `/memory`) now — **memory must run before push** so any memory changes are included in this push. If memory files changed, commit them (new commit). If no, report `SKIPPED (nothing to remember)` and continue.
4. If CLAUDE.md defines a build command (ai-tool:build or similar), run it to verify the build passes.
5. If the project uses a version field (package.json version, Cargo.toml version, etc.), bump the patch version. Use the Edit tool.
6. If version was bumped, rebuild to verify, then stage the version files and amend into last commit with `git commit --amend --no-edit`.
7. Run `git push`.
8. If CLAUDE.md defines a clean command (ai-tool:clean or similar), run it to free disk space.
