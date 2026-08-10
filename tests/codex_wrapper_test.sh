#!/usr/bin/env bash
# Unit tests for launch-time Codex updates. npm and node are isolated stubs;
# no package, network, or user installation is touched.
set -u

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_ROOT="$(mktemp -d)"
trap 'rm -rf "$TEST_ROOT"' EXIT

TEST_BIN="$TEST_ROOT/bin"
TEST_PREFIX="$TEST_ROOT/prefix"
TEST_NPM_ROOT="$TEST_PREFIX/lib/node_modules"
CODEX_JS="$TEST_NPM_ROOT/@openai/codex/bin/codex.js"
CALLS="$TEST_ROOT/calls"
VERSION_FILE="$TEST_ROOT/version"
mkdir -p "$TEST_BIN" "$(dirname "$CODEX_JS")"
: > "$CODEX_JS"

cat > "$TEST_BIN/npm" <<'EOF'
#!/usr/bin/env bash
printf 'npm %s\n' "$*" >> "$CALLS"
case "${1:-}" in
    root)
        printf '%s\n' "$TEST_NPM_ROOT"
        ;;
    view)
        if [ "${FAIL_CHECK:-0}" -eq 1 ]; then
            echo "registry unavailable" >&2
            exit 1
        fi
        printf '%s\n' "$LATEST_VERSION"
        ;;
    install)
        if [ "${FAIL_INSTALL:-0}" -eq 1 ]; then
            echo "install denied" >&2
            exit 1
        fi
        mkdir -p "$(dirname "$CODEX_JS")"
        : > "$CODEX_JS"
        printf '%s\n' "$LATEST_VERSION" > "$VERSION_FILE"
        ;;
esac
EOF

cat > "$TEST_BIN/node" <<'EOF'
#!/usr/bin/env bash
printf 'node %s prefix=%s\n' "$*" "${NPM_CONFIG_PREFIX:-}" >> "$CALLS"
if [ "${2:-}" = --version ]; then
    printf 'codex-cli %s\n' "$(cat "$VERSION_FILE")"
    exit 0
fi
exit "${LAUNCH_RC:-0}"
EOF
chmod +x "$TEST_BIN/npm" "$TEST_BIN/node"

fail=0
pass=0
check() { # description expected actual
    if [ "$2" = "$3" ]; then
        pass=$((pass + 1))
    else
        fail=$((fail + 1))
        echo "FAIL: $1 — expected '$2', got '$3'"
    fi
}

run_wrapper() {
    local output rc
    local -a codex_args=(exec sample)
    [ "$#" -eq 0 ] || codex_args=("$@")
    output="$(
        HOME="$TEST_ROOT/home" PATH="$TEST_BIN:$PATH" \
            CODEX_NPM_PREFIX="$TEST_PREFIX" TEST_NPM_ROOT="$TEST_NPM_ROOT" \
            CODEX_JS="$CODEX_JS" CALLS="$CALLS" VERSION_FILE="$VERSION_FILE" \
            LATEST_VERSION="${LATEST_VERSION:-0.144.3}" \
            FAIL_CHECK="${FAIL_CHECK:-0}" FAIL_INSTALL="${FAIL_INSTALL:-0}" \
            LAUNCH_RC="${LAUNCH_RC:-0}" \
            bash "$REPO_DIR/global-codex-wrapper.sh" "${codex_args[@]}" 2>&1
    )"
    rc=$?
    printf '%s\nrc=%s\n' "$output" "$rc"
}

# An older install is upgraded before the requested Codex command starts.
printf '0.144.1\n' > "$VERSION_FILE"
: > "$CALLS"
LATEST_VERSION=0.144.3
updated="$(run_wrapper)"
check "update -> exit 0" "rc=0" "$(tail -n1 <<<"$updated")"
check "update -> version advanced" "0.144.3" "$(cat "$VERSION_FILE")"
check "update -> install once" "1" "$(grep -c '^npm install ' "$CALLS")"
check "update -> reports versions" "1" "$(grep -c 'Updated Codex: 0.144.1 -> 0.144.3' <<<"$updated")"
check "launch -> trust bypass precedes subcommand" "1" \
    "$(grep -c 'node .* --dangerously-bypass-hook-trust exec sample ' "$CALLS")"
check "launch -> trust bypass once" "1" \
    "$(grep -c -- '--dangerously-bypass-hook-trust' "$CALLS")"

# The special update path also bypasses hook trust and retains its npm prefix.
: > "$CALLS"
update_command="$(run_wrapper update)"
check "update command -> exits 0" "rc=0" "$(tail -n1 <<<"$update_command")"
check "update command -> trust bypass precedes subcommand" "1" \
    "$(grep -c 'node .* --dangerously-bypass-hook-trust update prefix=' "$CALLS")"
check "update command -> npm prefix" "$TEST_PREFIX" \
    "$(sed -n 's/.* --dangerously-bypass-hook-trust update prefix=//p' "$CALLS")"

# A current install only checks the registry; it does not reinstall.
: > "$CALLS"
current="$(run_wrapper)"
check "current -> exit 0" "rc=0" "$(tail -n1 <<<"$current")"
check "current -> no install" "0" "$(grep -c '^npm install ' "$CALLS")"

# Registry and install failures warn but preserve access to the installed CLI.
: > "$CALLS"
FAIL_CHECK=1
check_failed="$(run_wrapper)"
FAIL_CHECK=0
check "check failure -> launches" "rc=0" "$(tail -n1 <<<"$check_failed")"
check "check failure -> warning" "1" \
    "$(grep -c 'WARNING: Codex update check failed' <<<"$check_failed")"

printf '0.144.1\n' > "$VERSION_FILE"
: > "$CALLS"
FAIL_INSTALL=1
install_failed="$(run_wrapper)"
FAIL_INSTALL=0
check "install failure -> launches" "rc=0" "$(tail -n1 <<<"$install_failed")"
check "install failure -> warning" "1" \
    "$(grep -c 'WARNING: Codex update failed' <<<"$install_failed")"

# A killed updater's lock is removed instead of delaying every future launch.
printf '0.144.1\n' > "$VERSION_FILE"
mkdir -p "$TEST_PREFIX/.update-lock"
printf '99999999\n' > "$TEST_PREFIX/.update-lock/pid"
: > "$CALLS"
recovered="$(run_wrapper)"
check "stale lock -> launches" "rc=0" "$(tail -n1 <<<"$recovered")"
check "stale lock -> updates" "0.144.3" "$(cat "$VERSION_FILE")"
check "stale lock -> removed" "0" "$([ ! -d "$TEST_PREFIX/.update-lock" ]; echo $?)"

# Without any installed package, a failed first update gives an actionable error.
rm -f "$CODEX_JS"
: > "$CALLS"
FAIL_INSTALL=1
missing="$(run_wrapper)"
FAIL_INSTALL=0
check "missing install -> exit 1" "rc=1" "$(tail -n1 <<<"$missing")"
check "missing install -> action" "1" \
    "$(grep -c 'run octo-skills/install.sh' <<<"$missing")"

echo "----"
echo "passed: $pass, failed: $fail"
[ "$fail" -eq 0 ]
