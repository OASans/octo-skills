#!/usr/bin/env bash
# Unit tests for configure-swap.sh. System commands are stubbed; no real swap,
# sudo, or /etc/fstab changes are made. Run: bash configure-swap.test.sh
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=configure-swap.sh
source "$SCRIPT_DIR/configure-swap.sh"

tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
calls="$tmp/calls"
fstab_input="$tmp/fstab-input"

fail=0
pass=0
check() { # description expected actual
  if [[ "$2" == "$3" ]]; then
    pass=$((pass + 1))
  else
    fail=$((fail + 1))
    echo "FAIL: $1 — expected '$2', got '$3'"
  fi
}

reset_stubs() {
  : > "$calls"
  : > "$fstab_input"
  SWAP_TARGET_GIB=32
  SWAP_FILE="$tmp/swap-octo.img"
  rm -f "$SWAP_FILE"
  FSTAB_FILE=/etc/fstab
  CURRENT_SWAP_BYTES=0
  SWAP_FILE_IS_ACTIVE=0
  FSTAB_HAS_SWAP_FILE=0
}

current_swap_bytes() { echo "$CURRENT_SWAP_BYTES"; }
swap_file_active() { [[ "$SWAP_FILE_IS_ACTIVE" -eq 1 ]]; }
fstab_has_swap_file() { [[ "$FSTAB_HAS_SWAP_FILE" -eq 1 ]]; }
run_as_root() {
  printf '%s\n' "$*" >> "$calls"
  if [[ "$1" == tee ]]; then
    cat >> "$fstab_input"
  fi
}

# Existing capacity is left untouched.
reset_stubs
CURRENT_SWAP_BYTES=$((32 * 1024 * 1024 * 1024))
configure_swap >/dev/null
check "sufficient swap -> no root commands" "0" "$(wc -l < "$calls")"

# An 8 GiB host gets only the missing 24 GiB, then activates and persists it.
reset_stubs
CURRENT_SWAP_BYTES=$((8 * 1024 * 1024 * 1024))
configure_swap >/dev/null
check "8 GiB -> allocate missing capacity" \
  "fallocate -l 24576M $SWAP_FILE" "$(sed -n '1p' "$calls")"
check "new swap -> secure permissions" \
  "chmod 600 $SWAP_FILE" "$(sed -n '2p' "$calls")"
check "new swap -> format" "mkswap $SWAP_FILE" "$(sed -n '3p' "$calls")"
check "new swap -> activate" "swapon $SWAP_FILE" "$(sed -n '4p' "$calls")"
check "new swap -> persist" \
  "tee -a /etc/fstab" "$(sed -n '5p' "$calls")"
check "fstab entry" "$SWAP_FILE none swap sw 0 0" "$(cat "$fstab_input")"

# A leftover inactive file is reset before allocation.
reset_stubs
touch "$SWAP_FILE"
configure_swap >/dev/null
check "inactive file -> truncate first" \
  "truncate -s 0 $SWAP_FILE" "$(sed -n '1p' "$calls")"
check "inactive file -> allocate second" \
  "fallocate -l 32768M $SWAP_FILE" "$(sed -n '2p' "$calls")"

# An interrupted run with active swap repairs fstab without reallocating.
reset_stubs
CURRENT_SWAP_BYTES=$((32 * 1024 * 1024 * 1024))
SWAP_FILE_IS_ACTIVE=1
configure_swap >/dev/null
check "active managed swap -> only persist" \
  "tee -a /etc/fstab" "$(cat "$calls")"

# Invalid configuration fails before touching the system.
reset_stubs
SWAP_TARGET_GIB=invalid
if configure_swap >/dev/null 2>&1; then invalid_rc=0; else invalid_rc=$?; fi
check "invalid target -> fail" "1" "$invalid_rc"
check "invalid target -> no root commands" "0" "$(wc -l < "$calls")"

echo "----"
echo "passed: $pass, failed: $fail"
[[ "$fail" -eq 0 ]]
