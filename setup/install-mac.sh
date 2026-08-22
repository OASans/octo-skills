#!/usr/bin/env bash
# Setup script: configure macOS dev tools, desktop apps, GitHub auth, and Codex.
# Run with: bash install-mac.sh
# Safe to re-run — every step skips work that's already done.
set -u

# Directory this script lives in, so it can find install-components/ regardless of cwd.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Git identity comes from setup/.env — see .env.example.
# shellcheck source=load-env.sh
. "$SCRIPT_DIR/load-env.sh"

# ---------- helpers ----------

# Source brew into the current shell if it exists anywhere standard.
load_brew_into_path() {
  if command -v brew >/dev/null 2>&1; then return 0; fi
  if [ -x /opt/homebrew/bin/brew ]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  elif [ -x /usr/local/bin/brew ]; then
    eval "$(/usr/local/bin/brew shellenv)"
  fi
}

# Persist `eval $(brew shellenv)` to ~/.zprofile if missing.
persist_brew_shellenv() {
  local brew_bin
  brew_bin="$(command -v brew || true)"
  [ -z "$brew_bin" ] && return 0
  local zprofile="$HOME/.zprofile"
  local line="eval \"\$(${brew_bin} shellenv)\""
  if ! grep -qsF "$line" "$zprofile"; then
    echo "$line" >> "$zprofile"
    echo "Added brew shellenv to $zprofile"
  else
    echo "brew shellenv already in $zprofile — skipping"
  fi
}

# Install a Homebrew cask if its .app isn't already in /Applications.
# Args: <cask-name> <App Bundle Name>.app
ensure_cask() {
  local cask="$1" app="$2"
  if [ -d "/Applications/$app" ] || [ -d "$HOME/Applications/$app" ]; then
    echo "$app already installed — skipping cask $cask"
  elif brew list --cask "$cask" >/dev/null 2>&1; then
    echo "Cask $cask already installed via brew — skipping"
  else
    brew install --cask "$cask"
  fi
}

