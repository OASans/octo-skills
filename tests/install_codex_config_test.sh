#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_ROOT="$(mktemp -d "$REPO_DIR/.install-codex-config-test.XXXXXX")"
trap 'rm -rf "$TEST_ROOT"' EXIT

TEST_HOME="$TEST_ROOT/home"
TEST_CODEX="$TEST_ROOT/custom-codex-home"
PLAYWRIGHT_CACHE="$TEST_ROOT/playwright"
TEST_BIN="$TEST_ROOT/bin"
CURL_CALLS="$TEST_ROOT/curl-calls"
CODEX_PROXY_CALLS="$TEST_ROOT/codex-proxy-calls"
CODEX_PROXY_STDIN="$TEST_ROOT/codex-proxy-stdin"
CODEX_DAEMON_CALLS="$TEST_ROOT/codex-daemon-calls"
CODEX_REMOTE_CONTROL_CALLS="$TEST_ROOT/codex-remote-control-calls"
CODEX_BOOTSTRAP_UNMANAGED_MARKER="$TEST_ROOT/codex-bootstrap-unmanaged-marker"
CODEX_UNMANAGED_STOPPED="$TEST_ROOT/codex-unmanaged-stopped"
KILL_CALLS="$TEST_ROOT/kill-calls"
STANDALONE_ENV="$TEST_ROOT/standalone-env"
STANDALONE_INSTALL_DIR="$TEST_ROOT/standalone-install-dir"
APP_SERVER_SOCKET="$TEST_CODEX/app-server-control/app-server-control.sock"
SYSTEMCTL_CALLS="$TEST_ROOT/systemctl-calls"
SYSTEMCTL_DISABLED="$TEST_ROOT/systemctl-disabled"
mkdir -p \
    "$TEST_CODEX" \
    "$(dirname "$APP_SERVER_SOCKET")" \
    "$PLAYWRIGHT_CACHE/chromium-test" \
    "$TEST_BIN"
: > "$APP_SERVER_SOCKET"
for command_name in codex node npm npx; do
    ln -s "$(type -P true)" "$TEST_BIN/$command_name"
done

cat > "$TEST_BIN/curl" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$CURL_CALLS"
if [ "${CURL_SHOULD_STALL:-}" = 1 ]; then
    sleep 4
    exit 1
fi
cat <<'INSTALLER'
#!/bin/sh
set -eu
printf '%s\n' "${CODEX_NON_INTERACTIVE:-}" > "$STANDALONE_ENV"
standalone_bin="${CODEX_HOME:-$HOME/.codex}/packages/standalone/current/bin"
visible_bin="${CODEX_INSTALL_DIR:-$HOME/.local/bin}"
printf '%s\n' "$visible_bin" > "$STANDALONE_INSTALL_DIR"
mkdir -p "$standalone_bin" "$visible_bin"
cat > "$standalone_bin/codex" <<'CODEX'
#!/bin/sh
if [ "${1:-}" = app-server ] && [ "${2:-}" = daemon ]; then
    printf '%s\n' "$*" >> "$CODEX_DAEMON_CALLS"
    if [ "${3:-}" = bootstrap ] &&
        [ "${CODEX_BOOTSTRAP_UNMANAGED_ONCE:-}" = 1 ] &&
        [ ! -e "$CODEX_BOOTSTRAP_UNMANAGED_MARKER" ]; then
        : > "$CODEX_BOOTSTRAP_UNMANAGED_MARKER"
        echo 'app server is running but is not managed by codex app-server daemon' >&2
        exit 1
    fi
    if [ "${3:-}" = restart ] && [ "${CODEX_RESTART_SHOULD_FAIL:-}" = 1 ]; then
        echo 'simulated restart failure' >&2
        exit 1
    fi
fi
if [ "${1:-}" = remote-control ]; then
    printf '%s\n' "$*" >> "$CODEX_REMOTE_CONTROL_CALLS"
    if [ "${2:-}" = stop ] && [ "${CODEX_REMOTE_CONTROL_STOP_UNMANAGED:-}" = 1 ]; then
        echo 'app server is running but is not managed by codex app-server daemon' >&2
        exit 1
    fi
    if [ "${2:-}" = stop ] && [ "${CODEX_REMOTE_CONTROL_STOP_SHOULD_FAIL:-}" = 1 ]; then
        echo 'simulated Remote Control stop failure' >&2
        exit 1
    fi
