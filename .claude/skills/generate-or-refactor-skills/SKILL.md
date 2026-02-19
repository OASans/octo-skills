---
---

Create a new skill or refactor existing skills in `.claude/skills/`.

Context:
- Existing skills: `!ls .claude/skills/`

## Skill Design Principles

- **First principles.** Identify the user's ultimate goal. Design the simplest flow that achieves that outcome — don't mechanically implement what was described. Push back if the approach adds unnecessary complexity.
- **Minimize steps.** Every step must carry real value. Cut bookkeeping (updating trackers, marking items done, logging completion). If a step doesn't meaningfully advance the task, delete it. Trackers/checklists: delete done items, only open work remains.
- **Compact.** Short sentences, flat structure. Steps as numbered list, one action each, no sub-steps. No verbose explanations or edge-case branches — trust the agent to infer.
- **File format.** Frontmatter (never add `allowed-tools`). One-line description. Context section (if needed) with `!command` for context injection, `$ARGUMENTS` for user input. Then Steps section.
- Keep focused: one task type per skill.

## Steps

1. Ask user to describe the skill or refactoring they want. Wait for response.
2. Read existing skill(s) if refactoring. Apply first-principles thinking — what does the user actually need? Design the simplest flow.
3. Write or update the SKILL.md file(s) following the design principles above. Update `scripts/skills-manifest.txt` for new or renamed skills.
4. Show the user the result and ask if changes are needed.
