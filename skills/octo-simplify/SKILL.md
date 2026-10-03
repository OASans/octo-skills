---
name: octo-simplify
description: >
  Simplify code while preserving behavior. Use only when explicitly asked to simplify, clean up, deduplicate, or shrink code; never as an automatic workflow step.
---

Simplify the requested code while preserving behavior and external contracts. Run only when explicitly requested. Use `octo-coding-guide-code` and relevant specialist guides as the shared quality rules.

## Steps

1. **Scope.** Use the requested paths. Without paths, inspect changed and task-related untracked files; if none, use `@{upstream}...HEAD`, or `HEAD~1..HEAD` without an upstream. Skip generated and unrelated files. An empty target is `Nothing to simplify.`
2. **Inspect.** Read the target, relevant guides, definitions, and callers. Look for dead code, duplicated responsibilities, redundant checks, unnecessary wrappers, and confusing control flow. Keep only changes with a concrete maintenance gain.
3. **Apply.** Make authorized, behavior-preserving changes. Update coupled definitions, callers, and tests together. Before removing a check or error path, establish why it is redundant or unreachable. Report behavior changes and unresolved scope decisions separately; reuse authorization already given.
4. **Verify.** Run affected checks and project-required gates. Reuse current passing evidence where applicable; investigate and fix failures caused by the change. Follow AGENTS.md for independent review.
5. **Report.** State what became simpler, checks run, and any remaining scope or decisions. A clean target is `No simplifications found.`

Work inline for small scopes. Delegate only when independent work saves time or improves confidence, following the project's delegation rules. File counts alone do not require agents, manifests, metrics, or extra verification passes.
