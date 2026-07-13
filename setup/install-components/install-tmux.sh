#!/usr/bin/env bash
# install-components/install-tmux.sh
# Ensure tmux meets OctoCode's minimum version on macOS and Linux (incl. WSL2).
#   - macOS:  install/upgrade via Homebrew (tracks the latest tmux release)
#   - Linux:  use apt's tmux if it's new enough, otherwise build
#             TMUX_BUILD_VERSION from source into /usr/local (Ubuntu LTS ships an
#             older tmux in apt — e.g. 22.04 → 3.2a — that OctoCode rejects)
#
# Usage:  bash install-components/install-tmux.sh
# Meant to be called by install-mac.sh / install-linux.sh / install-wsl2.sh.
set -u

echo "--- install-components: tmux ---"

# Minimum tmux version OctoCode needs (keep in sync with OctoCode's preflight).
TMUX_MIN_MAJOR=3
TMUX_MIN_MINOR=6
TMUX_BUILD_VERSION="3.7"    # built from source on Linux when apt's tmux is too old

case "$(uname -s)" in
  Darwin) PLATFORM="macos" ;;
  Linux)  PLATFORM="linux" ;;
  *)      PLATFORM="unknown" ;;
esac

# Parse a tmux-style version into "<major> <minor>" (base-10 digit runs), echoed
# on stdout. Handles "tmux 3.6a", "tmux next-3.7", "openbsd-7.4", "3.7". Echoes
# nothing when there's no parseable major.minor, so callers can detect failure.
parse_tmux_version() {
  local raw=$1 numeric major minor_tail minor c i
  raw=${raw#tmux }                 # tolerate a leading "tmux " (e.g. `tmux -V`)
  numeric=${raw##*-}               # drop a "next-"/"openbsd-" style prefix
  [[ "$numeric" == *.* ]] || return 0
  major=${numeric%%.*}
  minor_tail=${numeric#*.}
  minor=""
  for ((i=0; i<${#minor_tail}; i++)); do
    c=${minor_tail:i:1}
    [[ "$c" == [0-9] ]] || break   # stop at the letter suffix: "6a" -> "6"
    minor+="$c"
  done
  [[ "$major" =~ ^[0-9]+$ && -n "$minor" ]] || return 0
  printf '%s %s' "$major" "$minor"
}

# Returns 0 if the installed tmux is at least $1.$2 (OR is present with an
# unparseable version — don't lock out unknown-but-modern builds).
# Returns 1 only when tmux is missing or its version parses and is below $1.$2.
tmux_ge() {
  local want_major=$1 want_minor=$2 line major minor
  command -v tmux >/dev/null 2>&1 || return 1

  line=$(tmux -V 2>/dev/null)            # e.g. "tmux 3.6a" / "tmux next-3.7"
  read -r major minor < <(parse_tmux_version "$line")

  # Unparseable -> warn and treat as acceptable.
  if [[ -z "$major" || -z "$minor" ]]; then
    echo "  warning: could not parse tmux version from '$line' — assuming OK." >&2
    return 0
  fi

  # Force base-10 so leading-zero minors like "09" aren't read as octal.
  if (( 10#$major > 10#$want_major )); then return 0; fi
  if (( 10#$major == 10#$want_major && 10#$minor >= 10#$want_minor )); then return 0; fi
  return 1
}

# Meets OctoCode's minimum? (used by the macOS path)
tmux_version_ok() { tmux_ge "$TMUX_MIN_MAJOR" "$TMUX_MIN_MINOR"; }

# Already at (or above) the Linux build target? Fails fast if the build-target
# constant is malformed, rather than silently mis-gating the source rebuild.
tmux_at_build_target() {
  local major minor
  read -r major minor < <(parse_tmux_version "$TMUX_BUILD_VERSION")
  if [[ -z "$major" || -z "$minor" ]]; then
    echo "ERROR: could not parse TMUX_BUILD_VERSION='$TMUX_BUILD_VERSION'." >&2
    exit 1
  fi
  tmux_ge "$major" "$minor"
}

# macOS: Homebrew tracks the latest tmux, so install it (or upgrade if an old
# pinned/cached formula drifted below the minimum).
install_tmux_macos() {
  if ! command -v brew >/dev/null 2>&1; then
    echo "ERROR: Homebrew not found — install it first (install-mac.sh does this)." >&2
    exit 1
  fi
  if ! command -v tmux >/dev/null 2>&1; then
    echo "Installing tmux via Homebrew..."
    brew install tmux
  elif tmux_version_ok; then
    echo "tmux already OK ($(tmux -V)) — skipping"
  else
    echo "Homebrew tmux older than ${TMUX_MIN_MAJOR}.${TMUX_MIN_MINOR} — running 'brew upgrade tmux'..."
    brew upgrade tmux || true
  fi
  echo "tmux version: $(tmux -V 2>/dev/null || echo 'not installed')"
}

# Linux: build tmux $TMUX_BUILD_VERSION from source into /usr/local.
install_tmux_from_source() {
  echo "Installing tmux build dependencies via apt..."
  sudo apt-get install -y build-essential pkg-config libevent-dev libncurses-dev bison wget

  local tarball url
  tarball="tmux-${TMUX_BUILD_VERSION}.tar.gz"
  url="https://github.com/tmux/tmux/releases/download/${TMUX_BUILD_VERSION}/${tarball}"

  # Build in a subshell whose EXIT trap cleans up the temp tree on success or on
  # any failure (wget / configure / make / install). Bail out if it fails.
  if ! (
    set -e
    build_dir=$(mktemp -d)
    trap 'rm -rf "$build_dir"' EXIT
    cd "$build_dir"
    echo "Downloading $url ..."
    wget -q "$url" -O "$tarball"
    tar xzf "$tarball"
    cd "tmux-${TMUX_BUILD_VERSION}"
    ./configure
    make -j"$(nproc)"
    sudo make install
  ); then
    echo "ERROR: building tmux ${TMUX_BUILD_VERSION} from source failed." >&2
    exit 1
  fi

  # Flush the shell's command-path cache so `tmux` resolves to /usr/local/bin
  # instead of the apt-installed /usr/bin/tmux.
  hash -r
  echo "tmux built from source: $(tmux -V)"
}

# Linux: try apt's tmux first (quick win), build from source if it's still older
# than the build target (not just the minimum — so 3.6 upgrades to ${TMUX_BUILD_VERSION}).
install_tmux_linux() {
  sudo apt-get update -qq
  if ! command -v tmux >/dev/null 2>&1; then
    echo "Installing apt tmux first..."
    sudo apt-get install -y tmux || true
  fi
  if tmux_at_build_target; then
    echo "tmux version OK: $(tmux -V)"
  else
    echo "tmux missing or older than ${TMUX_BUILD_VERSION} — building ${TMUX_BUILD_VERSION} from source."
    install_tmux_from_source
  fi
}

# Only dispatch when executed directly — sourcing (e.g. from tests) just loads
# the helpers without kicking off an install.
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
  case "$PLATFORM" in
    macos) install_tmux_macos ;;
    linux) install_tmux_linux ;;
    *)     echo "Unsupported platform for tmux install: $(uname -s)" >&2; exit 1 ;;
  esac
fi
