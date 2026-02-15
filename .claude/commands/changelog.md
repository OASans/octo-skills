---
---

Generate a changelog entry from recent commits.

Usage: `/changelog` (since last tag) or `/changelog <range>` (specific commit range)

Context:
- Last tag: `!git describe --tags --abbrev=0 2>/dev/null || echo "no tags"`
- Recent commits: `!git log --oneline -20`

Steps:

1. Determine range. If `$ARGUMENTS` is empty, use last tag to HEAD. If no tags, use last 20 commits. Otherwise use `$ARGUMENTS` as range.
2. Read full commit messages: `git log --format="%H %s%n%b" <range>`.
3. Categorize by Conventional Commits prefix:
   - **Added** (feat): new features
   - **Fixed** (fix): bug fixes
   - **Changed** (refactor, perf): behavior or structural changes
   - **Docs** (docs): documentation changes
   - **Internal** (chore, ci, build, test, style): non-user-facing
4. Within each category, write one concise line per change. Reference commit hash (short). Combine related commits.
5. Read `CHANGELOG.md` if it exists. Prepend new entry with version and date. If no file exists, create it.
6. Present the entry for review before writing.
