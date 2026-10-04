---
name: tool-chatgpt-analysis
description: >
  Offload a complex, well-defined problem and ZIP context to GPT-6 Pro in
  browser Chat for one deep-analysis response, then save it and close the tab.
  Use for costly reasoning or ChatGPT Pro's second opinion; not ordinary local
  code review or ChatGPT Work.
---

# ChatGPT Pro analysis

1. Prepare one self-contained request: the complex problem, desired result, constraints, and what has already been tried. Offload the deep reasoning to browser Pro to save local Codex tokens; allow 10–20 minutes when needed. Collect the relevant files, ZIP them, and upload the ZIP directly. GPT-6 Pro can read ZIP files. For research reviews include the worker transcripts, strategy code, settings, result artifacts and relevant workflow documents. Keep unrelated files, credentials, `.env`, dependencies and build output out of the collection. Do not build sanitizers, exporters, deduplication systems, extra tests or reusable bundling tools. File collection → ZIP → direct upload is the complete preparation workflow.
2. Read the shared [browser workflow](../tool-chatgpt-images/references/browser.md). The helper lives in the sibling `tool-chatgpt-images` skill, which must be installed alongside this skill.
3. Run `analysis` mode with the prompt and attachments in a fresh chat. Send exactly one request and collect one response; never send follow-ups or start another run to continue the same analysis. The helper selects and verifies **GPT-6 Pro** in **Chat** before sending; if unavailable, stop rather than downgrade or switch to Work.
4. Include a short attachment-specific verification question in the prompt, such as identifying trial IDs and verdicts with their supporting ZIP paths. Check the answer against the uploaded files before presenting it as a file-based analysis.
5. Wait for completion and collect the response and conversation link; repeated `collect` calls only check the same request. Complete the shared workflow's required tab cleanup before finishing; report any unresolved cleanup blocker or changed tab. Evaluate its claims against the local code and tests before implementing any recommendations; the analysis itself does not authorize unrelated changes.

```bash
python3 <skills-root>/tool-chatgpt-images/scripts/browser.py start analysis --prompt <question.txt> --attach <context.zip> --run <project>/.chatgpt-workspace/<unique-run>
python3 <skills-root>/tool-chatgpt-images/scripts/browser.py collect --run <project>/.chatgpt-workspace/<unique-run>
```
