---
name: octo-commit
description: >
  Commit or save changes after completing the required project workflow. Use for commit requests, including commit-and-push; pushing remains a separate action.
---

Complete the required workflow, then record the authorized change on the default branch with a compact, meaningful commit.

## Steps

1. **Scope.** Inspect the changed paths and staged/unstaged diffs; include untracked files belonging to this task. A compound request still requires the commit gate, and does not authorize a branch or PR against the user's branch policy.
2. **Resolve the workflow.** Use the global and project `AGENTS.md` instructions. The merged workflow owns required checks and permitted skips; this skill adds no size-based or documentation-only exemptions.
3. **Complete prerequisites.** Check this session's evidence for every required step, perform missing authorized work, and resume this gate without ending the task. When delegated, report missing steps to the parent so it can complete them; ask the user only for a real unresolved decision or permission.
4. **Check freshness.** Once-per-session steps remain satisfied after later edits, including review fixes; inspect later deltas directly. Rerun affected build/test/lint checks after relevant changes, and record conditional skips only when their documented condition does not apply.
5. **Compose.** Read [commit message guidance](references/commit_message.md); write a subject that states the resulting change and add only useful rationale. Split unrelated work into separate commits.
6. **Commit.** Stage the specific authorized paths, never `git add -A`, and commit on the default branch; use a message file for multiline text. Do not proceed with failed required checks or include unrelated user edits.
7. **Sync.** With an upstream and a clean tree, run `git pull --rebase` and resolve conflicts without losing user work, then rerun affected checks. If unrelated edits remain, fetch and inspect divergence first; when integration requires moving those edits, preserve them and report the sync blocker without stashing or resetting, just as for an offline or missing upstream.
8. **Report.** State the workflow result and commit subject/hash. Pushing is separate: carry it out when the user authorized it, otherwise stop after the local commit and sync.
