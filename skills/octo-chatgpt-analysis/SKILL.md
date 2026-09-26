---
name: octo-chatgpt-analysis
description: >
  Send a scoped project question and selected files to ChatGPT's browser Chat
  mode for GPT-6 Pro analysis, then save the response. Use when the user wants
  ChatGPT Pro's second opinion; not ordinary local code review or ChatGPT Work.
---

# ChatGPT Pro analysis

1. Define the question and select only the relevant source, tests, constraints, and observed failures. Prefer one UTF-8 Markdown bundle with file paths and complete relevant functions; exclude credentials, `.env`, dependencies, build output, and unrelated files. Do not assume ZIP extraction works; use it only after verifying support in the target chat.
2. Read the shared [browser workflow](../octo-chatgpt-images/references/browser.md). The helper lives in the sibling `octo-chatgpt-images` skill, which must be installed alongside this skill.
3. Run `analysis` mode with the prompt and attachments. The helper selects and verifies **GPT-6 Pro** in **Chat** before sending; if unavailable, stop rather than downgrade or switch to Work.
4. Include a short attachment-specific verification question in the prompt, such as reproducing a named contract or marker. Check the answer against the uploaded content before presenting it as a file-based analysis.
5. Collect the completed response and conversation link. Evaluate its claims against the local code and tests before implementing any recommendations; the analysis itself does not authorize unrelated changes.

```bash
python3 <skills-root>/octo-chatgpt-images/scripts/browser.py start analysis --prompt <question.txt> --attach <context.md> --run <project>/.chatgpt-workspace/<unique-run>
python3 <skills-root>/octo-chatgpt-images/scripts/browser.py collect --run <project>/.chatgpt-workspace/<unique-run>
```
