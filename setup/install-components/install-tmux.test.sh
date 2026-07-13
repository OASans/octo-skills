#!/usr/bin/env bash
# Unit tests for install-components/install-tmux.sh version logic.
# Pure in-process tests: `tmux` is stubbed as a shell function, so no real tmux,
# apt, or shell/network dependency is touched. Run: bash install-tmux.test.sh
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Sourcing loads the helpers only (the script guards its install dispatch on
# being run directly), so parse_tmux_version / tmux_ge / tmux_at_build_target
# become callable here.
# shellcheck source=/dev/null
source "$SCRIPT_DIR/install-tmux.sh"

fail=0
pass=0
check() { # description  expected  actual
  if [[ "$2" == "$3" ]]; then
    pass=$((pass + 1))
  else
    fail=$((fail + 1))
    echo "FAIL: $1 — expected '$2', got '$3'"
  fi
}

# --- parse_tmux_version: real-world and adverse inputs ---
check "parse 3.6a"        "3 6" "$(parse_tmux_version 'tmux 3.6a')"
check "parse next-3.7"    "3 7" "$(parse_tmux_version 'tmux next-3.7')"
check "parse openbsd-7.4" "7 4" "$(parse_tmux_version 'openbsd-7.4')"
check "parse bare 3.7"    "3 7" "$(parse_tmux_version '3.7')"
check "parse leading-0"   "3 08" "$(parse_tmux_version '3.08')"   # kept; 10# handles it
check "parse no-dot"      ""    "$(parse_tmux_version '4')"       # unparseable -> empty
check "parse empty-minor" ""    "$(parse_tmux_version '3.')"      # unparseable -> empty
check "parse garbage"     ""    "$(parse_tmux_version 'tmux garbage')"

# --- tmux_at_build_target: the gate fix. Stub `tmux` to a chosen version,
#     then assert whether the build target (currently 3.7) is considered met.
#     "met" (rc 0) => skip source build; "not met" (rc 1) => rebuild.
gate() { # installed_version -> prints met|rebuild
  eval "tmux() { echo 'tmux $1'; }"
  if tmux_at_build_target; then echo met; else echo rebuild; fi
  unset -f tmux
}

# The regression: apt's 3.6 used to pass the old min-3.6 gate and never upgrade.
check "3.6 triggers rebuild"  "rebuild" "$(gate 3.6)"
check "3.6a triggers rebuild" "rebuild" "$(gate 3.6a)"
check "3.7 is met"            "met"     "$(gate 3.7)"
check "3.7a is met"           "met"     "$(gate 3.7a)"
check "next-3.8 is met"       "met"     "$(gate next-3.8)"
check "4.0 is met"            "met"     "$(gate 4.0)"

# --- tmux_ge base-10 guard: a leading-zero minor must not be read as octal ---
check_ge() { # want_major want_minor installed -> rc
  eval "tmux() { echo 'tmux $3'; }"
  tmux_ge "$1" "$2" && echo ge || echo lt
  unset -f tmux
}
check "3.10 >= 3.9 (not octal)" "ge" "$(check_ge 3 9 3.10)"

# --- unparseable installed version is treated as acceptable (not locked out) ---
check "unparseable installed -> met" "met" "$(gate 'garbage')"

echo "----"
echo "passed: $pass, failed: $fail"
[[ "$fail" -eq 0 ]]
