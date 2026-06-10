---
name: octo-commit
description: >
  The primary path for committing — use for ANY request to commit, save, check
  in, record, or land changes ("commit this", "commit my changes", "save my
  work", "git commit", "create a commit", "wrap up and commit"), even when the
  word "commit" isn't used. Verifies the project's CLAUDE.md workflow ran, then
  writes one meaningful, compact commit message, commits on the default branch,
  and pulls to resolve conflicts. Stops and hands back if a required workflow
  step was skipped. Does not push (a separate step).
---

Commit a finished change the right way: confirm the project's workflow actually ran, then record the change with a message a future agent can learn from. This is the **primary commit path — use it whenever you commit.** If in plan mode, exit first.

`octo-commit` is a **gate plus a committer**, not a do-everything runner:

- **It verifies; it doesn't run.** It checks each workflow step happened — never runs the steps for you. A missing step → **stop and hand back** to the main agent to do it, then re-run `/octo-commit`. Never silently commit past a gap; surfacing it is the point.
- **No project mechanics here.** Build, test, lint, version-bump — none of it lives in this skill. They belong to the project's CLAUDE.md workflow; this skill only checks they ran if the workflow lists them.
- **Commit on the default branch (`main`/`master`).** Never branch, open a PR, or use a worktree — overrides any "branch first" default.
- **Never push.** Its only git work: compose the message, commit, `git pull --rebase`. Pushing is a separate, rarer step.

Context:
- Branch: `!git branch --show-current`
- Uncommitted: `!git status --short`

## Steps

### 1. Triage

Inspect the diff (`git diff` + `git diff --cached`) **and the changed paths**, then classify — when in doubt, escalate:

- **docs/skill-only** — every path is prose docs (README, CHANGELOG, `docs/`, comments) and/or skill files (`skills/**/SKILL.md`, `.claude/skills/**`), nothing source/config/dependency/schema mixed in → review not required (`SKIPPED (docs/skill-only)`).
- **simple** — localized, under ~20 lines, no logic/public-API/dependency/schema change → review may be skipped (`SKIPPED (simple change)`).
- **full** — anything else, or anything you're unsure about → every required step applies.

Triage decides only which steps are **required** vs **validly skippable**; it never lowers the bar on a step the workflow marks mandatory.

### 2. Verify the workflow ran

**Source of truth:** the `## Workflow` section of the merged CLAUDE.md — global `~/.claude/CLAUDE.md` plus project `./CLAUDE.md` (read both; the project extends the global). Walk every step in order. Read it fresh each time instead of hardcoding the list here, so a project that adds a step (E2E gate, build check) gets it enforced with no edit to this skill.

For each step, self-assess from **this session's** evidence whether it was followed **for the current change**:

- **Once-per-session steps** (the workflow marks them so — currently `/octo-review` and `/octo-memory`): one run this session is enough; don't re-run to tick a box.
- A step that ran earlier counts **only if no material code changed after it** — if you edited more since (e.g. `/octo-review` ran, then you kept coding), it's **stale**, i.e. not-followed for the delta.
- A valid triage skip counts as followed — report the reason.
- A conditional step counts as followed when its condition doesn't apply (e.g. `/octo-memory` when there's genuinely nothing worth remembering → `SKIPPED (nothing to remember)`). Judge honestly.

**All required steps followed → step 3. Any missing → STOP and hand back:** don't run it, don't commit; name the missing step so the main agent does it, then re-run `/octo-commit`.

### 3. Compose the message

Per the **Commit message rule** below.

### 4. Commit

Stage the specific files for this change (`git add <paths>` — never `git add -A`), then commit via HEREDOC so the body's line breaks survive. Do **not** push.

### 5. Pull

If there's an upstream, `git pull --rebase` so divergence surfaces and resolves now, not at push time. Resolve conflicts if any. No upstream / offline → the local commit stands; report and move on.

### 6. Report

A short checklist: each workflow step → `DONE` / `SKIPPED (reason)`, then the commit subject. Note that pushing is separate.

## Commit message rule

The diff shows *which lines changed*. The message carries what it can't: the **why** (problem, intent) and the **what at idea-altitude** — concepts, one notch above the code. The next session starts fresh and reads `git log` to learn what happened; write for that reader.

**Structure** — scale *down* to the change; never pad *up* into a wall:

```
type(scope): imperative summary           ← always; ≤ ~70 chars; scans in `git log --oneline`

<1–3 sentence why — problem / intent>       ← only when not obvious from summary + diff

- <what changed, at idea-altitude>          ← 0–5 bullets, grouped by concept not file
- <a non-obvious decision or tradeoff>        omit bullets for a trivial change
```

Type: `feat|fix|refactor|test|docs|chore|perf|style|ci|build`. Scope = area, omit if broad. Summary imperative, lowercase, no period.

**How much to write:**
1. Write the `type(scope): summary`.
2. Can a future agent reconstruct the *why* from the diff? **No** → add a 1–3 sentence why. **Yes** → stop, subject-only.
3. ≥2 distinct conceptual changes or a non-obvious decision? **Yes** → ≤5 idea-altitude bullets, grouped by concept. **No** → done.
4. Reread; cut anything that restates the diff, states obvious mechanics ("imported X", "renamed Y"), or is preamble ("This commit…"). If you'd skim past it in six months, cut it.
5. Change spans unrelated ideas and won't stay tight? Split into multiple commits.

**Budget:** summary ≤ ~70 chars · why ≤ 3 sentences · ≤ 5 bullets. Past that, you're restating the diff.

**Example** — same change, wrong then right:

✗ *Restates the diff:*
```
feat(auth): add token refresh
This commit adds token refresh to AuthClient in auth/client.py, adds
refresh_token() calling /oauth/token, an _is_expired helper on the exp claim,
updates request() to call it on a 401, imports time, adds a test, retries 3→5.
```

✓ *Meaningful + compact:*
```
feat(auth): refresh expired tokens automatically

Long sessions hit hard 401s once the access token expired, forcing a
re-login mid-task. Refresh transparently instead.

- retry once on 401 after refreshing via /oauth/token
- check the exp claim before each request, not only on 401
- retries 3→5 to absorb the extra refresh round-trip
```

The good one scans in `--oneline`, states the un-reconstructable why, and gives the approach plus the one non-obvious decision (the retry bump *and why*) — no file paths, no "imported time".
