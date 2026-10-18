#!/usr/bin/env bash
# install-linux.sh
# Set up a fresh Linux (Debian/Ubuntu, apt-based) machine for octo-setup:
#   - Install git, curl, ca-certificates, gnupg
#   - Install gh (GitHub CLI) from the official apt repo
#   - Install desktop apps: Google Chrome, VS Code (official apt repos)
#   - Disable GNOME LocalSearch indexing for the installing user
#   - Install NVIDIA drivers (Ubuntu signed modules) + NVIDIA CUDA toolkit
#     (only when an NVIDIA GPU is present; a reboot is needed after the driver)
#   - Install OctoCode's build/runtime libraries (OpenSSL, ALSA, cmake, clang,
#     ffmpeg, etc.) so `cargo build` works on a fresh box
#   - Ensure at least 32 GiB of persistent swap for short memory spikes
#   - Attach the existing Linux data SSD configured in setup/.env (never format)
#   - Configure this box as an internal-only server:
#       * SSH server with key-only auth (no passwords, no root login)
#       * ufw firewall: deny all inbound except SSH from the LAN and your web
#         port from specific internal IPs (configured in setup/.env)
#       * power: never auto-suspend/hibernate; blank screen after 5 min, no lock
#   - Set git globals (matches install-mac.sh)
#   - Log in to GitHub via gh (browser device flow) and wire gh up as the
#     git credential helper so HTTPS push/pull works without passwords
#
# Run with: bash install-linux.sh
# Safe to re-run: installed tools are skipped, managed config refreshed, and Rust updated.
#
# Unlike install-mac.sh, this script *runs* `gh auth login` for you. The login
# is interactive: it prints a one-time code and opens your browser. Run this
# script in a real terminal on the target machine so the browser flow can
# complete (use the "paste a token" option if the machine is headless).
set -u

# Directory this script lives in, so it can find install-components/ regardless of cwd.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Server/network config (git identity, SSH CIDR, web port + allowed IPs) comes from
# setup/.env — see .env.example. This machine is set up as an internal-only server:
# SSH is locked to key-only auth and ufw denies all inbound except those rules.
# shellcheck source=load-env.sh
. "$SCRIPT_DIR/load-env.sh"
require_env INTERNAL_SSH_CIDR SSH_PORT

# ---------- helpers ----------

require_sudo() {
  if sudo -n true 2>/dev/null; then return 0; fi
  echo "This script needs sudo. Enter your password to continue."
  sudo -v || { echo "sudo authentication failed."; exit 1; }
}

ensure_apt_pkg() {
  local pkg="$1"
  if dpkg -s "$pkg" >/dev/null 2>&1; then
    echo "apt: $pkg already installed — skipping"
  else
    sudo apt-get install -y "$pkg"
  fi
}

# Set a GNOME gsettings key (idempotent). Skips cleanly if gsettings, the schema,
# or a session D-Bus aren't available (e.g. run over plain SSH with no GUI
# session) — these are per-user desktop prefs and need the user's session bus.
ensure_gsetting() {
  local schema="$1" key="$2" want="$3" before after
  command -v gsettings >/dev/null 2>&1 || { echo "  gsettings not installed — skipping $key"; return 0; }
  gsettings writable "$schema" "$key" >/dev/null 2>&1 || { echo "  $schema $key not present — skipping"; return 0; }
  before="$(gsettings get "$schema" "$key" 2>/dev/null)"
  if ! gsettings set "$schema" "$key" "$want" 2>/dev/null; then
    echo "  couldn't set $key (no GUI session bus? run this in the desktop session) — skipping"
    return 0
  fi
  after="$(gsettings get "$schema" "$key" 2>/dev/null)"
  if [ "$before" = "$after" ]; then echo "  $key already = $after — skipping"; else echo "  $key: $before -> $after"; fi
}

