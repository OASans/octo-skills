# Shared Agent Scenario Checks

Run `python3 evals/run_scenarios.py --baseline <git-revision>` from this checkout with a logged-in Codex CLI. The baseline revision must contain `evals/suite.json`; each revision supplies its own policy paths so file renames remain comparable. This opt-in check compares baseline and working instructions using the primary and reviewer models/efforts from the current source configs, with at most two requests running concurrently; these currently resolve to Astra/medium and Sol/low.

The seven scenarios cover a prose fix, a bug with regression coverage, coupled simplification, a concrete review defect, commit prerequisites, an ambiguous data-policy choice, and syncing with unrelated user edits. `suite.json` defines the policy fixture and case file; extend it when a new scenario needs another instruction source. Models select actions from each scenario's choices; expected answers stay outside the model prompt.

The runner uses isolated Codex homes, read-only sandboxes, and temporary links to the existing login, removed after each run. Disposable traces and a machine-readable summary stay under the gitignored `.eval-workspace/`; do not publish raw traces or credentials. The runner uses the installer's Python/TOML parser requirements.

Each completed answer is checked for missing/duplicate scenarios, invalid actions, and exact agreement with the expected action set. Errors, timeouts, and malformed answers are reported separately; any failed or incomplete revised run exits nonzero.

These are decision-scenario smoke tests, not end-to-end task execution or automatic skill-trigger measurements. One batch cannot establish general task quality, cost, or latency; inspect real task traces before claiming those improvements.

## Initial comparison

On 2026-09-13, baseline `b3d6b1275920061d679fb6460a7f126fa616d9bf` versus the pre-review revised instructions produced the following initial six-case result:

| Instructions | Model / effort | Cases passed | Seconds | Input tokens | Output tokens |
|---|---|---:|---:|---:|---:|
| Baseline | Astra / medium | 4/6 | 38.30 | 25,457 | 313 |
| Revised | Astra / medium | 6/6 | 31.96 | 23,788 | 138 |
| Baseline | Sol / low | 5/6 | 55.44 | 24,359 | 532 |
| Revised | Sol / low | 6/6 | 27.70 | 22,690 | 138 |

Baseline Astra selected unnecessary coding-guide loading for the typo and per-file test/revert for the coupled change. Baseline Sol omitted the required review for the typo; both revised runs selected the expected actions in all cases. Token counts come from CLI usage events and include the host prompt; timings are single observations, not performance estimates.

The prompt revision follows [OpenAI's Astra skills guidance](https://developers.openai.com/blog/rethinking-skills-and-prompts-for-gpt-6-astra) and [model guidance](https://developers.openai.com/api/docs/guides/latest-model?model=gpt-6-astra). Model effort settings reflect the user's choices, and the shared rules remain applicable to Sol.

After review fixes, the seven-case suite passed 7/7 on revised Astra/medium and 7/7 on revised Sol/low. Baseline Sol passed 6/7; the baseline Astra request returned model-at-capacity and is excluded from that comparison rather than scored as a failure. The initial completed six-case baseline above remains the available Astra comparison.
