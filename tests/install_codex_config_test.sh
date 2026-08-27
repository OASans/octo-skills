#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_ROOT="$(mktemp -d)"
trap 'rm -rf "$TEST_ROOT"' EXIT

TEST_HOME="$TEST_ROOT/home"
PLAYWRIGHT_CACHE="$TEST_ROOT/playwright"
TEST_BIN="$TEST_ROOT/bin"
CURL_CALLS="$TEST_ROOT/curl-calls"
CODEX_PROXY_CALLS="$TEST_ROOT/codex-proxy-calls"
CODEX_PROXY_STDIN="$TEST_ROOT/codex-proxy-stdin"
STANDALONE_ENV="$TEST_ROOT/standalone-env"
STANDALONE_INSTALL_DIR="$TEST_ROOT/standalone-install-dir"
APP_SERVER_SOCKET="$TEST_HOME/.codex/app-server-control/app-server-control.sock"
SYSTEMCTL_CALLS="$TEST_ROOT/systemctl-calls"
SYSTEMCTL_DISABLED="$TEST_ROOT/systemctl-disabled"
mkdir -p \
    "$TEST_HOME/.codex" \
    "$(dirname "$APP_SERVER_SOCKET")" \
    "$PLAYWRIGHT_CACHE/chromium-test" \
    "$TEST_BIN"
: > "$APP_SERVER_SOCKET"
for command_name in codex node npm npx sourcekit-lsp; do
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
standalone_bin="$HOME/.codex/packages/standalone/current/bin"
visible_bin="${CODEX_INSTALL_DIR:-$HOME/.local/bin}"
printf '%s\n' "$visible_bin" > "$STANDALONE_INSTALL_DIR"
mkdir -p "$standalone_bin" "$visible_bin"
cat > "$standalone_bin/codex" <<'CODEX'
#!/bin/sh
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

cat > "$TEST_HOME/.codex/config.toml" <<'EOF'
model = "custom-model"

[projects."/tmp/example"]
trust_level = "trusted"

[tui]
theme = "ansi"
EOF
mkdir -p "$TEST_HOME/.codex/agents"
printf '%s\n' 'name = "personal-agent"' > "$TEST_HOME/.codex/agents/personal-agent.toml"
mkdir -p "$TEST_HOME/.config/systemd/user"
printf '%s\n' '[Service]' > \
    "$TEST_HOME/.config/systemd/user/octo-codex-remote-control.service"