# Disable indexing persistently, including desktop and D-Bus activation.
disable_localsearch() {
  local config_dir="${XDG_CONFIG_HOME:-$HOME/.config}"
  systemctl --user mask localsearch-3.service localsearch-control-3.service \
    localsearch-writeback-3.service || return 1
  mkdir -p "$config_dir/autostart" || return 1
  cat > "$config_dir/autostart/localsearch-3.desktop" <<'EOF'
[Desktop Entry]
Type=Application
Name=LocalSearch
Hidden=true
EOF
  [ "$?" -eq 0 ] || return 1
  if systemctl --user show-environment >/dev/null 2>&1; then
    systemctl --user daemon-reload || return 1
    systemctl --user stop localsearch-3.service localsearch-control-3.service \
      localsearch-writeback-3.service || return 1
  else
    echo "No user service manager available; LocalSearch will be disabled at next login."
  fi
}

# Fetch and dearmor an apt repo signing key into a keyring (idempotent).
# Args: <keyring-path> <key-url>
ensure_apt_repo_key() {
  local keyring="$1" url="$2"
  [ -f "$keyring" ] && return 0
  curl -fsSL "$url" | gpg --dearmor | sudo dd of="$keyring" status=none
  sudo chmod go+r "$keyring"
}

# Install Google Chrome from Google's official apt repo (amd64 only).
install_chrome() {
  if command -v google-chrome >/dev/null 2>&1 || command -v google-chrome-stable >/dev/null 2>&1; then
    echo "Google Chrome already installed — skipping"
    return 0
  fi
  if [ "$(dpkg --print-architecture)" != "amd64" ]; then
    echo "Google Chrome for Linux is amd64-only; this machine is $(dpkg --print-architecture) — skipping."
    echo "  Use Chromium instead:  sudo snap install chromium"
    return 0
  fi
  ensure_apt_repo_key /usr/share/keyrings/google-chrome.gpg https://dl.google.com/linux/linux_signing_key.pub
  echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] https://dl.google.com/linux/chrome/deb/ stable main" \
    | sudo tee /etc/apt/sources.list.d/google-chrome.list >/dev/null
  sudo apt-get update -qq
  sudo apt-get install -y google-chrome-stable
}

# Install VS Code from Microsoft's official apt repo.
install_vscode() {
  if command -v code >/dev/null 2>&1; then
    echo "VS Code already installed — skipping"
    return 0
  fi
  ensure_apt_repo_key /usr/share/keyrings/packages.microsoft.gpg https://packages.microsoft.com/keys/microsoft.asc
  echo "deb [arch=amd64,arm64,armhf signed-by=/usr/share/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" \
    | sudo tee /etc/apt/sources.list.d/vscode.list >/dev/null
  sudo apt-get update -qq
  sudo apt-get install -y code
}

# A damaged CUDA index can prevent even unrelated apt installs. Retry once after
# deleting only NVIDIA's downloaded indexes; sources and installed packages stay.
refresh_apt() {
  local log
  log="$(mktemp "$SCRIPT_DIR/.apt-update.XXXXXX")" || return 1
  if sudo apt-get update -qq --error-on=any >"$log" 2>&1; then
    cat "$log"
    rm -f "$log"
    return 0
  fi
  cat "$log" >&2
  if ! grep -qE 'Problem with MergeList /var/lib/apt/lists/developer\.download\.nvidia\.com_compute_cuda_repos_' "$log"; then
    rm -f "$log"
    return 1
  fi
  rm -f "$log"
  echo "Refreshing damaged NVIDIA CUDA package indexes (one retry)."
  sudo find /var/lib/apt/lists -maxdepth 1 -type f \
    -name 'developer.download.nvidia.com_compute_cuda_repos_*' -delete || return 1
  sudo apt-get update -qq --error-on=any
}

