---
name: knowledge-skill-trigger-eval
description: >
  Diagnose skill-trigger evaluations: timeouts, registration conflicts, and trace evidence. Load when measuring skill selection.
user-invocable: false
---

# Skill Trigger Evaluation

- Separate completed negative results from timeouts, CLI errors, and registration failures using exit status and traces. An all-zero result is a reason to investigate, not proof of any one cause.
- Measure startup and first-tool latency before choosing a timeout or concurrency; retry an invalid measurement with enough time to complete. Report incomplete runs separately rather than scoring them as trigger failures.
- Evaluate in an isolated skill catalog so an installed same-name skill cannot compete with a proxy. Do not move live installed skills aside while other agents may use them.
- For Claude Code streaming traces, use `claude -p --output-format stream-json --verbose`. Record which skill was invoked, not merely whether a `Skill` tool appeared.
- Test description-selected skills with positive and negative task cues, including hidden `user-invocable: false` knowledge skills. That flag hides the menu entry; it does not require invocation by name.
- Test explicit-only workflows separately from automatic selection. A single successful trace establishes that case only, not general trigger accuracy or behavior quality.

<!-- Last verified: 2026-09-13 -->
