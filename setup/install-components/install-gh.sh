#!/usr/bin/env bash
# Install GitHub CLI from its Debian/Ubuntu repository; also used by WSL2.
set -u

if command -v gh >/dev/null 2>&1; then
  echo "gh already installed ($(gh --version | head -n1)) — skipping install"
else
  KEYRING=/usr/share/keyrings/githubcli-archive-keyring.gpg
  if [ ! -f "$KEYRING" ]; then
    curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg \
      | sudo dd of="$KEYRING" status=none
    sudo chmod go+r "$KEYRING"
  fi
  echo "deb [arch=$(dpkg --print-architecture) signed-by=$KEYRING] https://cli.github.com/packages stable main" \
    | sudo tee /etc/apt/sources.list.d/github-cli.list >/dev/null
  sudo apt-get update -qq
  sudo apt-get install -y gh
fi