# Ubuntu supplies signed modules for Secure Boot. Upgrade the kernel and NVIDIA
# tracking packages together; old kernels may require obsolete driver versions.
# https://ubuntu.com/server/docs/how-to/graphics/install-nvidia-drivers/
repair_ubuntu_nvidia_driver() {
  local drivers driver kernel flavour image target
  local -a module_packages=() kernel_images=()
  drivers="$(dpkg-query -W -f='${Package}\t${db:Status-Abbrev}\t${Depends}\n' 'nvidia-driver-*' 2>/dev/null \
    | awk -F '\t' '$2 ~ /^ii/ && $1 ~ /^nvidia-driver-[0-9]+(-server)?(-open)?$/ && $3 !~ /nvidia-driver-[0-9]/ {print $1}')"
  if [ -z "$drivers" ]; then
    sudo apt-get install -y ubuntu-drivers-common || return 1
    sudo ubuntu-drivers install || return 1
    drivers="$(dpkg-query -W -f='${Package}\t${db:Status-Abbrev}\t${Depends}\n' 'nvidia-driver-*' 2>/dev/null \
      | awk -F '\t' '$2 ~ /^ii/ && $1 ~ /^nvidia-driver-[0-9]+(-server)?(-open)?$/ && $3 !~ /nvidia-driver-[0-9]/ {print $1}')"
  fi
  if [ -z "$drivers" ] || [[ "$drivers" == *$'\n'* ]]; then
    echo "ERROR: expected one installed Ubuntu NVIDIA driver; found: ${drivers:-none}" >&2
    return 1
  fi
  driver="${drivers#nvidia-driver-}"
  kernel="$(uname -r)"
  flavour="${kernel##*-}"
  # Follow the installed kernel track, including HWE/OEM suffixes. uname alone
  # cannot distinguish generic from generic-hwe-<release>.
  while IFS= read -r image; do
    [ -n "$image" ] || continue
    kernel_images+=("$image")
    module_packages+=("linux-modules-nvidia-$driver-${image#linux-image-}")
  done < <(dpkg-query -W -f='${Package} ${db:Status-Abbrev}\n' "linux-image-$flavour*" 2>/dev/null \
    | awk '$2 == "ii" {print $1}')
  if [ "${#module_packages[@]}" -eq 0 ]; then
    echo "ERROR: no installed kernel tracking package for $flavour; cannot ensure future NVIDIA modules." >&2
    return 1
  fi
  echo "Installing matching kernel and NVIDIA $driver tracking packages."
  sudo apt-get install -y "${kernel_images[@]}" "${module_packages[@]}" "$drivers" || return 1
  for image in "${kernel_images[@]}"; do
    target="$(dpkg-query -W -f='${Depends}\n' "$image" \
      | grep -oE 'linux-image-[0-9][^ ,(|)]*')" || return 1
    if [ -z "$target" ] || [[ "$target" == *$'\n'* ]]; then
      echo "ERROR: cannot determine the installed kernel for $image." >&2
      return 1
    fi
    target="${target#linux-image-}"
    sudo depmod -a "$target" || return 1
    if [ ! -f "/boot/vmlinuz-$target" ] || ! modinfo -k "$target" nvidia >/dev/null 2>&1; then
      echo "ERROR: kernel or NVIDIA module is missing for $target." >&2
      return 1
    fi
    echo "NVIDIA module installed for $target (running kernel: $kernel)."
  done
  echo "Reboot into the updated kernel, then verify with nvidia-smi."
}

# Pick the NVIDIA CUDA apt repo path for this machine (e.g. ubuntu2404). NVIDIA
# publishes one repo per distro release; brand-new releases may not have one yet,
# so we probe and fall back to the newest known-good repo. Echoes the repo slug.
nvidia_cuda_repo() {
  local arch ver candidate base
  arch="$(uname -m)"                     # x86_64 on the 4090 box
  ver="${VERSION_ID//./}"                # 2604 for 26.04 (from /etc/os-release)
  base="https://developer.download.nvidia.com/compute/cuda/repos"
  for candidate in "ubuntu${ver}" ubuntu2404 ubuntu2204; do
    if curl -fsI "$base/$candidate/$arch/cuda-keyring_1.1-1_all.deb" >/dev/null 2>&1; then
      echo "$candidate"
      return 0
    fi
  done
  return 1
}

