---
name: octo-check-codex-weekly-usage
description: >
  Check the signed-in Codex account's live weekly allowance remaining and reset
  time when the user asks about weekly usage, quota, or remaining capacity.
---

# Check Codex Weekly Usage

Run the packaged helper:

```bash
python3 <skill-dir>/scripts/check_usage.py
```

Use the actual directory containing this skill. Report the percentage remaining,
percentage used, and reset time with its timezone. If the check fails, report the
error without guessing the allowance.

The helper reads `account/rateLimits/read` from the existing local Codex daemon.
It requires Python 3 and the sibling `tool-codex-capacity-and-quota-listener` transport helper,
both deployed by this repository's installer. It honors `CODEX_HOME`, never starts
or restarts a daemon, and never spends credits or redeems a rate-limit reset.
This check reports usage; it does not prevent later credit spending.
