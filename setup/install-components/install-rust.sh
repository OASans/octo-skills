#!/usr/bin/env bash
# install-components/install-rust.sh
# Install (or update) the Rust toolchain via rustup. Works on macOS and Linux
# (including WSL2). Idempotent: updates an existing toolchain, fresh-installs
# otherwise. Requires curl (present by default on macOS; install-linux.sh /
# install-wsl2.sh install it before calling this).
#
# Usage:  bash install-components/install-rust.sh
# Meant to be called by install-mac.sh / install-linux.sh / install-wsl2.sh.
set -u

echo "--- install-components: Rust toolchain ---"

# Detect platform (macos | linux). WSL2 reports as Linux, which is what we want.
case "$(uname -s)" in
  Darwin) PLATFORM="macos" ;;
  Linux)  PLATFORM="linux" ;;
  *)      PLATFORM="unknown" ;;
esac

# Make an existing rustup/cargo visible to this (non-login) shell.
if [ -f "$HOME/.cargo/env" ]; then
  # shellcheck disable=SC1091
  . "$HOME/.cargo/env"
fi

if command -v rustc >/dev/null 2>&1; then
  echo "Rust already installed ($(rustc --version)) — updating via rustup"
  rustup update || true
else
  echo "Installing Rust via rustup..."
  curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
  # shellcheck disable=SC1091
  . "$HOME/.cargo/env"
fi

# macOS release builds target Apple Silicon explicitly.
if [ "$PLATFORM" = "macos" ]; then
  if rustup target list --installed 2>/dev/null | grep -q '^aarch64-apple-darwin$'; then
    echo "aarch64-apple-darwin target already installed — skipping"
  else
    echo "Adding aarch64-apple-darwin target for release builds..."
    rustup target add aarch64-apple-darwin
  fi
fi

echo "Rust ready: $(rustc --version 2>/dev/null || echo 'open a new shell to pick up cargo/rustc on PATH')"