# Install the NVIDIA driver and full CUDA toolkit from NVIDIA's official apt repo.
install_cuda() {
  command -v lspci >/dev/null 2>&1 || ensure_apt_pkg pciutils
  if ! lspci 2>/dev/null | grep -qi nvidia; then
    echo "No NVIDIA GPU detected (lspci) — skipping CUDA install."
    return 0
  fi

  . /etc/os-release
  if [ "$ID" = ubuntu ]; then
    repair_ubuntu_nvidia_driver || return 1
  fi

  # CUDA availability must not prevent Ubuntu driver repair above.
  if command -v nvcc >/dev/null 2>&1; then
    if [ "$ID" = ubuntu ] || nvidia-smi >/dev/null 2>&1; then
      echo "CUDA toolkit already installed — skipping toolkit install."
      nvcc --version
      return
    fi
  fi

  local arch repo
  arch="$(uname -m)"
  if ! repo="$(nvidia_cuda_repo)"; then
    echo "No NVIDIA CUDA apt repo found for ${ID}${VERSION_ID}/$arch — skipping."
    echo "  Install manually from https://developer.nvidia.com/cuda-downloads"
    return 0
  fi
  echo "Using NVIDIA CUDA repo: $repo ($arch)"

  # The driver builds a kernel module via DKMS — needs a compiler + matching headers.
  if [ "$ID" != ubuntu ]; then
    ensure_apt_pkg build-essential || return 1
    ensure_apt_pkg "linux-headers-$(uname -r)" || return 1
  fi

  # Add NVIDIA's CUDA apt repo via their keyring package (idempotent).
  if [ ! -f /usr/share/keyrings/cuda-archive-keyring.gpg ]; then
    local tmp status
    tmp="$(mktemp -d "$SCRIPT_DIR/.cuda-keyring.XXXXXX")" || return 1
    if curl -fsSL -o "$tmp/cuda-keyring.deb" \
      "https://developer.download.nvidia.com/compute/cuda/repos/$repo/$arch/cuda-keyring_1.1-1_all.deb" \
      && sudo dpkg -i "$tmp/cuda-keyring.deb"; then
      status=0
    else
      status=1
    fi
    rm -rf "$tmp"
    [ "$status" -eq 0 ] || return "$status"
  fi
  refresh_apt || return 1

  # Latest toolkit + driver. If a working driver is already present, don't risk
  # clobbering it — install the toolkit only.
  if [ "$ID" = ubuntu ] || { command -v nvidia-smi >/dev/null 2>&1 && nvidia-smi >/dev/null 2>&1; }; then
    echo "Installing CUDA toolkit without replacing the NVIDIA driver."
    sudo apt-get install -y cuda-toolkit
  else
    sudo apt-get install -y cuda-toolkit cuda-drivers
  fi
}

# Persist CUDA on PATH/LD_LIBRARY_PATH in ~/.bashrc (idempotent).
persist_cuda_path() {
  [ -d /usr/local/cuda/bin ] || return 0
  local rc="$HOME/.bashrc" marker='# octo-setup: CUDA'
  if grep -qF "$marker" "$rc" 2>/dev/null; then
    echo "CUDA already on PATH in $rc — skipping"
    return 0
  fi
  {
    echo ""
    echo "$marker"
    echo 'export PATH=/usr/local/cuda/bin:$PATH'
    echo 'export LD_LIBRARY_PATH=/usr/local/cuda/lib64:$LD_LIBRARY_PATH'
  } >> "$rc"
  echo "Added CUDA to PATH in $rc — open a new shell (or 'source $rc') to use nvcc."
}

# If Secure Boot is on, an unsigned NVIDIA module won't load — warn with the fix.
warn_secure_boot() {
  command -v mokutil >/dev/null 2>&1 || return 0
  if mokutil --sb-state 2>/dev/null | grep -qi enabled; then
    cat <<'EOF'
NOTE: Secure Boot is ENABLED. The NVIDIA kernel module must be signed and
enrolled or the driver won't load after reboot. If the driver install prompted
you to set a one-time password, then on the NEXT reboot pick "Enroll MOK" in the
blue MOK Manager screen and enter that password. Ubuntu's prebuilt signed
modules do not need MOK enrollment. Keep Secure Boot enabled.
EOF
  fi
}