fi
if [ "${1:-}" = app-server ] && [ "${2:-}" = proxy ]; then
    printf '%s\n' "$*" >> "$CODEX_PROXY_CALLS"
    while IFS= read -r line; do
        printf '%s\n' "$line" >> "$CODEX_PROXY_STDIN"
        case "$line" in
            *'"id":2'*)
                printf '%s\n' '{"id":2,"result":{"status":"ok"}}'
                ;;
        esac
    done
fi
exit 0
CODEX
chmod +x "$standalone_bin/codex"
ln -sf "$standalone_bin/codex" "$visible_bin/codex"
INSTALLER
EOF
chmod +x "$TEST_BIN/curl"

cat > "$TEST_BIN/systemctl" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$SYSTEMCTL_CALLS"
case "$*" in
    '--user is-active --quiet octo-codex-app-server.service')
        exit 1
        ;;
    '--user is-enabled --quiet octo-codex-app-server.service')
        test ! -f "$SYSTEMCTL_DISABLED"
        ;;
    '--user disable octo-codex-app-server.service')
        : > "$SYSTEMCTL_DISABLED"
        ;;
    '--user is-active --quiet '*|'--user is-enabled --quiet '*)
        exit 1
        ;;
esac
EOF
chmod +x "$TEST_BIN/systemctl"

cat > "$TEST_BIN/lsof" <<'EOF'
#!/usr/bin/env bash
[ ! -e "$CODEX_UNMANAGED_STOPPED" ] || exit 1
echo 4242
EOF
chmod +x "$TEST_BIN/lsof"

cat > "$TEST_BIN/ps" <<'EOF'
#!/usr/bin/env bash
case "$*" in
    '-p 4242 -o args=')
        echo '/legacy/codex app-server --listen unix://'
        ;;
    '-eo pid=,args=')
        echo '4343 /standalone/codex app-server proxy'
        ;;
esac
EOF
chmod +x "$TEST_BIN/ps"

cat > "$TEST_BIN/kill" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$KILL_CALLS"
case "$*" in
    '-TERM 4242')
        : > "$CODEX_UNMANAGED_STOPPED"
        ;;
    '-0 4242')
        [ ! -e "$CODEX_UNMANAGED_STOPPED" ]
        ;;
esac
EOF
chmod +x "$TEST_BIN/kill"

cat > "$TEST_CODEX/config.toml" <<'EOF'
model = "custom-model"
sandbox_mode = "workspace-write"

[projects."/tmp/example"]
trust_level = "trusted"

[hooks.state."local-hooks:session_start:0:0"]
trusted_hash = "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
enabled = false

[tui]
theme = "ansi"
EOF
mkdir -p "$TEST_CODEX/agents"
printf '%s\n' 'name = "personal-agent"' > "$TEST_CODEX/agents/personal-agent.toml"
mkdir -p "$TEST_CODEX/skills/retired-skill" "$TEST_CODEX/skills/.system/builtin"
printf '%s\n' 'retired' > "$TEST_CODEX/skills/retired-skill/SKILL.md"
printf '%s\n' 'builtin' > "$TEST_CODEX/skills/.system/builtin/SKILL.md"
mkdir -p "$TEST_HOME/.config/systemd/user"
printf '%s\n' '[Service]' > \
    "$TEST_HOME/.config/systemd/user/octo-codex-remote-control.service"

run_install() {
    HOME="$TEST_HOME" CODEX_HOME="$TEST_CODEX" \
        PATH="$TEST_BIN:$PATH" PLAYWRIGHT_BROWSERS_PATH="$PLAYWRIGHT_CACHE" \
        CURL_CALLS="$CURL_CALLS" STANDALONE_ENV="$STANDALONE_ENV" \
        STANDALONE_INSTALL_DIR="$STANDALONE_INSTALL_DIR" \
        CODEX_PROXY_CALLS="$CODEX_PROXY_CALLS" CODEX_PROXY_STDIN="$CODEX_PROXY_STDIN" \
        CODEX_DAEMON_CALLS="$CODEX_DAEMON_CALLS" \
        CODEX_REMOTE_CONTROL_CALLS="$CODEX_REMOTE_CONTROL_CALLS" \
        CODEX_BOOTSTRAP_UNMANAGED_MARKER="$CODEX_BOOTSTRAP_UNMANAGED_MARKER" \
        CODEX_UNMANAGED_STOPPED="$CODEX_UNMANAGED_STOPPED" KILL_CALLS="$KILL_CALLS" \
        CODEX_BOOTSTRAP_UNMANAGED_ONCE="${CODEX_BOOTSTRAP_UNMANAGED_ONCE:-}" \
        CODEX_RESTART_SHOULD_FAIL="${CODEX_RESTART_SHOULD_FAIL:-}" \
        CODEX_REMOTE_CONTROL_STOP_UNMANAGED="${CODEX_REMOTE_CONTROL_STOP_UNMANAGED:-}" \
        CODEX_REMOTE_CONTROL_STOP_SHOULD_FAIL="${CODEX_REMOTE_CONTROL_STOP_SHOULD_FAIL:-}" \
        CURL_SHOULD_STALL="${CURL_SHOULD_STALL:-}" \
        OCTO_CODEX_INSTALL_TIMEOUT_SECONDS="${OCTO_CODEX_INSTALL_TIMEOUT_SECONDS:-300}" \
        CODEX_INSTALL_DIR="$TEST_ROOT/inherited-bin" \
        SYSTEMCTL_CALLS="$SYSTEMCTL_CALLS" SYSTEMCTL_DISABLED="$SYSTEMCTL_DISABLED" \
        "$REPO_DIR/install.sh" "$@" >/dev/null
}

