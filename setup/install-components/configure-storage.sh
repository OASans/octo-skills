#!/usr/bin/env bash
# Attach the existing Linux data SSD selected in setup/.env. Never format disks.
set -euo pipefail
export LC_ALL=C
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
. "$SCRIPT_DIR/../load-env.sh"

die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }
(($# == 0)) || die 'This component takes no flags; configure SSD_DISK_ID in setup/.env.'
if [[ -z $SSD_DISK_ID ]]; then
  echo 'Storage: no SSD_DISK_ID configured — skipping.'
  exit 0
fi
owner=${SUDO_USER:-$(id -un)}
uid=$(id -u "$owner")
[[ $uid != 0 ]] || die 'Run as your normal user, or with sudo from that account.'
root=(sudo)
[[ $EUID != 0 ]] || root=()
for command in lsblk readlink findmnt mountpoint find blkid; do
  command -v "$command" >/dev/null || die "Missing command: $command"
done
[[ $SSD_DISK_ID == /dev/disk/by-id/* && -L $SSD_DISK_ID ]] || die 'SSD_DISK_ID must be an existing /dev/disk/by-id/ whole-disk symlink.'
disk=$(readlink -f -- "$SSD_DISK_ID")
[[ -b $disk && $(lsblk -dnro TYPE "$disk") == disk ]] || die 'SSD_DISK_ID must identify a whole disk.'
home_dir=$(getent passwd "$owner" | cut -d: -f6)
mount_dir=${SSD_MOUNT_DIR:-$home_dir/Storage}
[[ $mount_dir == /* && $mount_dir != / && ! $mount_dir =~ [[:space:]\\#] ]] || die 'Mount path must be absolute, without spaces, backslashes, or #.'
[[ $(readlink -m -- "$mount_dir") == "$mount_dir" ]] || die 'Use a canonical mount path without symlinks or trailing slash.'
mount_parent=$(dirname -- "$mount_dir")
[[ -d $mount_parent ]] || die 'Mount directory parent does not exist.'
[[ ! -e $mount_dir || -d $mount_dir ]] || die 'Mount path exists and is not a directory.'

mapfile -t devices < <(lsblk -nrpo NAME "$disk")
mapfile -t partitions < <(lsblk -nrpo NAME,TYPE "$disk" | awk '$2 == "part" {print $1}')
((${#partitions[@]} == 1 && ${#devices[@]} == 2)) || die 'Expected exactly one existing ext4 partition. Initialize blank disks separately; this script never formats.'
partition=${partitions[0]}
[[ $(lsblk -dnro FSTYPE "$partition") == ext4 ]] || die 'Existing partition is not ext4; refusing to change it.'
for device in "${devices[@]}"; do
  holders=$(find "/sys/class/block/${device##*/}/holders" -mindepth 1 -maxdepth 1 -print -quit)
  [[ -z $holders ]] || die "$device has active holders."
  while IFS= read -r target; do
    [[ -z $target || $target == "$mount_dir" ]] || die "$device is in use at $target."
  done < <(lsblk -nro MOUNTPOINTS "$device")
done
uuid=$("${root[@]}" blkid -s UUID -o value "$partition")
[[ -n $uuid ]] || die 'Existing ext4 partition has no readable UUID.'
entries=$(awk -v target="$mount_dir" '$1 !~ /^#/ && $2 == target { print $1 " " $3 }' /etc/fstab)
[[ -z $entries || ( -n $uuid && $entries == "UUID=$uuid ext4" ) ]] || die 'Mount path has a conflicting /etc/fstab entry.'
mounted=false
if mountpoint -q -- "$mount_dir"; then
  [[ $(findmnt -nro MAJ:MIN --mountpoint "$mount_dir") == "$(lsblk -dnro MAJ:MIN "$partition")" ]] || die 'A different device is mounted at the target.'
  mounted=true
elif [[ -d $mount_dir ]]; then
  contents=$("${root[@]}" find "$mount_dir" -mindepth 1 -maxdepth 1 -print -quit)
  [[ -z $contents ]] || die 'Unmounted mount directory must be empty.'
fi

lsblk -d -o NAME,SIZE,MODEL,SERIAL "$disk"
echo "Storage: $SSD_DISK_ID -> $mount_dir"
if [[ -z $entries ]]; then
  backup=$("${root[@]}" mktemp /etc/fstab.before-ssd.XXXXXXXX)
  "${root[@]}" cp --preserve=mode,ownership,timestamps /etc/fstab "$backup"
  echo "fstab backup: $backup"
fi
if $mounted; then
  # A non-recursive parent bind exposes the directory beneath the live SSD mount.
  underlay=$(mktemp -d "$SCRIPT_DIR/.ssd-underlay.XXXXXXXX")
  cleanup_underlay() {
    if mountpoint -q -- "$underlay"; then
      "${root[@]}" umount -- "$underlay" || return 1
    fi
    rmdir -- "$underlay"
  }
  trap cleanup_underlay EXIT
  "${root[@]}" mount --bind "$mount_parent" "$underlay"
  "${root[@]}" chown root:root "$underlay/${mount_dir##*/}"
  "${root[@]}" chmod 000 "$underlay/${mount_dir##*/}"
  cleanup_underlay
  trap - EXIT
else
  "${root[@]}" mkdir -p -- "$mount_dir"
  # Prevent ordinary writes to the system disk when the SSD is disconnected.
  "${root[@]}" chown root:root "$mount_dir"
  "${root[@]}" chmod 000 "$mount_dir"
  "${root[@]}" mount -t ext4 "$partition" "$mount_dir"
fi
if [[ -z $entries ]]; then
  printf '\nUUID=%s %s ext4 defaults,nofail 0 2\n' "$uuid" "$mount_dir" \
    | "${root[@]}" tee -a /etc/fstab >/dev/null
  "${root[@]}" systemctl daemon-reload
fi
findmnt --mountpoint "$mount_dir"
echo "Storage ready: $mount_dir"