# Install the system libraries OctoCode needs to build (and run) on Linux.
# Source of truth: octo-code's scripts/install_dependencies.sh (Linux base set).
# Without these, `cargo build` fails on the native -sys crates:
#   libssl-dev      -> openssl-sys (reqwest's default native-tls) — blocks ALL binaries
#   cmake           -> whisper-rs-sys / ort (build whisper.cpp + ONNX) — voice feature
#   libasound2-dev  -> alsa-sys via cpal (audio capture)            — voice feature
# clang + libclang-dev back bindgen; build-essential/pkg-config are the C
# toolchain + lib discovery. wget/jq/espeak-ng/ffmpeg/imagemagick are runtime
# tools OctoCode shells out to. curl + git are already installed in Step 2.
# Idempotent: ensure_apt_pkg skips anything already present.
install_octocode_deps() {
  local pkg
  for pkg in \
    build-essential pkg-config \
    libssl-dev cmake libasound2-dev clang libclang-dev \
    wget jq espeak-ng ffmpeg imagemagick
  do
    ensure_apt_pkg "$pkg"
  done
}

# Install + harden the SSH server for key-only auth. Refuses to disable password
# auth unless a public key is already present (otherwise you'd lock yourself out).
setup_ssh_server() {
  ensure_apt_pkg openssh-server

  local akeys="$HOME/.ssh/authorized_keys"
  if [ ! -s "$akeys" ] || ! grep -qE '^(ssh-(ed25519|rsa)|ecdsa-)' "$akeys" 2>/dev/null; then
    echo "WARNING: no SSH public key in $akeys."
    echo "  NOT disabling password auth — that would lock you out of this server."
    echo "  Add your laptop's key first:  ./grant-ssh-access.sh   (then re-run this script)"
    echo "  sshd will be installed/enabled with the distro defaults for now."
  else
    # Drop-in keeps us from ever mangling the distro's sshd_config.
    local conf=/etc/ssh/sshd_config.d/00-octo-hardening.conf
    sudo tee "$conf" >/dev/null <<EOF
# octo-setup: key-only SSH hardening
PasswordAuthentication no
KbdInteractiveAuthentication no
ChallengeResponseAuthentication no
PubkeyAuthentication yes
PermitRootLogin no
EOF
    echo "Wrote $conf — key-only auth, root login disabled."
  fi

  # Validate before (re)starting so a bad config can't take sshd down.
  if sudo sshd -t; then
    sudo systemctl enable ssh >/dev/null 2>&1 || true
    sudo systemctl restart ssh
    echo "sshd enabled and (re)started."
  else
    echo "ERROR: 'sshd -t' failed — leaving sshd as-is. Fix the config and re-run." >&2
  fi
}

# Configure ufw: deny all inbound except SSH from the LAN and the web port from
# specific IPs. Allow rules are added BEFORE enabling so default-deny can't cut SSH.
setup_firewall() {
  ensure_apt_pkg ufw

  sudo ufw allow from "$INTERNAL_SSH_CIDR" to any port "$SSH_PORT" proto tcp \
    comment 'octo: SSH from internal LAN'

  if [ -n "$WEB_PORT" ] && [ "${#WEB_ALLOWED_IPS[@]}" -gt 0 ]; then
    local entry ip label
    for entry in "${WEB_ALLOWED_IPS[@]}"; do
      ip="${entry%% *}"            # first field
      label="${entry#* }"         # remainder after the first space
      [ "$label" = "$entry" ] && label="web allowed"   # no label given
      sudo ufw allow from "$ip" to any port "$WEB_PORT" proto tcp \
        comment "octo web: $label"
      echo "  allowed $ip ($label) → port $WEB_PORT"
    done
  else
    echo "WEB_PORT / WEB_ALLOWED_IPS not set — no web allow rule added; existing rules unchanged."
    echo "  Set them in $SCRIPT_DIR/.env, then re-run to open it."
  fi

  sudo ufw default deny incoming
  sudo ufw default allow outgoing
  sudo ufw --force enable
  echo
  sudo ufw status verbose
}

