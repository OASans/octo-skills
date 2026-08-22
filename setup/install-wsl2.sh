#!/usr/bin/env bash
# install-wsl2.sh
# Configure WSL2 (Ubuntu) for the octo-setup SSH server:
#   - Ensure /etc/wsl.conf has systemd=true
#   - Comment out duplicate `command = ... ssh start` if present (systemd
#     handles ssh; the duplicate causes "Address already in use" at boot)
#   - Install openssh-server, gh, git, curl
#   - Enable + start ssh.service
#   - Set git globals (matches install-mac.sh)
#
# Run with: bash install-wsl2.sh
# Safe to re-run — every step skips work that's already done.
#
# Order of operations across machines:
#   1. install-windows.ps1 on the Windows host (elevated PowerShell)
#   2. wsl --shutdown
#   3. install-wsl2.sh inside WSL  (this script)
#   4. grant-ssh-access.sh inside WSL → bundle to laptop
#   5. accept-ssh-access.sh on laptop with the bundle
set -u

# Directory this script lives in, so it can find install-components/ regardless of cwd.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Git identity comes from setup/.env — see .env.example.
# shellcheck source=load-env.sh
. "$SCRIPT_DIR/load-env.sh"

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

# ---------- preflight ----------
if ! grep -qiE 'microsoft|wsl' /proc/version 2>/dev/null; then
  echo "ERROR: This script is for WSL2. /proc/version doesn't look like WSL." >&2
  exit 1
fi
require_sudo

# ---------- Step 1: /etc/wsl.conf ----------
echo "=== Step 1: configure /etc/wsl.conf ==="
WSL_CONF=/etc/wsl.conf
if [ ! -f "$WSL_CONF" ]; then
  echo "$WSL_CONF does not exist — creating with [boot] systemd=true"
  printf '[boot]\nsystemd=true\n' | sudo tee "$WSL_CONF" >/dev/null
else
  if grep -q '^systemd=true' "$WSL_CONF"; then
    echo "$WSL_CONF already has systemd=true"
  else
    echo "WARNING: $WSL_CONF exists but doesn't have systemd=true under [boot]."
    echo "  Edit it manually — auto-fix avoided to prevent mangling other settings."
  fi
  if grep -qE '^command[[:space:]]*=.*ssh' "$WSL_CONF"; then
    echo "Found duplicate 'command = ... ssh' in $WSL_CONF — commenting out"
    echo "  (systemd's ssh.service is the canonical starter; the duplicate causes"
    echo "   'Address already in use' errors at boot.)"
    sudo cp "$WSL_CONF" "${WSL_CONF}.bak.$(date +%s)"
    sudo sed -i -E '/^command[[:space:]]*=.*ssh/s|^|# octo-setup: disabled (systemd handles ssh) -- |' "$WSL_CONF"
    echo "  Backup written; change applies after 'wsl --shutdown'."
  fi
fi
echo

# ---------- Step 2: install apt packages ----------
echo "=== Step 2: install apt packages ==="
sudo apt-get update -qq
ensure_apt_pkg curl
ensure_apt_pkg ca-certificates
ensure_apt_pkg git
ensure_apt_pkg openssh-server
echo

# ---------- Step 3: enable + start ssh.service ----------
echo "=== Step 3: enable + start ssh.service ==="
sudo systemctl enable ssh >/dev/null 2>&1 || true
if systemctl is-active --quiet ssh; then
  echo "ssh.service already active"
else
  if sudo systemctl start ssh; then
    echo "ssh.service started"
  else
    if sudo journalctl -u ssh -n 20 --no-pager 2>/dev/null | grep -q 'Address already in use'; then
      cat <<'EOF'

ERROR: ssh.service failed because port 22 is already in use on the host.

In WSL2 mirrored networking, the WSL VM shares the Windows host's network
namespace. A stale Windows netsh portproxy rule on port 22 will block sshd
inside WSL.

Fix: run install-windows.ps1 from an elevated PowerShell on the Windows host
(removes the stale portproxy + sets mirrored networking), then `wsl --shutdown`
and re-run this script.
EOF
      exit 1
    fi
    echo "ssh.service failed. See: sudo journalctl -u ssh -n 50 --no-pager"
    exit 1
  fi
fi
sudo systemctl status ssh --no-pager 2>/dev/null | head -5 || true
echo

# ---------- Step 4: install gh ----------
echo "=== Step 4: install gh (GitHub CLI) ==="
if command -v gh >/dev/null 2>&1; then
  echo "gh already installed ($(gh --version | head -n1))"
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

# ---------- Step 5: git globals ----------
echo "=== Step 5: configure git globals ==="
ensure_git_global user.name  "$GIT_USER_NAME"
ensure_git_global user.email "$GIT_USER_EMAIL"
ensure_git_global pull.rebase true
echo

# ---------- Step 6: Rust toolchain ----------
echo "=== Step 6: install Rust toolchain (rustup) ==="
bash "$SCRIPT_DIR/install-components/install-rust.sh" || echo "WARNING: Rust install component failed — see output above."
echo

# ---------- Step 7: tmux (OctoCode needs >= 3.6) ----------
echo "=== Step 7: install tmux (build 3.7 from source if apt's is too old) ==="
bash "$SCRIPT_DIR/install-components/install-tmux.sh" || echo "WARNING: tmux install component failed — see output above."
echo

# ---------- Step 8: status ----------
echo "=== Step 8: status ==="
DEFAULT_IFACE=$(ip -4 route show default 2>/dev/null | awk '{print $5; exit}')
if [ -n "$DEFAULT_IFACE" ]; then
  LAN_IP=$(ip -4 addr show "$DEFAULT_IFACE" 2>/dev/null | awk '/inet /{print $2; exit}' | cut -d/ -f1)
  echo "WSL LAN IP (default route via $DEFAULT_IFACE): ${LAN_IP:-<not detected>}"
fi
ss -tln 2>/dev/null | awk '$4 ~ /:22$/ {print "sshd listening on: " $4}'
echo
echo "Next: run grant-ssh-access.sh, share the bundle with your laptop,"
echo "      then run accept-ssh-access.sh on the laptop."

echo "=== Done ==="
