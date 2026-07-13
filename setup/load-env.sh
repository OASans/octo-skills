#!/usr/bin/env bash
# Sourced by the install scripts to load setup/.env — the machine-specific values
# (git identity, LAN topology) that must never be committed. .env is gitignored;
# .env.example is the committed template.
#
# It's bash, not generic dotenv: WEB_ALLOWED_IPS is a real bash array, so .env is
# `source`d rather than parsed. Defaults are set here first, so .env only has to
# override what it cares about, and an omitted array stays safe under `set -u`.
#
# Usage:
#   source "$SCRIPT_DIR/load-env.sh"          # loads .env, requires the git identity
#   require_env INTERNAL_SSH_CIDR             # additional vars the caller depends on

# ---------- defaults (a .env value overrides any of these) ----------
GIT_USER_NAME=""
GIT_USER_EMAIL=""
INTERNAL_SSH_CIDR=""
SSH_PORT=22
WEB_PORT=""
WEB_ALLOWED_IPS=()

OCTO_ENV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OCTO_ENV_FILE="$OCTO_ENV_DIR/.env"

if [ ! -f "$OCTO_ENV_FILE" ]; then
  echo "ERROR: $OCTO_ENV_FILE not found — the install scripts read your settings from it." >&2
  echo "  Create it:  cp $OCTO_ENV_DIR/.env.example $OCTO_ENV_FILE" >&2
  echo "  Then fill it in and re-run this script." >&2
  exit 1
fi

# shellcheck source=/dev/null
. "$OCTO_ENV_FILE"

# Fail with the full list of what's missing, not just the first one.
require_env() {
  local var missing=()
  for var in "$@"; do
    [ -n "${!var:-}" ] || missing+=("$var")
  done
  if [ "${#missing[@]}" -gt 0 ]; then
    echo "ERROR: $OCTO_ENV_FILE is missing required value(s): ${missing[*]}" >&2
    echo "  See $OCTO_ENV_DIR/.env.example for what each one means." >&2
    exit 1
  fi
}

# Every install script sets git globals, so the identity is always required.
require_env GIT_USER_NAME GIT_USER_EMAIL