# Power/idle behaviour for an always-on box: never auto-suspend, blank the
# screen after 5 min, but DON'T lock (no password to wake). The display/lock
# prefs are per-user GNOME settings (gsettings); the hard "can never suspend"
# guarantee is a system-level mask of the sleep targets (needs root). Idempotent.
setup_power() {
  echo "GNOME display/idle prefs:"
  ensure_gsetting org.gnome.desktop.session               idle-delay                     300      # blank screen after 5 min
  ensure_gsetting org.gnome.desktop.screensaver           lock-enabled                   false    # no password on wake
  ensure_gsetting org.gnome.settings-daemon.plugins.power sleep-inactive-ac-type         nothing  # never suspend on AC
  ensure_gsetting org.gnome.settings-daemon.plugins.power sleep-inactive-ac-timeout      0
  ensure_gsetting org.gnome.settings-daemon.plugins.power sleep-inactive-battery-type    nothing  # (desktop has no battery; harmless)
  ensure_gsetting org.gnome.settings-daemon.plugins.power sleep-inactive-battery-timeout 0

  echo "System suspend block:"
  local t already=1
  local targets="sleep.target suspend.target hibernate.target hybrid-sleep.target suspend-then-hibernate.target"
  for t in $targets; do
    [ "$(systemctl is-enabled "$t" 2>/dev/null)" = masked ] || already=0
  done
  if [ "$already" = 1 ]; then
    echo "  sleep/suspend/hibernate targets already masked — skipping"
  elif sudo systemctl mask $targets >/dev/null 2>&1; then
    echo "  masked sleep/suspend/hibernate targets — system can no longer auto-suspend."
  else
    echo "  WARNING: couldn't mask sleep targets — system-level suspend NOT blocked."
  fi
}

# ---------- preflight ----------
# Must run as your normal user, NOT with sudo. gh stores your login under
# $HOME/.config/gh and git writes globals to $HOME/.gitconfig; running the whole
# script as root points those at /root, so gh can't see your existing login and
# re-prompts, and your git identity lands in root's config instead of yours.
# The script escalates with sudo only for the apt steps that need it.
if [ "$(id -u)" -eq 0 ]; then
  echo "ERROR: Don't run this script as root / with sudo." >&2
  if [ -n "${SUDO_USER:-}" ]; then
    echo "  Re-run it as yourself:  bash install-linux.sh" >&2
  fi
  echo "  It will ask for your sudo password once, only for the apt install steps." >&2
  exit 1
fi
if ! command -v apt-get >/dev/null 2>&1; then
  echo "ERROR: This script targets Debian/Ubuntu (apt). No apt-get found." >&2
  echo "  On Fedora/RHEL use dnf; on Arch use pacman — adapt the package steps." >&2
  exit 1
fi
require_sudo

echo "=== Disable GNOME LocalSearch indexing ==="
disable_localsearch || { echo "ERROR: could not disable LocalSearch." >&2; exit 1; }
echo

# ---------- Step 1: inspect ----------
echo "=== Step 1: inspect existing tools ==="
command -v git && git --version || echo "git: not installed"
command -v gh  && gh --version | head -n1 || echo "gh: not installed"
command -v curl && curl --version | head -n1 || echo "curl: not installed"
echo

# ---------- Step 2: install apt packages ----------
echo "=== Step 2: install apt packages ==="
refresh_apt || { echo "ERROR: apt index refresh failed." >&2; exit 1; }
ensure_apt_pkg curl
ensure_apt_pkg ca-certificates
ensure_apt_pkg gnupg
ensure_apt_pkg git
ensure_apt_pkg python-is-python3
echo

# ---------- Step 3: install gh (GitHub CLI) ----------
# Use the official GitHub apt repo so we get a current gh on any Debian/Ubuntu
# release (distro packages are often old or absent).
echo "=== Step 3: install gh (GitHub CLI) ==="
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
echo

# ---------- Step 4: configure git globals ----------
echo "=== Step 4: configure git globals ==="
ensure_git_global user.name  "$GIT_USER_NAME"
ensure_git_global user.email "$GIT_USER_EMAIL"
ensure_git_global pull.rebase true
echo

