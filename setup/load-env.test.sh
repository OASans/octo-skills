#!/usr/bin/env bash
# Unit tests for load-env.sh.
# load-env.sh resolves .env relative to its OWN location, so each case copies it
# into a tempdir next to a fixture .env and runs a probe script there. No real
# .env, no network, no system state — tempdirs only, cleaned up on exit.
# Run: bash load-env.test.sh
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

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

# Run a probe against a fixture .env. Args: <env-content|__NONE__> <probe-body>
# Prints the probe's stdout+stderr, then "rc=<exit code>" on the last line.
run_case() {
  local env_content="$1" probe="$2" dir out rc
  dir="$(mktemp -d)"
  cp "$SCRIPT_DIR/load-env.sh" "$dir/load-env.sh"
  [[ "$env_content" == "__NONE__" ]] || printf '%s\n' "$env_content" > "$dir/.env"
  {
    echo 'set -u'
    echo 'SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"'
    echo '. "$SCRIPT_DIR/load-env.sh"'
    printf '%s\n' "$probe"
  } > "$dir/probe.sh"
  out="$(bash "$dir/probe.sh" 2>&1)"; rc=$?
  rm -rf "$dir"
  printf '%s\nrc=%s\n' "$out" "$rc"
}

VALID_ENV='GIT_USER_NAME="Test User"
GIT_USER_EMAIL="test@example.com"'

# --- missing .env: refuse to run, and say how to fix it ---
missing="$(run_case __NONE__ 'echo REACHED')"
check "no .env -> exit 1"           "rc=1" "$(tail -n1 <<<"$missing")"
check "no .env -> body not run"     "0"    "$(grep -c REACHED <<<"$missing")"
check "no .env -> tells you to cp"  "1"    "$(grep -c 'cp .*\.env\.example' <<<"$missing")"

# --- valid .env: identity loads ---
ok="$(run_case "$VALID_ENV" 'echo "name=$GIT_USER_NAME email=$GIT_USER_EMAIL"')"
check "valid .env -> exit 0"    "rc=0"                                   "$(tail -n1 <<<"$ok")"
check "valid .env -> identity"  "name=Test User email=test@example.com"  "$(grep '^name=' <<<"$ok")"

# --- the guard that keeps personal data out of the repo: identity is mandatory ---
no_email="$(run_case 'GIT_USER_NAME="Test User"' 'echo REACHED')"
check "missing email -> exit 1"      "rc=1" "$(tail -n1 <<<"$no_email")"
check "missing email -> named"       "1"    "$(grep -c 'GIT_USER_EMAIL' <<<"$no_email")"

# require_env reports EVERY missing var in one pass, not just the first.
none="$(run_case '# empty' 'echo REACHED')"
check "empty .env -> both named" "1" "$(grep -c 'GIT_USER_NAME GIT_USER_EMAIL' <<<"$none")"

# A caller's extra requirement (install-linux.sh needs the CIDR) is enforced too.
no_cidr="$(run_case "$VALID_ENV" 'require_env INTERNAL_SSH_CIDR; echo REACHED')"
check "missing CIDR -> exit 1"  "rc=1" "$(tail -n1 <<<"$no_cidr")"
check "missing CIDR -> named"   "1"    "$(grep -c 'INTERNAL_SSH_CIDR' <<<"$no_cidr")"

# --- defaults: an omitted optional var must not blow up under `set -u` ---
# WEB_ALLOWED_IPS is the sharp edge — install-linux.sh reads ${#WEB_ALLOWED_IPS[@]},
# which would be an unbound-variable error if load-env.sh didn't pre-declare it.
defaults="$(run_case "$VALID_ENV" 'echo "port=$SSH_PORT web=[$WEB_PORT] n=${#WEB_ALLOWED_IPS[@]}"')"
check "defaults -> exit 0"      "rc=0"                  "$(tail -n1 <<<"$defaults")"
check "defaults applied"        "port=22 web=[] n=0"    "$(grep '^port=' <<<"$defaults")"

# --- .env overrides the defaults, arrays included ---
OVERRIDE_ENV="$VALID_ENV"'
SSH_PORT=2222
WEB_PORT="8080"
WEB_ALLOWED_IPS=(
  "192.0.2.10 laptop-a"
  "192.0.2.11 laptop-b"
)'
over="$(run_case "$OVERRIDE_ENV" 'echo "port=$SSH_PORT n=${#WEB_ALLOWED_IPS[@]} first=${WEB_ALLOWED_IPS[0]}"')"
check "override -> exit 0"  "rc=0"                                    "$(tail -n1 <<<"$over")"
check "override applied"    "port=2222 n=2 first=192.0.2.10 laptop-a" "$(grep '^port=' <<<"$over")"

echo "----"
echo "passed: $pass, failed: $fail"
[[ "$fail" -eq 0 ]]
