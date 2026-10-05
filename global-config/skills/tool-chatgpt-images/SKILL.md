---
name: tool-chatgpt-images
description: >
  Generate images through the user's logged-in ChatGPT website with non-Pro
  settings. This is the only route to use for image generation, including prompt
  iteration; never use native Codex image generation or an image API.
---

# ChatGPT browser images

1. Prepare the image prompt locally. Use the shared [browser workflow](references/browser.md); it requires Google's Chrome DevTools MCP/CLI, not `image-use` or `chrome-use`.
2. Run the helper in `images` mode. It selects and verifies **Instant** before submission; never switch to Pro, Work, native Codex image generation, or the API when this route fails.
3. Collect the result, inspect the saved image, complete the shared workflow's required tab cleanup, and return its path and conversation link. For a requested revision, prepare a new prompt and run directory; attach the previous image with `--attach` when its visual content must be preserved.
4. Distinguish the verified browser route and selected setting from quota accounting. Browser evidence cannot prove a zero quota delta, and Codex still spends usage coordinating the task.

```bash
python3 <skill-dir>/scripts/browser.py start images --prompt <prompt.txt> --run <project>/.chatgpt-workspace/<unique-run>
python3 <skill-dir>/scripts/browser.py collect --run <project>/.chatgpt-workspace/<unique-run>
```