# ---------- Preflight: Xcode license ----------
# /usr/bin/git is a stub that goes through xcrun; an unaccepted Xcode license
# blocks every git invocation by dumping the license text and waiting on stdin.
# Detect that case up front (with all I/O redirected so the license doesn't
# flood the terminal) and exit with a clear instruction.
preflight_xcode_license() {
  [ -d "/Applications/Xcode.app" ] || return 0
  local xcode_dev_dir
  xcode_dev_dir="$(xcode-select -p 2>/dev/null || true)"
  case "$xcode_dev_dir" in
    /Applications/Xcode.app/*) ;;
    *) return 0 ;;
  esac
  if /usr/bin/xcrun --find git </dev/null >/dev/null 2>&1; then
    return 0
  fi
  cat <<'EOF'
Xcode is installed and selected, but its license has not been accepted yet.
Every git and xcodebuild call below would be blocked by the license prompt.

Run this yourself in the prompt (interactive — needs sudo):

    !sudo xcodebuild -license accept

Then re-run this script with:  bash install-mac.sh
EOF
  exit 1
}
preflight_xcode_license

# ---------- Preflight: Xcode first-launch components ----------
# After license accept, xcodebuild still needs CoreSimulator and other
# privately-installed frameworks before any build/test will succeed.
# `-checkFirstLaunchStatus` returns 0 when first-launch tasks are done.
preflight_xcode_first_launch() {
  [ -d "/Applications/Xcode.app" ] || return 0
  local xcode_dev_dir
  xcode_dev_dir="$(xcode-select -p 2>/dev/null || true)"
  case "$xcode_dev_dir" in
    /Applications/Xcode.app/*) ;;
    *) return 0 ;;
  esac
  if xcodebuild -checkFirstLaunchStatus </dev/null >/dev/null 2>&1; then
    return 0
  fi
  cat <<'EOF'
Xcode is installed but first-launch components (CoreSimulator framework, etc.)
have not been set up. xcodebuild build/test will fail until they're installed.

Run this yourself in the prompt (interactive — needs sudo, downloads a few hundred MB):

    !sudo xcodebuild -runFirstLaunch

Then re-run this script with:  bash install-mac.sh
EOF
  exit 1
}
preflight_xcode_first_launch

# ---------- Step 1: inspect ----------
echo "=== Step 1: inspect existing tools ==="
echo "--- gh ---"
command -v gh && gh --version || echo "gh: not installed"
echo "--- git ---"
command -v git && git --version || echo "git: not installed"
echo "--- brew ---"
if command -v brew >/dev/null 2>&1; then
  brew --version
elif [ -x /opt/homebrew/bin/brew ]; then
  echo "brew found at /opt/homebrew/bin/brew (not on PATH yet)"
elif [ -x /usr/local/bin/brew ]; then
  echo "brew found at /usr/local/bin/brew (not on PATH yet)"
else
  echo "brew: not installed"
fi
echo "--- curl ---"
command -v curl && curl --version | head -n1 || echo "curl: not installed"
echo

# Make brew available for the rest of this script if it's installed at all.
load_brew_into_path

# ---------- Step 2: configure git globals ----------
echo "=== Step 2: configure git globals ==="
ensure_git_global user.name  "$GIT_USER_NAME"
ensure_git_global user.email "$GIT_USER_EMAIL"
ensure_git_global pull.rebase true
echo

# ---------- Step 3: install Homebrew ----------
echo "=== Step 3: install Homebrew (if missing) ==="
if command -v brew >/dev/null 2>&1; then
  echo "brew already installed at: $(command -v brew) — skipping install"
else
  echo "Installing Homebrew. You'll be prompted to press RETURN, then for your sudo password."
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  load_brew_into_path
  if ! command -v brew >/dev/null 2>&1; then
    echo "ERROR: Homebrew install did not complete — no brew binary found."
    echo "Common cause: your account isn't a macOS admin (required to install to /opt/homebrew)."
    echo "Stopping. Tell me if you'd like to switch to a no-admin install (gh binary into ~/.local/bin)."
    exit 1
  fi
fi
# Always make sure the shellenv line is persisted, even if brew was pre-existing.
persist_brew_shellenv
echo

# ---------- Step 4: install gh ----------
echo "=== Step 4: install gh (if missing) ==="
if command -v gh >/dev/null 2>&1; then
  echo "gh already installed ($(gh --version | head -n1)) — skipping install"
else
  brew install gh
fi
echo

# ---------- Step 5: install desktop apps (Chrome, VSCode, Discord, iTerm2) ----------
echo "=== Step 5: install desktop apps (Chrome, VSCode, Discord, iTerm2) ==="
ensure_cask google-chrome      "Google Chrome.app"
ensure_cask visual-studio-code "Visual Studio Code.app"
ensure_cask discord            "Discord.app"
ensure_cask iterm2             "iTerm.app"
echo

# ---------- Step 6: Rust toolchain ----------
echo "=== Step 6: install Rust toolchain (rustup) ==="
bash "$SCRIPT_DIR/install-components/install-rust.sh" || echo "WARNING: Rust install component failed — see output above."
echo

# ---------- Step 7: tmux (Homebrew) ----------
echo "=== Step 7: install tmux (Homebrew) ==="
bash "$SCRIPT_DIR/install-components/install-tmux.sh" || echo "WARNING: tmux install component failed — see output above."
echo

# ---------- Step 8: install / select Xcode ----------
echo "=== Step 8: install / select Xcode (if missing) ==="
xcode_dev_dir="$(xcode-select -p 2>/dev/null || true)"
if [ -d "/Applications/Xcode.app" ] && [ "$xcode_dev_dir" = "/Applications/Xcode.app/Contents/Developer" ]; then
  echo "Xcode already installed and selected — skipping"
  xcodebuild -version 2>/dev/null || true
elif [ -d "/Applications/Xcode.app" ]; then
  echo "Xcode is installed but xcode-select points at: ${xcode_dev_dir:-<unset>}"
  cat <<'EOF'
Run these yourself in the prompt (interactive — needs sudo):

    !sudo xcode-select -s /Applications/Xcode.app/Contents/Developer
    !sudo xcodebuild -license accept

Then re-run this script with:  bash install-mac.sh
EOF
else
  cat <<'EOF'
Xcode is NOT installed yet. Apple gates the full Xcode behind the App Store +
Apple ID auth, so this step can't be fully unattended.

Pick one:

  A) App Store (simplest):
     Open the App Store, search "Xcode", click Get/Install. ~10–20 min.

  B) xcodes CLI (scriptable, still asks for Apple ID once):
     brew install xcodesorg/made/xcodes aria2
     xcodes install --latest --select

After install, accept the license:

    !sudo xcodebuild -license accept

Then re-run this script with:  bash install-mac.sh
EOF
fi
echo

# ---------- Step 9: gh auth ----------
echo "=== Step 9: gh auth status ==="
if gh auth status >/dev/null 2>&1; then
  echo "gh already authenticated — skipping login"
  gh auth status
else
  cat <<'EOF'
gh is NOT authenticated yet.

Run this yourself in the prompt (interactive — opens a browser):

    !gh auth login

Then re-run this script with:  bash install-mac.sh
EOF
fi
echo

# ---------- Step 10: install Codex and shared agent config ----------
echo "=== Step 10: install Codex and shared agent config ==="
bash "$SCRIPT_DIR/../install.sh"
echo

echo "=== Done ==="
