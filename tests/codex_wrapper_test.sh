#!/usr/bin/env bash
# Unit tests for launch-time Codex updates. npm and node are isolated stubs;
# no package, network, or user installation is touched.
set -u

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_ROOT="$(mktemp -d)"
ROUTE_PATH=""
SOCKET_SERVER_PID=""
cleanup() {
    [ -z "$SOCKET_SERVER_PID" ] || kill "$SOCKET_SERVER_PID" 2>/dev/null || true
    [ -z "$SOCKET_SERVER_PID" ] || wait "$SOCKET_SERVER_PID" 2>/dev/null || true
    [ -z "$ROUTE_PATH" ] || rm -f "$ROUTE_PATH"
    rm -rf "$TEST_ROOT"
}
trap cleanup EXIT

TEST_BIN="$TEST_ROOT/bin"
TEST_PREFIX="$TEST_ROOT/prefix"
TEST_NPM_ROOT="$TEST_PREFIX/lib/node_modules"
TEST_CODEX_HOME="$TEST_ROOT/codex-home"
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
printf 'hook_file=%s\n' "${OCTO_HOOK_FILE:-}" >> "$CALLS"
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
    if [ "${1:-}" = --no-args ]; then
        codex_args=()
    elif [ "$#" -ne 0 ]; then
        codex_args=("$@")
    fi
    output="$(
        HOME="$TEST_ROOT/home" PATH="$TEST_BIN:$PATH" \
            CODEX_NPM_PREFIX="$TEST_PREFIX" TEST_NPM_ROOT="$TEST_NPM_ROOT" \
            CODEX_JS="$CODEX_JS" CALLS="$CALLS" VERSION_FILE="$VERSION_FILE" \
            LATEST_VERSION="${LATEST_VERSION:-0.144.3}" \
            FAIL_CHECK="${FAIL_CHECK:-0}" FAIL_INSTALL="${FAIL_INSTALL:-0}" \
            LAUNCH_RC="${LAUNCH_RC:-0}" OCTO_HOOK_FILE="${OCTO_HOOK_FILE:-}" \
            CODEX_HOME="${WRAPPER_CODEX_HOME:-$TEST_CODEX_HOME}" \
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

# Remote-server launches get a stable default hook file while preserving an
# OctoCode-provided per-agent path.
: > "$CALLS"
remote_server="$(run_wrapper app-server)"
check "remote server -> exits 0" "rc=0" "$(tail -n1 <<<"$remote_server")"
check "remote server -> default hook file" "/tmp/octo-hook-octo-code-default.jsonl" \
    "$(sed -n 's/^hook_file=//p' "$CALLS" | sort -u)"
: > "$CALLS"
OCTO_HOOK_FILE=/tmp/custom-octo-hook.jsonl
remote_server="$(run_wrapper app-server)"
unset OCTO_HOOK_FILE
check "remote server -> preserves hook file" "/tmp/custom-octo-hook.jsonl" \
    "$(sed -n 's/^hook_file=//p' "$CALLS" | sort -u)"

# An OctoCode TUI joins the shared App Server at its pane's project directory.
mkdir -p "$TEST_CODEX_HOME/app-server-control"
python3 -c '
import socket, sys, time
server = socket.socket(socket.AF_UNIX)
server.bind(sys.argv[1])
server.listen()
time.sleep(30)
' "$TEST_CODEX_HOME/app-server-control/app-server-control.sock" &
SOCKET_SERVER_PID=$!
for _attempt in $(seq 1 100); do
    [ -S "$TEST_CODEX_HOME/app-server-control/app-server-control.sock" ] && break
    sleep 0.01
done
test -S "$TEST_CODEX_HOME/app-server-control/app-server-control.sock"
: > "$CALLS"
OCTO_HOOK_FILE="/tmp/octo-hook-wrapper-test-$$.jsonl"
route_key="$(printf '%s' "$OCTO_HOOK_FILE" | tr -c 'A-Za-z0-9._-' '_')"
ROUTE_PATH="/tmp/octocode-app-server-cwd/$route_key-3"
export OCTO_AGENT_ID=3
octo_tui="$(run_wrapper --no-args)"
unset OCTO_AGENT_ID
check "OctoCode TUI -> exits 0" "rc=0" "$(tail -n1 <<<"$octo_tui")"
check "OctoCode TUI -> shared app server" "1" \
    "$(grep -c -- "--remote unix:// --cd $ROUTE_PATH" "$CALLS")"
check "OctoCode TUI -> routing cwd targets project" "$REPO_DIR" "$(readlink "$ROUTE_PATH")"
unset OCTO_HOOK_FILE

# Explicit remote endpoints and non-TUI commands are never rewritten.
: > "$CALLS"
export OCTO_AGENT_ID=3
explicit_remote="$(run_wrapper --remote ws://example.test)"
unset OCTO_AGENT_ID
check "explicit remote -> preserved" "1" \
    "$(grep -c -- '--dangerously-bypass-hook-trust --remote ws://example.test' "$CALLS")"
: > "$CALLS"
export OCTO_AGENT_ID=3
app_server="$(run_wrapper app-server proxy)"
unset OCTO_AGENT_ID
check "OctoCode subcommand -> no remote TUI args" "0" \
    "$(grep -c -- '--remote unix://' "$CALLS")"
: > "$CALLS"
export OCTO_AGENT_ID=3
global_flags_exec="$(run_wrapper -c model=custom exec sample)"
unset OCTO_AGENT_ID
check "global flags + subcommand -> no remote TUI args" "0" \
    "$(grep -c -- '--remote unix://' "$CALLS")"

# If bootstrap is unavailable, the pane still starts with ordinary local Codex.
: > "$CALLS"
export OCTO_AGENT_ID=3
WRAPPER_CODEX_HOME="$TEST_ROOT/missing-codex-home"
missing_socket="$(run_wrapper --no-args)"
unset WRAPPER_CODEX_HOME OCTO_AGENT_ID
check "missing app server -> local fallback" "0" \
    "$(grep -c -- '--remote unix://' "$CALLS")"
check "missing app server -> warning" "1" \
    "$(grep -c 'App Server socket is unavailable' <<<"$missing_socket")"

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
