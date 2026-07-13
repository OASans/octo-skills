# setup — machine provisioning

Provision a fresh machine for OctoCode development: dev tools, desktop apps, Rust, tmux, CUDA, and (on Linux) an internal-only SSH server.

Separate from the repo's top-level `install.sh`, which deploys the Claude Code + Codex skills and config. These scripts set up the *machine*; `install.sh` sets up the *agents*.

## First: create `.env`

Every install script reads its machine-specific values — git identity, LAN topology — from `setup/.env`, which is **gitignored** and never committed. Nothing runs without it:

```bash
cp setup/.env.example setup/.env   # then fill it in
```

`.env.example` documents each value. It's bash (the scripts `source` it), not a generic dotenv file.

## Then: run the script for your platform

Each is idempotent — safe to re-run, every step skips work already done.

| Platform | Script | Notes |
|----------|--------|-------|
| Linux (Debian/Ubuntu) | `bash setup/install-linux.sh` | Also provisions at least 32 GiB of persistent swap and hardens the box as an internal-only server: key-only SSH, ufw default-deny, never auto-suspend. Installs CUDA when an NVIDIA GPU is present — **reboot** after a fresh driver install. |
| macOS | `bash setup/install-mac.sh` | Homebrew, gh, casks, Xcode. Xcode's license/first-launch steps need sudo and are printed for you to run. |
| Windows + WSL2 | `install-windows.ps1`, then `install-wsl2.sh` | See the ordering below. |

`install-components/` holds the pieces shared across platforms (`install-rust.sh`, `install-tmux.sh`); the platform scripts call them.

## WSL2 ordering

The Windows host and the WSL guest must be configured in this order — the host sets mirrored networking, which the guest depends on:

1. `install-windows.ps1` on the Windows host, from an **elevated** PowerShell.
2. `wsl --shutdown` (close all WSL terminals first).
3. `bash setup/install-wsl2.sh` inside WSL.

## SSH access to the server

Run these once per laptop you want to let in. The keypair is generated on the server at run time; no key material is ever stored in this repo.

1. On the **server**: `bash setup/grant-ssh-access.sh` — generates an ed25519 keypair, appends the public key to `authorized_keys`, and prints a base64 bundle (also copied to your clipboard).
2. On the **laptop**: `bash setup/accept-ssh-access.sh` — paste the bundle. It installs the private key and adds a `~/.ssh/config` entry, so you can then just `ssh <alias>`.

To revoke a laptop, delete its line from the server's `~/.ssh/authorized_keys` — each is labelled with the name you chose in step 1.