assert_section_line() {
    local section="$1" expected="$2"
    awk -v section="$section" -v expected="$expected" '
        $0 == section { in_section = 1; found_section = 1; next }
        in_section && /^\[/ { in_section = 0 }
        in_section && $0 == expected { found_value = 1 }
        END { exit !(found_section && found_value) }
    ' "$CONFIG"
}


run_install --restart
cmp "$REPO_DIR/global-tmux.conf" "$TEST_HOME/.tmux.conf"
grep -qFx 'sandbox_mode = "danger-full-access"' "$TEST_CODEX/config.toml"
grep -qFx 'approval_policy = "on-request"' "$TEST_CODEX/config.toml"
grep -qFx 'model = "gpt-6-astra"' "$TEST_CODEX/config.toml"
grep -qFx 'model_reasoning_effort = "medium"' "$TEST_CODEX/config.toml"
[ ! -e "$TEST_HOME/.claude" ]
cmp -s "$REPO_DIR/global-codex-hooks.json" "$TEST_CODEX/hooks.json"
jq -e '.hooks | keys == ["SessionStart"]' "$TEST_CODEX/hooks.json" >/dev/null
cmp -s "$REPO_DIR/global-AGENTS.md" "$TEST_CODEX/AGENTS.md"
[ ! -e "$TEST_CODEX/skills/retired-skill" ]
grep -qFx 'builtin' "$TEST_CODEX/skills/.system/builtin/SKILL.md"
for skill_dir in "$REPO_DIR/skills"/*/; do
    diff -r "$skill_dir" "$TEST_CODEX/skills/$(basename "$skill_dir")"
done
cmp -s "$REPO_DIR/codex-agents/octo-reviewer.toml" "$TEST_CODEX/agents/octo-reviewer.toml"
cmp -s "$REPO_DIR/codex-agents/octo-review-verifier.toml" "$TEST_CODEX/agents/octo-review-verifier.toml"
for agent_name in octo-reviewer octo-review-verifier; do
    agent_config="$TEST_CODEX/agents/$agent_name.toml"
    grep -qFx "name = \"$agent_name\"" "$agent_config"
    grep -qFx 'sandbox_mode = "read-only"' "$agent_config"
done
grep -qFx 'model = "gpt-5.6-sol"' "$TEST_CODEX/agents/octo-reviewer.toml"
grep -qFx 'model_reasoning_effort = "low"' "$TEST_CODEX/agents/octo-reviewer.toml"
grep -qFx 'model = "gpt-5.6-sol"' "$TEST_CODEX/agents/octo-review-verifier.toml"
grep -qFx 'model_reasoning_effort = "low"' "$TEST_CODEX/agents/octo-review-verifier.toml"
cp "$TEST_CODEX/config.toml" "$TEST_ROOT/first-config.toml"
grep -qFx 'name = "personal-agent"'  "$TEST_CODEX/agents/personal-agent.toml"
rm -f "$TEST_HOME/.local/bin/codex"
printf '%s\n' '#!/bin/sh' 'exit 99' > "$TEST_HOME/.local/bin/codex"
chmod +x "$TEST_HOME/.local/bin/codex"
# Normal installs must not invoke any operation that can interrupt a live turn.
for calls in "$CURL_CALLS" "$CODEX_DAEMON_CALLS" "$SYSTEMCTL_CALLS"; do
    if [ -e "$calls" ]; then
        cp "$calls" "$calls.before-normal"
    fi
done
run_install
run_install
# An installed binary is enough to preserve a runtime with a missing socket.
rm -f "$APP_SERVER_SOCKET"
run_install
# Preserve socket/PID owners even when the standalone binary is unavailable.
chmod -x "$TEST_CODEX/packages/standalone/current/bin/codex"
: > "$APP_SERVER_SOCKET"
run_install
rm -f "$APP_SERVER_SOCKET"
mkdir -p "$TEST_CODEX/app-server-daemon"
printf '%s\n' '{"pid":4242}' > "$TEST_CODEX/app-server-daemon/app-server.pid"
run_install
rm -f "$TEST_CODEX/app-server-daemon/app-server.pid"
chmod +x "$TEST_CODEX/packages/standalone/current/bin/codex"
: > "$APP_SERVER_SOCKET"
for calls in "$CURL_CALLS" "$CODEX_DAEMON_CALLS" "$SYSTEMCTL_CALLS"; do
    if [ -e "$calls.before-normal" ]; then
        cmp "$calls.before-normal" "$calls"
    else
        test ! -e "$calls"
    fi
done
test ! -e "$CODEX_PROXY_CALLS"
test ! -e "$CODEX_REMOTE_CONTROL_CALLS"
test ! -e "$KILL_CALLS"

CONFIG="$TEST_CODEX/config.toml"
cmp -s "$TEST_ROOT/first-config.toml" "$CONFIG"
grep -qFx 'model_verbosity = "low"' "$CONFIG"
grep -qFx 'personality = "pragmatic"' "$CONFIG"
! grep -qFx 'model = "custom-model"' "$CONFIG"
awk '
    /^\[/ { in_table = 1 }
    !in_table && $0 == "background_terminal_max_timeout = 3600000" { found = 1 }
    END { exit !found }
' "$CONFIG"
grep -qFx 'max_threads = 20' "$CONFIG"
assert_section_line '[features.multi_agent_v2]' 'enabled = true'
assert_section_line '[features.multi_agent_v2]' 'max_concurrent_threads_per_session = 20'
assert_section_line '[features.multi_agent_v2]' 'min_wait_timeout_ms = 300000'
assert_section_line '[features.multi_agent_v2]' 'default_wait_timeout_ms = 3600000'
assert_section_line '[features.multi_agent_v2]' 'max_wait_timeout_ms = 3600000'
assert_section_line '["projects"."/tmp/example"]' '"trust_level" = "trusted"'
assert_section_line '["hooks"."state"."local-hooks:session_start:0:0"]' '"enabled" = false'
! grep -qF '/home/clavier' "$CONFIG"
! test -e "$TEST_HOME/.codex/config.toml"
grep -qFx -- '-fsSL https://chatgpt.com/codex/install.sh' "$CURL_CALLS"
test "$(wc -l < "$CURL_CALLS")" -eq 1
grep -qFx '1' "$STANDALONE_ENV"
grep -qFx "$TEST_HOME/.local/bin" "$STANDALONE_INSTALL_DIR"
test ! -e "$TEST_ROOT/inherited-bin/codex"
test -x "$TEST_CODEX/packages/standalone/current/bin/codex"
test -x "$TEST_HOME/.local/bin/codex"
test -L "$TEST_HOME/.local/bin/codex"
test "$(readlink "$TEST_HOME/.local/bin/codex")" = \
    "$TEST_CODEX/packages/standalone/current/bin/codex"
if [[ "$(uname -s)" == Linux ]]; then
    test ! -e "$TEST_HOME/.config/systemd/user/octo-codex-remote-control.service"
    test ! -e "$TEST_HOME/.config/systemd/user/octo-codex-app-server.service"
    for obsolete_unit in octo-codex-remote-control.service octo-codex-app-server.service; do
        test "$(grep -cFx -- "--user stop $obsolete_unit" "$SYSTEMCTL_CALLS")" -eq 1
        test "$(grep -cFx -- "--user disable $obsolete_unit" "$SYSTEMCTL_CALLS")" -eq 1
    done
    test "$(grep -cFx -- '--user is-active --quiet octo-codex-app-server.service' "$SYSTEMCTL_CALLS")" -eq 1
    test "$(grep -cFx -- '--user is-enabled --quiet octo-codex-app-server.service' "$SYSTEMCTL_CALLS")" -eq 1
    test "$(grep -cFx -- '--user daemon-reload' "$SYSTEMCTL_CALLS")" -eq 1
    ! grep -q -E -- '--user (enable|start|restart) ' "$SYSTEMCTL_CALLS"
else
    test -e "$TEST_HOME/.config/systemd/user/octo-codex-remote-control.service"
    test ! -e "$SYSTEMCTL_CALLS"
fi
test "$(grep -cFx 'app-server daemon bootstrap --remote-control' "$CODEX_DAEMON_CALLS")" -eq 1
test "$(grep -cFx 'app-server daemon restart' "$CODEX_DAEMON_CALLS")" -eq 1

restart_error="$TEST_ROOT/restart-error"
if CODEX_RESTART_SHOULD_FAIL=1 run_install --restart 2>"$restart_error"; then
    echo "Expected install.sh --restart to fail when the managed daemon cannot restart" >&2
    exit 1
fi
grep -qF 'ERROR: Codex managed app-server restart failed.' "$restart_error"
grep -qF 'simulated restart failure' "$restart_error"

: > "$CODEX_DAEMON_CALLS"
: > "$CODEX_REMOTE_CONTROL_CALLS"
rm -f "$CODEX_BOOTSTRAP_UNMANAGED_MARKER"
rm -f "$CODEX_UNMANAGED_STOPPED" "$KILL_CALLS"
CODEX_BOOTSTRAP_UNMANAGED_ONCE=1 CODEX_REMOTE_CONTROL_STOP_UNMANAGED=1 \
    run_install --restart
test "$(grep -cFx 'app-server daemon bootstrap --remote-control' "$CODEX_DAEMON_CALLS")" -eq 2
! grep -qFx 'app-server daemon restart' "$CODEX_DAEMON_CALLS"
grep -qFx 'remote-control stop' "$CODEX_REMOTE_CONTROL_CALLS"
grep -qFx -- '-TERM 4343' "$KILL_CALLS"
grep -qFx -- '-TERM 4242' "$KILL_CALLS"
grep -qFx -- '-0 4242' "$KILL_CALLS"

: > "$CODEX_DAEMON_CALLS"
: > "$CODEX_REMOTE_CONTROL_CALLS"
rm -f "$CODEX_BOOTSTRAP_UNMANAGED_MARKER"
if CODEX_BOOTSTRAP_UNMANAGED_ONCE=1 CODEX_REMOTE_CONTROL_STOP_SHOULD_FAIL=1 \
    run_install --restart 2>"$restart_error"; then
    echo "Expected install.sh --restart to fail when Remote Control cannot stop" >&2
    exit 1
fi
grep -qF 'ERROR: could not stop the existing Remote Control app-server.' "$restart_error"
grep -qF 'simulated Remote Control stop failure' "$restart_error"
test "$(grep -cFx 'app-server daemon bootstrap --remote-control' "$CODEX_DAEMON_CALLS")" -eq 1
grep -qFx 'remote-control stop' "$CODEX_REMOTE_CONTROL_CALLS"

# A failed replacement bootstrap preserves a potentially working old service.
printf '%s\n' '[Service]' > \
    "$TEST_HOME/.config/systemd/user/octo-codex-remote-control.service"
: > "$SYSTEMCTL_CALLS"
rm -f "$APP_SERVER_SOCKET"
chmod -x "$TEST_CODEX/packages/standalone/current/bin/codex"
rm -f "$TEST_HOME/.local/bin/codex"
printf '%s\n' \
    '#!/usr/bin/env bash' \
    'CODEX_NPM_PREFIX="${CODEX_NPM_PREFIX:-$HOME/.local/share/octo-codex}"' \
    'update_codex() {' \
    '    :' \
    '}' > "$TEST_HOME/.local/bin/codex"
chmod +x "$TEST_HOME/.local/bin/codex"
start_seconds=$SECONDS
curl_calls_before=$(wc -l < "$CURL_CALLS")
CURL_SHOULD_STALL=1 OCTO_CODEX_INSTALL_TIMEOUT_SECONDS=1 run_install
test "$((SECONDS - start_seconds))" -lt 3
test "$(wc -l < "$CURL_CALLS")" -eq "$((curl_calls_before + 1))"
test ! -e "$TEST_HOME/.local/bin/codex"
test -e "$TEST_HOME/.config/systemd/user/octo-codex-remote-control.service"
! grep -q -E -- '--user (stop|disable) ' "$SYSTEMCTL_CALLS"

# With no installed executable or server ownership markers, normal installation
# still provisions Codex and bootstraps it without an explicit restart.
: > "$CODEX_DAEMON_CALLS"
run_install
grep -qFx 'app-server daemon bootstrap --remote-control' "$CODEX_DAEMON_CALLS"
! grep -qFx 'app-server daemon restart' "$CODEX_DAEMON_CALLS"
test -x "$TEST_CODEX/packages/standalone/current/bin/codex"
