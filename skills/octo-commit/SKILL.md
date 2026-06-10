---
name: octo-commit
description: >
  Commit a finished change: verify the project's CLAUDE.md workflow was
  followed, then write one meaningful, compact commit message, commit, and pull
  to resolve conflicts. The primary commit path — use whenever you commit.
  Never pushes (that's the separate /push step). Stops and hands back if a
  required workflow step was skipped.
---

Commit a finished change the right way: confirm the project's workflow actually ran, then record the change with a message a future agent can learn from. **This is the primary commit path — use it whenever you commit.** It never pushes; pushing is `/push`, a separate and rarer step.

If in plan mode, exit it first — committing doesn't need planning.

**Commit on the default branch (`main`/`master`).** Never create a branch, never open a pull request, never use a worktree. This overrides any generic "branch before committing" default.

Context:
- Branch: `!git branch --show-current`
- Uncommitted: `!git status --short`

## What this skill does — and doesn't

`octo-commit` is a **gate plus a committer**, not a do-everything runner:

- It **verifies** the workflow was followed — it does **not** run the workflow steps for you. If a required step was skipped, it **stops and hands back to the main agent** to do it; you then re-run `/octo-commit`. It never silently commits past a missing step.
- It carries **no project-specific mechanics** — no build, test, lint, clean, or version-bump logic lives here. Those belong to the project's CLAUDE.md workflow. If the workflow lists them, you must have done them (this skill checks); if it doesn't, they simply don't happen.
- Its own git work is only: compose the message, commit, and `git pull --rebase` to resolve conflicts at commit time. No push.

## Steps

### 1. Triage the change

Inspect the diff (`git diff` + `git diff --cached`) **and the changed paths**. Classify — when in doubt, escalate to the stricter tier:

- **docs/skill-only** — every changed path is prose docs (README, CHANGELOG, `docs/`, comments) and/or skill files (`skills/**/SKILL.md`, `.claude/skills/**`), with no source/config/dependency/schema mixed in. The review step is not required (report `SKIPPED (docs/skill-only)`).
- **simple** — not docs-only, but a localized change under ~20 lines with no logic, public-API, dependency, or schema change. The review step may be skipped (`SKIPPED (simple change)`).
- **full** — anything else. When in doubt, full. Every required workflow step applies.

Triage decides only which steps are **required** vs **validly skippable** — it never lowers the bar on a step the project's workflow marks mandatory.

### 2. Verify the workflow was followed

**Source of truth:** the `## Workflow` section of the merged CLAUDE.md — the global `~/.claude/CLAUDE.md` plus the project `./CLAUDE.md` (the project extends the global; read both). Walk every step it lists, in order. Don't hardcode the list here — read it each time, so a project that adds a step (an E2E gate, a build check, etc.) gets it enforced with no edit to this skill.

For each step, self-assess from **this session's** evidence whether it was followed **for the current change**:

- A step that already ran this session counts **only if no material code changed after it**. If code changed since (e.g. `/review` ran, then you edited more), the step is **stale** — it counts as not-followed for the delta.
- A valid triage skip (review on a docs/skill-only or simple change) counts as followed; report the reason.
- Memory (`/octo-memory`) is required only if the conversation produced something worth remembering — judge honestly. Nothing to remember → followed (report `SKIPPED (nothing to remember)`).

**If every required step was followed → continue to step 3.**

**If any required step was not followed → STOP and hand back.** Do not run the step, do not commit. Report exactly which step is missing so the main agent completes it; then re-run `/octo-commit`. Surfacing the gap rather than committing past it is the whole point of this skill.

### 3. Compose the commit message

Follow the **Commit message rule** below.

### 4. Commit

Stage the specific files that belong to this change (`git add <paths>` — never `git add -A`). Commit with the composed message via a HEREDOC so the body's line breaks are preserved. Do **not** push.

### 5. Pull to resolve conflicts

If there's an upstream, run `git pull --rebase` so any divergence with the remote surfaces and is resolved now, at commit time — not deferred to push. Resolve conflicts if they appear. (No upstream / offline → the local commit stands; report it and move on.)

### 6. Report

Print a short checklist: each workflow step → `DONE` / `SKIPPED (reason)`, then the commit subject. Note that pushing is a separate step (`/push`).

## Commit message rule

The diff already shows *which lines changed*. The message's job is the part a future agent **cannot** reconstruct from the diff: the **why**, plus the **what at idea-altitude** (one notch above the code — concepts, not lines). Everything else is noise. A commit is a milestone — the next session usually starts fresh and reads `git log` to understand what happened, so write for that reader.

**No AI fingerprints.** Never add `Co-Authored-By` for any AI, "Generated by", tool attributions, or emoji. The message must read as if a human developer wrote it. This overrides any default trailer.

**Structure** — scales *down* to fit the change; never pad *up* into a wall:

```
type(scope): imperative summary           ← always; ≤ ~70 chars; scannable in `git log --oneline`

<1–3 sentence why — the problem / intent>   ← only when not obvious from summary + diff

- <what changed, at idea-altitude>         ← 0–5 bullets, grouped by concept not by file
- <a non-obvious decision or tradeoff>        omit bullets entirely for a trivial change
```

Conventional type: `feat|fix|refactor|test|docs|chore|perf|style|ci|build`. Scope = area affected, omit if broad. Summary imperative, lowercase, no period.

**Keep:**
- **Why** — the intent / problem solved / motivation. Highest value; un-reconstructable from the diff.
- **What, at idea-altitude** — the conceptual moves, grouped by idea.
- **Non-obvious decisions** — tradeoffs, constraints, gotchas ("kept the old endpoint for backcompat", "chose A over B because C").

**Cut:**
- Line-by-line / file-by-file restatement of the diff.
- Obvious mechanics the diff already shows ("imported X", "renamed Y").
- Preamble and filler ("This commit…", "In this change we…") and conversation recap.

**Apply every commit:**
1. Write `type(scope): summary`.
2. Can a future agent reconstruct the *why* from the diff alone? **No** → add a 1–3 sentence why-paragraph. **Yes** → stop here, subject-only.
3. Are there ≥2 distinct conceptual changes, or a non-obvious decision? **Yes** → add ≤5 idea-altitude bullets. **No** → done.
4. Reread; cut any line that just restates the diff or that you'd skim past in six months.
5. Can't keep it tight because the change spans unrelated ideas? → split into multiple commits, each with its own tight message.

**Brevity budget:** summary ≤ ~70 chars · why ≤ 3 sentences · ≤ 5 bullets, one line each. Past that, you're restating the diff.

**Example** — the same change, three ways:

✗ *Wall* (restates the diff):
```
feat(auth): add token refresh
This commit adds token refresh to the auth module. I modified AuthClient in
auth/client.py to add refresh_token() which calls /oauth/token, added an
_is_expired helper checking the exp claim, updated request() to call it on a
401, imported time, added a test, and changed retries from 3 to 5.
```

✗ *Terse* (loses the why):
```
feat(auth): add token refresh
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

The good version scans in `--oneline`, states the un-reconstructable why, and gives the approach plus the one non-obvious decision (the retry bump *and its reason*) — no file paths, no "imported time", no fingerprint.