run_install() {
    HOME="$TEST_HOME" CODEX_HOME="$TEST_HOME/.codex" \
        PATH="$TEST_BIN:$PATH" PLAYWRIGHT_BROWSERS_PATH="$PLAYWRIGHT_CACHE" \
        CURL_CALLS="$CURL_CALLS" STANDALONE_ENV="$STANDALONE_ENV" \
        STANDALONE_INSTALL_DIR="$STANDALONE_INSTALL_DIR" \
        CODEX_PROXY_CALLS="$CODEX_PROXY_CALLS" CODEX_PROXY_STDIN="$CODEX_PROXY_STDIN" \
        CURL_SHOULD_STALL="${CURL_SHOULD_STALL:-}" \
        OCTO_CODEX_INSTALL_TIMEOUT_SECONDS="${OCTO_CODEX_INSTALL_TIMEOUT_SECONDS:-300}" \
        CODEX_INSTALL_DIR="$TEST_ROOT/inherited-bin" \
        SYSTEMCTL_CALLS="$SYSTEMCTL_CALLS" SYSTEMCTL_DISABLED="$SYSTEMCTL_DISABLED" \
        "$REPO_DIR/install.sh" >/dev/null
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

assert_section_hash() {
    local section="$1"
    awk -v section="$section" '
        $0 == section { in_section = 1; found_section = 1; next }
        in_section && /^\[/ { in_section = 0 }
        in_section && /^trusted_hash = "sha256:[0-9a-f]+"$/ {
            hash = $0
            sub(/^trusted_hash = "sha256:/, "", hash)
            sub(/"$/, "", hash)
            if (length(hash) == 64) found_hash = 1
        }
        END { exit !(found_section && found_hash) }
    ' "$CONFIG"
}

run_install
cmp -s "$REPO_DIR/global-codex-config.toml" "$TEST_HOME/.codex/config.toml"
jq -e '.env.OCTO_HOOK_FILE == "/tmp/octo-hook-octo-code-default.jsonl"' \
    "$TEST_HOME/.claude/settings.json" >/dev/null
jq --slurpfile settings "$REPO_DIR/global-settings.json" -e '
    . == {hooks: {SessionStart: $settings[0].hooks.SessionStart}}
' "$TEST_HOME/.codex/hooks.json" >/dev/null
jq -e '.remoteControlAtStartup == true' "$TEST_HOME/.claude/settings.json" >/dev/null
cmp -s "$REPO_DIR/global-CLAUDE.md" "$TEST_HOME/.claude/CLAUDE.md"
cmp -s "$REPO_DIR/global-CLAUDE.md" "$TEST_HOME/.codex/AGENTS.md"
cmp -s "$REPO_DIR/codex-agents/octo-reviewer.toml" "$TEST_HOME/.codex/agents/octo-reviewer.toml"
cmp -s "$REPO_DIR/codex-agents/octo-review-verifier.toml" "$TEST_HOME/.codex/agents/octo-review-verifier.toml"
for agent_name in octo-reviewer octo-review-verifier; do
    agent_config="$TEST_HOME/.codex/agents/$agent_name.toml"
    grep -qFx "name = \"$agent_name\"" "$agent_config"
    grep -qFx 'model = "gpt-5.6-terra"' "$agent_config"
    grep -qFx 'model_reasoning_effort = "high"' "$agent_config"
    grep -qFx 'sandbox_mode = "read-only"' "$agent_config"
done
grep -qFx 'name = "personal-agent"' "$TEST_HOME/.codex/agents/personal-agent.toml"
rm -f "$TEST_HOME/.local/bin/codex"
printf '%s\n' '#!/bin/sh' 'exit 99' > "$TEST_HOME/.local/bin/codex"
chmod +x "$TEST_HOME/.local/bin/codex"
run_install
run_install

CONFIG="$TEST_HOME/.codex/config.toml"
cmp -s "$REPO_DIR/global-codex-config.toml" "$CONFIG"
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
test "$(grep -c '^\[projects\."/home/clavier/Desktop/fin-[1-6]"\]$' "$CONFIG")" -eq 6
assert_section_line \
    '[projects."/home/clavier/Desktop/octo-1"]' \
    'trust_level = "trusted"'
grep -qFx '[hooks.state]' "$CONFIG"
for project_number in 1 2 3 4 5 6; do
    assert_section_line \
        "[projects.\"/home/clavier/Desktop/fin-$project_number\"]" \
        'trust_level = "trusted"'
done
test "$(grep -c '^\[hooks.state\.' "$CONFIG")" -eq 1
assert_section_hash \
    '[hooks.state."/home/clavier/.codex/hooks.json:session_start:0:0"]'
grep -qFx -- '-fsSL https://chatgpt.com/codex/install.sh' "$CURL_CALLS"
test "$(wc -l < "$CURL_CALLS")" -eq 3
grep -qFx '1' "$STANDALONE_ENV"
grep -qFx "$TEST_HOME/.local/bin" "$STANDALONE_INSTALL_DIR"
test ! -e "$TEST_ROOT/inherited-bin/codex"
test -x "$TEST_HOME/.codex/packages/standalone/current/bin/codex"
test -x "$TEST_HOME/.local/bin/codex"
test -L "$TEST_HOME/.local/bin/codex"
test "$(readlink "$TEST_HOME/.local/bin/codex")" = \
    "$TEST_HOME/.codex/packages/standalone/current/bin/codex"
test ! -e "$TEST_HOME/.config/systemd/user/octo-codex-remote-control.service"
test ! -e "$TEST_HOME/.config/systemd/user/octo-codex-app-server.service"
for obsolete_unit in octo-codex-remote-control.service octo-codex-app-server.service; do
    test "$(grep -cFx -- "--user stop $obsolete_unit" "$SYSTEMCTL_CALLS")" -eq 1
    test "$(grep -cFx -- "--user disable $obsolete_unit" "$SYSTEMCTL_CALLS")" -eq 1
done
test "$(grep -cFx -- '--user is-active --quiet octo-codex-app-server.service' "$SYSTEMCTL_CALLS")" -eq 3
test "$(grep -cFx -- '--user is-enabled --quiet octo-codex-app-server.service' "$SYSTEMCTL_CALLS")" -eq 3
test "$(grep -cFx -- '--user daemon-reload' "$SYSTEMCTL_CALLS")" -eq 1
! grep -q -E -- '--user (enable|start|restart) ' "$SYSTEMCTL_CALLS"
test "$(grep -cFx "app-server proxy --sock $APP_SERVER_SOCKET" "$CODEX_PROXY_CALLS")" -eq 3
test "$(grep -cF '"method":"config/batchWrite"' "$CODEX_PROXY_STDIN")" -eq 3
test "$(grep -cF '"edits":[]' "$CODEX_PROXY_STDIN")" -eq 3
test "$(grep -cF '"reloadUserConfig":true' "$CODEX_PROXY_STDIN")" -eq 3

# A failed replacement bootstrap preserves a potentially working old service.
printf '%s\n' '[Service]' > \
    "$TEST_HOME/.config/systemd/user/octo-codex-remote-control.service"
: > "$SYSTEMCTL_CALLS"
rm -f "$APP_SERVER_SOCKET"
chmod -x "$TEST_HOME/.codex/packages/standalone/current/bin/codex"
rm -f "$TEST_HOME/.local/bin/codex"
printf '%s\n' \
    '#!/usr/bin/env bash' \
    'CODEX_NPM_PREFIX="${CODEX_NPM_PREFIX:-$HOME/.local/share/octo-codex}"' \
    'update_codex() {' \
    '    :' \
    '}' > "$TEST_HOME/.local/bin/codex"
chmod +x "$TEST_HOME/.local/bin/codex"
start_seconds=$SECONDS
CURL_SHOULD_STALL=1 OCTO_CODEX_INSTALL_TIMEOUT_SECONDS=1 run_install
test "$((SECONDS - start_seconds))" -lt 3
test "$(wc -l < "$CURL_CALLS")" -eq 4
test ! -e "$TEST_HOME/.local/bin/codex"
test -e "$TEST_HOME/.config/systemd/user/octo-codex-remote-control.service"
! grep -q -E -- '--user (stop|disable) ' "$SYSTEMCTL_CALLS"
