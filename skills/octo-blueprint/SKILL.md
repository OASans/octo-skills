---
name: octo-blueprint
description: >
  Grade a package against the team blueprint and propose prioritized improvements. Run only when explicitly invoked, optionally with a target path.
---

# Octo Blueprint

Grade a package against the blueprint and return prioritized action items. Run only on explicit user invocation; this workflow is read-only.

## Steps

1. **Pick the target.** The current project root by default, or a path the user named with the invocation.
2. **Load the blueprint and list its dimensions.** Read the headings in [the blueprint](references/blueprint.md) and collect its `###` dimensions; each grader reads only its assigned dimension and the structure contract. If it defines no dimensions yet (the skeleton state), there is nothing to grade — report *"The blueprint is not yet defined."* and stop.
3. **Grade dimensions in parallel — one sub-agent per `###` dimension.** Spawn one read-only subagent per dimension, concurrently within the host limit. Explicitly select an available model appropriate to the dimension (Astra or Sol). Give each the base instructions below, target path, blueprint reference path, and assigned `###` heading; the assignment must be self-contained, use no history inheritance, and the agent name must include its selected model.

   **Base instructions (shared by all agents):**

   > You grade one dimension of a package against a blueprint. You are READ-ONLY — you propose work, you never edit the package. Do these in order:
   >
   > 1. Your criteria are **only the rules in your assigned `###` dimension** (read from the supplied blueprint reference) — every rule and every nested criterion. Do not grade against other dimensions; another agent owns each of those.
   > 2. Inspect the target package at the given path. **Verify each rule against the real artifact** — open the script, run its `--help`, `wc -l` the file — never trust a name or a doc line. Search directly for needed context; do not spawn additional agents.
   > 3. Grade each rule **met / partial / unmet / N/A**. Use N/A only when the rule's precondition doesn't hold (e.g. a Rust-only rule in a repo with no Rust), and say why.
   > 4. For every *partial* or *unmet* rule, draft one action item: a suggested priority (P0 blocking · P1 important · P2 polish), a one-line imperative title, the gap (what the rule wants vs. what the package has — name the path), and a concrete **Do** the next agent can act on without re-deriving the rule.
   >
   > Return a structured list headed by your dimension name: every rule's verdict, then the drafted action item for each gap.
4. **Merge and prioritize.** Collect all agents' results into one report: compute the met/total tally across every dimension, order the action items P0 → P1 → P2 (using each agent's suggested priority, normalized across dimensions), and deduplicate where two dimensions flag the same path (keep the higher-priority item).
5. **Report.** Output the prioritized action-item list per the format below. This skill is **read-only**: it proposes the work; it never edits the package. Implementing the items is a separate step (the user, or another agent).

## Output — action items

Lead with a one-line verdict: the met/total tally — N/A rules drop out of the denominator, noted separately — plus the action-item count (e.g. `12/15 rules met (3 N/A) — 6 action items`).

Then a prioritized checkbox list, one item per *partial* or *unmet* rule:

```
- [ ] P0 — <imperative title>   ·   <dimension>
      Gap: <what the rule wants vs. what the package has — name the path>
      Do:  <the concrete change that satisfies the rule>
```

- Order **P0 → P1 → P2** (blocking → important → polish).
- No item without a concrete **Do** — a finding the next agent can't act on isn't an action item.
- Cite paths so the fix is locatable; keep each item to a few lines.
