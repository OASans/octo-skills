---
name: knowledge-claude-code-permissions
description: >
  settings.json permission globs: `/`=repo-root not fs, `//`=fs-root, `~` literal, bare tool=all paths; out-of-tree write needs additionalDirectories.
user-invocable: false
---

# Claude Code Permission Path Matching

## What
`permissions.allow`/`deny` path args are gitignore-style globs (picomatch matcher via the `zM8` resolver; verified in the installed binary, grep-the-binary method). The glob anchoring is the trap:

- **Single leading `/` = PROJECT-ROOT-relative, NOT filesystem root.** `Write(/**)` auto-approves only inside the current repo.
- **`//` = filesystem root** — the resolver strips one slash → a clean absolute glob. Out-of-tree form: `Write(//home/user/x/**)`.
- **`~` is NOT expanded in allow-rule globs** — picomatch matches it literally, so `Write(~/x/**)` never matches a real absolute path. The trap: `~` *is* expanded in `additionalDirectories` (a different field).
- **Bare tool name (`Read`/`Edit`/`Write`, no parens) = all paths, any operation.**
- **Read allow-rules** cover Read/Grep/Glob + file-reading bash (cat/head/tail/sed), but NOT files opened indirectly by a subprocess (e.g. a python script). OS-level enforcement needs sandboxing.

`additionalDirectories` is **orthogonal**: it brings an out-of-tree dir into write scope; the allow-rule gates the approval prompt. Auto-approving an out-of-repo write needs **both**.

## How to Apply
- In-repo auto-approve: `Edit(/**)` + `Write(/**)`.
- Out-of-tree auto-approve (e.g. `~/.octo-memory`): a `Write(//abs/path/**)` allow-rule **AND** the dir listed in `additionalDirectories`.
- Read everything: bare `Read` (simplest) or `Read(//**)` — never `Read(/**)` (that anchors to the repo).
- Portability: `~` fails and the path must be absolute, so team-shared `global-settings.json` stores it as `/__HOME__/...`; `install.sh` expands `$HOME` at install time. Deploy edits via `./install.sh`.

## Key Files
- `global-settings.json` — `permissions.allow` / `additionalDirectories`
- `install.sh` — `${content//__HOME__/$HOME}` expansion (~line 80)

<!-- Last verified: 2026-07-13, commit: f699a61 -->
