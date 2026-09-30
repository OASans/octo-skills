---
name: octo-chatgpt-research
description: >
  Run one Deep Research task through the user's signed-in ChatGPT browser,
  with uploaded project artifacts, then save the cited report and conversation
  link. Use for thorough source-based research; not ordinary Pro analysis,
  quick web lookups, or API research.
---

# ChatGPT Deep Research

1. Prepare one self-contained question with the goal, scope, constraints, preferred sources, and expected report. Request direct source links alongside citations. Resolve missing decisions before sending; include known preferences so the browser can proceed without clarification. Run one research task and collect one report; never start another task to continue or retry it.
2. Prepare only relevant artifacts. Prefer a UTF-8 Markdown package with file paths and complete relevant content, or attach supported documents directly. Exclude credentials, `.env`, dependencies, and unrelated files. A ZIP is useful only when the browser can read its contents; include an attachment-specific check such as a hidden marker or a calculation from a named file, and verify it in the report before claiming the package was read.
3. Read the shared [browser workflow](../octo-chatgpt-images/references/browser.md). Its helper must be installed alongside this skill. Use `research` mode; it selects and verifies the Deep Research plugin before sending. Stop on unavailable access or quota instead of switching to ordinary chat or an API.
4. Collect the same run until the research report is complete; allow 5–30 minutes or the user's time budget. The helper waits for the report inside the Deep Research widget, not the chat acknowledgment. `awaiting_plan` means inspect the proposed plan; it may start automatically. `needs_input` means inspect the widget or chat response for a clarification, failed task, or quota. Continue the same task only using the supplied brief; ask the user only for a material missing decision. Never automatically resend after a timeout or uncertain submission.
5. Collection saves `response.md` with rendered report text, direct source links and conversation URL, plus `sources.json`. Check tables when formatting matters. Verify the attachment check and relevant claims, and report unsupported or unreadable files. Confirm that collection closed its own tab; report any cleanup failure. Keep prompts, uploaded packages, and reports local by default. Research does not authorize implementing recommendations or writing to connected services.

```bash
python3 <skills-root>/octo-chatgpt-images/scripts/browser.py start research --prompt <question.txt> --attach <artifacts.md> --run <project>/.chatgpt-workspace/<unique-run>
python3 <skills-root>/octo-chatgpt-images/scripts/browser.py collect --run <project>/.chatgpt-workspace/<unique-run>
```
