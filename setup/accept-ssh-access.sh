#!/usr/bin/env bash
# Run on the LAPTOP. Prompts for the bundle produced by grant-ssh-access.sh,
# installs the private key, and adds an entry to ~/.ssh/config.
set -euo pipefail

echo "Paste the bundle from the server (single line), then press Enter:"
read -r BUNDLE
if [[ -z "$BUNDLE" ]]; then
  echo "No input." >&2
  exit 1
fi

DECODED=$(printf '%s' "$BUNDLE" | base64 -d 2>/dev/null) || {
  echo "Failed to base64-decode bundle." >&2
  exit 1
}

HOST=$(printf '%s\n' "$DECODED" | sed -n 's/^HOST=//p')
PORT=$(printf '%s\n' "$DECODED" | sed -n 's/^PORT=//p')
USER_NAME=$(printf '%s\n' "$DECODED" | sed -n 's/^USER=//p')
LABEL=$(printf '%s\n' "$DECODED" | sed -n 's/^ALIAS=//p')
PRIV=$(printf '%s\n' "$DECODED" | sed -n '/^KEY_BEGIN$/,/^KEY_END$/p' | sed '1d;$d')

if [[ -z "$HOST" || -z "$PORT" || -z "$USER_NAME" || -z "$LABEL" || -z "$PRIV" ]]; then
  echo "Bundle is missing required fields." >&2
  exit 1
fi

echo "Server registered this key under label: $LABEL"
echo "(Used on the server to revoke this laptop later.)"
echo
read -rp "SSH alias to use locally — what you'll type as 'ssh <alias>' (e.g. wsl-home): " ALIAS
ALIAS=$(printf '%s' "$ALIAS" | tr -c 'A-Za-z0-9._-' '-' | sed 's/^-*//;s/-*$//')
if [[ -z "$ALIAS" ]]; then
  echo "Alias is required." >&2
  exit 1
fi

mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"

KEY_PATH="$HOME/.ssh/$ALIAS"
if [[ -e "$KEY_PATH" ]]; then
  echo "Refusing to overwrite existing key at $KEY_PATH" >&2
  exit 1
fi
printf '%s\n' "$PRIV" > "$KEY_PATH"
chmod 600 "$KEY_PATH"

CONFIG="$HOME/.ssh/config"
touch "$CONFIG"
chmod 600 "$CONFIG"

if grep -qE "^Host[[:space:]]+$ALIAS\$" "$CONFIG"; then
  echo "SSH config already contains Host $ALIAS — skipping config update." >&2
else
  cat >> "$CONFIG" <<EOF

Host $ALIAS
  HostName $HOST
  Port $PORT
  User $USER_NAME
  IdentityFile $KEY_PATH
  IdentitiesOnly yes
EOF
fi

echo
echo "Installed key at: $KEY_PATH"
echo "Added SSH config entry: Host $ALIAS"
echo "Connect with:  ssh $ALIAS"
