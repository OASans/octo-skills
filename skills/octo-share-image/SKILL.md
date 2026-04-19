---
name: octo-share-image
description: >
  Share an image to the OctoCode Slack channel for this agent. Copies the image
  to the media directory and writes a manifest entry so the bridge uploads it.
  Use when the user asks to share, send, or show an image via Slack.
---

Share an image file to the agent's Slack channel via OctoCode's media bridge.

## Usage

`/octo-share-image <path> [caption]`

- `<path>` — absolute or relative path to the image file
- `[caption]` — optional text caption shown alongside the image in Slack

## Steps

1. **Validate environment**: check that `$OCTO_MEDIA_DIR` and `$OCTO_AGENT_ID` env vars are set. If not, tell the user this skill requires OctoCode's Slack bridge to be active.

2. **Validate the image file**: confirm the file at `<path>` exists and is under 10 MB. Supported formats: PNG, JPEG, GIF, WebP, SVG, PDF.

3. **Copy the image**: run:
   ```bash
   mkdir -p "$OCTO_MEDIA_DIR"
   EPOCH_MS=$(date +%s%3N)
   DEST="$OCTO_MEDIA_DIR/${EPOCH_MS}-${OCTO_AGENT_ID}-$(basename '<path>')"
   cp '<path>' "$DEST.tmp" && mv "$DEST.tmp" "$DEST"
   ```
   The `.tmp` + rename ensures atomic writes (bridge ignores `.tmp` files).

4. **Write manifest**: recreate the manifest file with just this entry:
   ```bash
   MANIFEST="$OCTO_MEDIA_DIR/manifest.jsonl"
   printf '{"aid":"%s","ts":%s,"file":"%s","caption":"%s"}\n' \
     "$OCTO_AGENT_ID" "$EPOCH_MS" "$(basename "$DEST")" '<caption>' \
     > "$MANIFEST.tmp" && mv "$MANIFEST.tmp" "$MANIFEST"
   ```
   If no caption was provided, omit the `"caption"` field from the JSON.

5. **Confirm**: tell the user the image has been queued for Slack upload. The bridge will pick it up within a few seconds.
