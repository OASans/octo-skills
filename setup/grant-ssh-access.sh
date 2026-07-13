#!/usr/bin/env bash
# Run on the SERVER. Generates a fresh ed25519 keypair, adds the public key to
# ~/.ssh/authorized_keys, and prints a base64 bundle to copy to the laptop.
set -euo pipefail

read -rp "Label for this laptop (used as key filename and SSH config alias, e.g. my-macbook): " LABEL
LABEL=$(printf '%s' "$LABEL" | tr -c 'A-Za-z0-9._-' '-' | sed 's/^-*//;s/-*$//')
if [[ -z "$LABEL" ]]; then
  echo "Label is required." >&2
  exit 1
fi

TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

ssh-keygen -t ed25519 -N '' -C "$LABEL" -f "$TMPDIR/key" -q
PUB=$(cat "$TMPDIR/key.pub")
PRIV=$(cat "$TMPDIR/key")

mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"
touch "$HOME/.ssh/authorized_keys"
chmod 600 "$HOME/.ssh/authorized_keys"

if grep -qF "$PUB" "$HOME/.ssh/authorized_keys"; then
  echo "Public key already present in authorized_keys (unexpected)." >&2
else
  echo "$PUB" >> "$HOME/.ssh/authorized_keys"
fi

# Detect the LAN IP automatically. With WSL2 mirrored networking (set in
# %USERPROFILE%\.wslconfig on the Windows host), the WSL VM shares the
# Windows host's network interfaces — its own IP IS the LAN IP, and no
# `netsh portproxy` is needed. Override by exporting HOST=<ip> before running.
detect_host_ip() {
  local iface ip
  iface=$(ip -4 route show default 2>/dev/null | awk '{print $5; exit}')
  if [[ -n "$iface" ]]; then
    ip=$(ip -4 addr show "$iface" 2>/dev/null | awk '/inet /{print $2; exit}' | cut -d/ -f1)
    [[ -n "$ip" ]] && { printf '%s' "$ip"; return; }
  fi
  hostname -I 2>/dev/null | awk '{print $1}'
}
HOST="${HOST:-$(detect_host_ip)}"
PORT="${PORT:-22}"
USER_NAME=$(whoami)

if [[ -z "$HOST" ]]; then
  echo "Could not detect a LAN IP. Set HOST=<ip> and re-run." >&2
  exit 1
fi
echo "Using HOST=$HOST PORT=$PORT USER=$USER_NAME"

BUNDLE_RAW=$(printf 'HOST=%s\nPORT=%s\nUSER=%s\nALIAS=%s\nKEY_BEGIN\n%s\nKEY_END\n' \
  "$HOST" "$PORT" "$USER_NAME" "$LABEL" "$PRIV")
BUNDLE=$(printf '%s' "$BUNDLE_RAW" | base64 | tr -d '\n')

copy_to_clipboard() {
  if command -v clip.exe >/dev/null 2>&1; then
    printf '%s' "$1" | clip.exe && echo "clip.exe (Windows)" && return 0
  fi
  if command -v wl-copy >/dev/null 2>&1; then
    printf '%s' "$1" | wl-copy && echo "wl-copy" && return 0
  fi
  if command -v xclip >/dev/null 2>&1; then
    printf '%s' "$1" | xclip -selection clipboard && echo "xclip" && return 0
  fi
  if command -v xsel >/dev/null 2>&1; then
    printf '%s' "$1" | xsel --clipboard --input && echo "xsel" && return 0
  fi
  if command -v pbcopy >/dev/null 2>&1; then
    printf '%s' "$1" | pbcopy && echo "pbcopy" && return 0
  fi
  return 1
}

echo
echo "Public key added. Label: $LABEL"
echo "To revoke later, delete the line ending in '$LABEL' from ~/.ssh/authorized_keys"
echo
if CLIP_TOOL=$(copy_to_clipboard "$BUNDLE"); then
  echo "Bundle copied to clipboard via $CLIP_TOOL."
else
  echo "(No clipboard tool found — install clip.exe / xclip / xsel / wl-copy / pbcopy to enable auto-copy.)"
fi
echo
echo "===== BUNDLE (single line) — also printed below in case clipboard fails ====="
echo "$BUNDLE"
echo "===== END ====="
