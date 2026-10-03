# Commit Message

1. Use `type(scope): imperative summary`, normally within 70 characters; omit the scope when the change is broad. Choose `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `perf`, `style`, `ci`, or `build`.
2. State what changed in language a future reader understands without the task conversation. Use lowercase and no final period; avoid task numbers or unexplained project codenames.
3. Add one to three sentences of rationale only when the summary and diff do not explain why the change was needed. Add up to five bullets for distinct concepts or consequential tradeoffs, without listing edited files or restating the diff.
4. Use a subject-only message for a small, self-explanatory change. Split unrelated changes into separate commits rather than padding one description.

Example:

```text
fix(auth): refresh expired tokens during long sessions

Sessions previously failed with a hard 401 after token expiry.
Refresh once and retry the request so users can continue working.
```
