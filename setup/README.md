# setup — machine provisioning

Provision a fresh machine for OctoCode development: dev tools, desktop apps, Rust, tmux, CUDA, and (on Linux) an internal-only SSH server.

The repo's top-level `install.sh` deploys shared Codex skills and config, and installs Codex CLI. Platform scripts set up the machine; the macOS script also runs `install.sh` as its final step so Codex is ready immediately.

## First: create `.env`

The Linux and macOS installers read git identity and relevant network settings from `setup/.env`, which is **gitignored** and required by those scripts:

```bash
cp setup/.env.example setup/.env   # then fill it in
```

`.env.example` documents each value. It's bash (the scripts `source` it), not a generic dotenv file.

## Then: run the script for your platform

Scripts can be rerun: they skip installed components, refresh managed configuration, and update Rust.

| Platform | Script | Notes |
|----------|--------|-------|
| Linux (Debian/Ubuntu) | `bash setup/install-linux.sh` | Also provisions at least 32 GiB of persistent swap and hardens the box as an internal-only server: key-only SSH, ufw default-deny, never auto-suspend. Installs CUDA when an NVIDIA GPU is present — **reboot** after a fresh driver install. |
| macOS | `bash setup/install-mac.sh` | Homebrew, gh, casks, Xcode, and Codex. Xcode's license/first-launch steps need sudo and are printed for you to run. |

On Ubuntu, every Linux installer run upgrades the installed kernel track and its NVIDIA module metapackage together for a matching kernel/driver set, even when CUDA is already installed. It uses Ubuntu's signed modules for Secure Boot and installs the CUDA toolkit separately. Missing module packages or failed installs stop setup with an error; reboot into the updated kernel after repair and check `nvidia-smi`. Older running kernels may require driver versions that conflict with current packages; setup verifies the updated kernel’s module instead. Other apt-based distributions retain the NVIDIA CUDA driver install path.

The first apt refresh retries once for a corrupted NVIDIA CUDA package index, deleting only downloaded CUDA indexes before fetching them again.

Every Linux installer run disables GNOME LocalSearch indexing for the installing user, blocking service and desktop startup. It stops the indexer immediately when the user service manager is available; otherwise the change takes effect at next login.

Linux installs `python-is-python3` so `python` runs Python 3 in terminals and agent commands.

`install-components/` holds the pieces shared across platforms (`install-rust.sh`, `install-tmux.sh`); the platform scripts call them.

Linux also attaches the optional data SSD selected by `SSD_DISK_ID` in `setup/.env`, using a stable whole-disk `/dev/disk/by-id/` path. No flags are needed. It requires exactly one existing ext4 partition and never partitions or formats disks. Other layouts and disks in use elsewhere are refused. The mount defaults to the installing user's `~/Storage`; `SSD_MOUNT_DIR` overrides it. Existing file ownership is preserved, and the filesystem UUID is saved in `/etc/fstab` for automatic mounting. The underlying directory blocks ordinary user writes while the SSD is absent. Leave `SSD_DISK_ID` empty on machines without a data SSD.

For a descriptive mount name, set `SSD_MOUNT_DIR="$HOME/9100-pro-4tb"` in `setup/.env`. To rename an existing mount, first unmount it and update its existing UUID entry in `/etc/fstab` to the new path, then run the storage component. Changing `.env` alone does not move an active mount. Update any applications using the old path.

To configure only storage, without rerunning the other installer steps:

```bash
bash setup/install-components/configure-storage.sh
```

Initialize a new blank SSD separately, once. After reinstalling Linux, restore the disk ID in `.env` and run the same component to reconnect the existing ext4 filesystem. If your numeric user ID changed, inspect file ownership separately.

Both `install.sh` and the tmux install component refresh the managed `~/.tmux.conf` from `global-config/global-tmux.conf`, replacing local edits. It sets `tmux-256color` and clears inherited `NO_COLOR` for new panes. Existing servers load it with `tmux source-file ~/.tmux.conf`; running applications need a restart from a shell with `NO_COLOR` unset.

Run `bash scripts/reboot-tmux.sh` from the repo root in a terminal outside tmux to destroy all default-server sessions and panes, then leave an empty server running with the repo's shared config. Other named tmux servers are untouched.

## SSH access to the server

Run these once per laptop you want to let in. The keypair is generated on the server at run time; no key material is ever stored in this repo.

1. On the **server**: `bash setup/grant-ssh-access.sh` — generates an ed25519 keypair, appends the public key to `authorized_keys`, and prints a base64 bundle (also copied to your clipboard).
2. On the **laptop**: `bash setup/accept-ssh-access.sh` — paste the bundle. It installs the private key and adds a `~/.ssh/config` entry, so you can then just `ssh <alias>`.

To revoke a laptop, delete its line from the server's `~/.ssh/authorized_keys` — each is labelled with the name you chose in step 1.