# ---------- Step 5: install desktop apps (Chrome, VS Code) ----------
echo "=== Step 5: install desktop apps (Chrome, VS Code) ==="
install_chrome
install_vscode
echo

# ---------- Step 6: gh auth login ----------
echo "=== Step 6: gh auth login ==="
if gh auth status >/dev/null 2>&1; then
  echo "gh already authenticated — skipping login"
  gh auth status
else
  echo "Starting GitHub login (HTTPS, browser device flow)."
  echo "A one-time code will be shown — your browser opens to github.com/login/device."
  echo "On a headless machine, choose 'Paste an authentication token' instead."
  echo
  gh auth login --hostname github.com --git-protocol https --web
fi
echo

# ---------- Step 7: wire gh up as git credential helper ----------
echo "=== Step 7: configure git to use gh credentials over HTTPS ==="
if gh auth status >/dev/null 2>&1; then
  gh auth setup-git
  echo "git is now configured to use your gh token for HTTPS operations."
else
  echo "Skipping — gh is not authenticated, so there are no credentials to wire up."
fi
echo

# ---------- Step 8: Rust toolchain ----------
echo "=== Step 8: install Rust toolchain (rustup) ==="
bash "$SCRIPT_DIR/install-components/install-rust.sh" || echo "WARNING: Rust install component failed — see output above."
echo

# ---------- Step 9: tmux (OctoCode needs >= 3.6) ----------
echo "=== Step 9: install tmux (build 3.7 from source if apt's is too old) ==="
bash "$SCRIPT_DIR/install-components/install-tmux.sh" || echo "WARNING: tmux install component failed — see output above."
echo

# ---------- Step 10: install CUDA (NVIDIA driver + full toolkit) ----------
echo "=== Step 10: install CUDA (NVIDIA driver + full toolkit) ==="
install_cuda || { echo "ERROR: NVIDIA/CUDA setup failed — see output above." >&2; exit 1; }
persist_cuda_path
warn_secure_boot
echo

# ---------- Step 11: OctoCode build/runtime dependencies ----------
echo "=== Step 11: OctoCode build/runtime dependencies ==="
install_octocode_deps
echo

# ---------- Step 12: emergency swap capacity ----------
echo "=== Step 12: configure 32 GiB emergency swap capacity ==="
bash "$SCRIPT_DIR/install-components/configure-swap.sh" || {
  echo "ERROR: swap configuration failed — see output above." >&2
  exit 1
}
echo

# ---------- Step 13: SSH server (key-only auth) ----------
echo "=== Step 13: SSH server (key-only auth) ==="
setup_ssh_server
echo

# ---------- Step 14: firewall (internal-only: SSH from LAN, web from set IPs) ----------
echo "=== Step 14: firewall (ufw — internal-only) ==="
setup_firewall
echo

# ---------- Step 15: power (never suspend; blank screen, no lock) ----------
echo "=== Step 15: power settings (never suspend; blank screen, no lock) ==="
setup_power
echo

echo "=== Step 16: Linux data SSD ==="
bash "$SCRIPT_DIR/install-components/configure-storage.sh" || {
  echo "ERROR: storage setup failed; inspect lsblk before retrying." >&2
  exit 1
}
echo

echo "=== Done ==="
echo "Verify with:"
echo "  gh auth status  &&  git config --global --list"
echo "  sudo ufw status verbose          # firewall rules"
echo "  sudo sshd -T | grep -Ei 'passwordauthentication|permitrootlogin'   # key-only?"
echo "  swapon --show                    # at least 32 GiB total swap"
echo "  pkg-config --exists alsa openssl && echo 'OctoCode build libs OK'   # build deps"
if lspci 2>/dev/null | grep -qi nvidia; then
  echo "  nvidia-smi          # GPU + driver (REBOOT first if the driver was just installed)"
  echo "  nvcc --version      # CUDA toolkit (open a new shell so PATH picks it up)"
  echo
  echo "If the NVIDIA driver was installed this run, REBOOT before the GPU is usable:  sudo reboot"
fi
