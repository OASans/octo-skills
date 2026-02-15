---
---

Create or edit a skill file in `.claude/commands/`.

Context:
- Existing skills: `!ls .claude/commands/`

Steps:

1. Ask user to describe the skill: purpose, trigger, what tools it needs, what it should do. Wait for response.
2. Derive a short kebab-case name from the description. Check if `.claude/commands/<name>.md` exists. If editing, read it.
3. Write the skill file following these rules:
   - Compact. Short sentences, flat structure, minimal nesting.
   - Steps as numbered list. Each step = one action. No sub-steps.
   - No verbose explanations or edge-case branches. Trust the agent to infer.
   - Trackers/checklists: delete done items, don't accumulate history. Only open work remains.
   - Use `!command` for context injection, `$ARGUMENTS` for user input.
   - Frontmatter: never add `allowed-tools` — all skills should have unrestricted tool access.
   - One-line description after frontmatter. Then Context section (if needed). Then Steps section.
   - Keep focused: one task type per skill.
4. Read the written file back. Verify: frontmatter present, steps are flat numbered list, no sub-steps, compact style, tools constrained.
5. Show the user the final file and ask if changes are needed.
