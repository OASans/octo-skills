# Project memory

`octo-memory` is a manual transcript audit. Browser GPT-6 Pro proposes durable knowledge; the local agent verifies factual claims before publishing concise project `knowledge-*` skills. Ordinary development tasks keep knowledge retrieval without generating captures.

The default window is seven days, overridable with `--days`. The global ledger and saved reports live under `~/.octo-memory/projects/<project-id>/`, outside installed skill folders. It records session and message IDs so overlapping audits skip processed content while resumed sessions contribute new messages.

`scripts/transcripts.py prepare` produces equivalent Markdown and ZIP artifacts. `finish` records only a completed, attachment-verified browser audit. Legacy captures import once. See [storage details](references/storage.md).
