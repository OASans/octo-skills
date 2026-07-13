#!/usr/bin/env bash
# Ensure a Linux host has enough persistent swap for short memory spikes.
# Meant to be called by install-linux.sh. Safe to source for unit tests.
set -u

SWAP_TARGET_GIB="${SWAP_TARGET_GIB:-32}"
SWAP_FILE="${SWAP_FILE:-/swap-octo.img}"
PROC_SWAPS_FILE="${PROC_SWAPS_FILE:-/proc/swaps}"
FSTAB_FILE="${FSTAB_FILE:-/etc/fstab}"
BYTES_PER_MIB=$((1024 * 1024))

run_as_root() {
  sudo "$@"
}

current_swap_bytes() {
  awk 'NR > 1 { total += $3 * 1024 } END { printf "%.0f\n", total + 0 }' "$PROC_SWAPS_FILE"
}

swap_file_active() {
  awk -v file="$SWAP_FILE" 'NR > 1 && $1 == file { found = 1 } END { exit !found }' "$PROC_SWAPS_FILE"
}

fstab_has_swap_file() {
  awk -v file="$SWAP_FILE" '
    $0 !~ /^[[:space:]]*#/ && $1 == file && $3 == "swap" { found = 1 }
    END { exit !found }
  ' "$FSTAB_FILE"
}

persist_swap_file() {
  fstab_has_swap_file && return 0
  printf '%s none swap sw 0 0\n' "$SWAP_FILE" \
    | run_as_root tee -a "$FSTAB_FILE" >/dev/null
  echo "Added $SWAP_FILE to $FSTAB_FILE."
}

configure_swap() {
  case "$SWAP_TARGET_GIB" in
    ''|*[!0-9]*)
      echo "ERROR: SWAP_TARGET_GIB must be a positive integer; got '$SWAP_TARGET_GIB'." >&2
      return 1
      ;;
  esac
  if [ "$SWAP_TARGET_GIB" -eq 0 ]; then
    echo "ERROR: SWAP_TARGET_GIB must be greater than zero." >&2
    return 1
  fi

  local target_bytes current_bytes missing_bytes missing_mib
  target_bytes=$((SWAP_TARGET_GIB * 1024 * 1024 * 1024))
  current_bytes="$(current_swap_bytes)"

  # Repair persistence after an interrupted earlier run before checking capacity.
  if swap_file_active; then
    persist_swap_file || {
      echo "ERROR: couldn't persist $SWAP_FILE in $FSTAB_FILE." >&2
      return 1
    }
  fi

  if [ "$current_bytes" -ge "$target_bytes" ]; then
    echo "Swap: at least ${SWAP_TARGET_GIB} GiB already active — skipping"
    return 0
  fi
  if swap_file_active; then
    echo "ERROR: $SWAP_FILE is active, but total swap is below ${SWAP_TARGET_GIB} GiB." >&2
    echo "  Increase SWAP_TARGET_GIB only after resizing or removing the managed swapfile." >&2
    return 1
  fi

  missing_bytes=$((target_bytes - current_bytes))
  missing_mib=$(((missing_bytes + BYTES_PER_MIB - 1) / BYTES_PER_MIB))
  echo "Swap: creating $SWAP_FILE (${missing_mib} MiB) to reach ${SWAP_TARGET_GIB} GiB total."

  if [ -e "$SWAP_FILE" ]; then
    run_as_root truncate -s 0 "$SWAP_FILE" || {
      echo "ERROR: couldn't reset inactive swapfile $SWAP_FILE." >&2
      return 1
    }
  fi
  run_as_root fallocate -l "${missing_mib}M" "$SWAP_FILE" || {
    echo "ERROR: couldn't allocate $SWAP_FILE; check free disk space and filesystem support." >&2
    return 1
  }
  run_as_root chmod 600 "$SWAP_FILE" || return 1
  run_as_root mkswap "$SWAP_FILE" >/dev/null || {
    echo "ERROR: couldn't format $SWAP_FILE as swap." >&2
    return 1
  }
  run_as_root swapon "$SWAP_FILE" || {
    echo "ERROR: couldn't activate $SWAP_FILE." >&2
    return 1
  }
  persist_swap_file || {
    echo "ERROR: swap is active, but couldn't persist it in $FSTAB_FILE." >&2
    return 1
  }
  echo "Swap: ${SWAP_TARGET_GIB} GiB emergency capacity is now available."
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
  configure_swap
fi
