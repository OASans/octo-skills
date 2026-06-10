---
name: knowledge-skill-trigger-eval
description: >
  Skill-creator trigger-eval gotchas: 30s-timeout false-0/3 trap, installed-skill
  vs proxy confound, stream-json needs --verbose. Load when measuring skill triggering.
user-invocable: false
---

# Skill-Creator Trigger-Eval Gotchas

## What
Measuring whether a skill's description triggers (skill-creator `run_eval.py` / `run_loop.py`) has three traps:
- **False 0/3 from the timeout.** Default `--timeout 30` under 10-way `--num-workers` kills every `claude -p` before the skill invocation streams (Opus time-to-first-tool ~111s). All-zeros across *every* query — including obvious positives AND the negatives — is a measurement artifact, not a bad description. An unparallelized run confirms the skill does trigger (first tool was `Skill`).
- **Installed skill steals the trigger.** run_eval registers a uniquely-named proxy command; an installed skill of the same name out-competes it and is counted as not-triggered.
- **stream-json needs --verbose.** `claude -p --output-format stream-json` errors with empty output unless `--verbose` is also passed.

## How to Apply
- For a real number: run with a long `--timeout` (~150s) and low `--num-workers` (3-4). Faster: skip the harness and read one `claude -p` trace — if the first tool is `Skill`, it triggers.
- During the eval, move the installed same-name skill aside (`mv ~/.claude/skills/<name>` away, trap-restore on exit) so it can't out-compete the proxy.
- Gate/commit-type skills are hard to measure this way (Claude can often act directly); a single qualitative trace beats a noisy harness pass.

## Key Files
- skill-creator plugin: `scripts/run_eval.py`, `scripts/run_loop.py`

<!-- Last verified: 2026-06-10, commit: 656045f -->
