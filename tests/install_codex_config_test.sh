#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_ROOT="$(mktemp -d)"
trap 'rm -rf "$TEST_ROOT"' EXIT

TEST_HOME="$TEST_ROOT/home"
PLAYWRIGHT_CACHE="$TEST_ROOT/playwright"
TEST_BIN="$TEST_ROOT/bin"
TEST_NPM_ROOT="$TEST_ROOT/npm/lib/node_modules"
NPM_CALLS="$TEST_ROOT/npm-calls"
CURL_CALLS="$TEST_ROOT/curl-calls"
STANDALONE_ENV="$TEST_ROOT/standalone-env"
STANDALONE_INSTALL_DIR="$TEST_ROOT/standalone-install-dir"
mkdir -p "$TEST_HOME/.codex" "$PLAYWRIGHT_CACHE/chromium-test" "$TEST_BIN"
for command_name in codex node npx sourcekit-lsp; do
    ln -s "$(command -v true)" "$TEST_BIN/$command_name"
done

cat > "$TEST_BIN/npm" <<'EOF'
#!/usr/bin/env bash
printf '%s\n' "$*" >> "$NPM_CALLS"
case "${1:-}" in
    root)
        printf '%s\n' "$TEST_NPM_ROOT"
        ;;
    install)
        mkdir -p "$TEST_NPM_ROOT/@openai/codex/bin"
        : > "$TEST_NPM_ROOT/@openai/codex/bin/codex.js"
        ;;
esac
EOF
chmod +x "$TEST_BIN/npm"

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
printf '#!/bin/sh\nexit 0\n' > "$standalone_bin/codex"
chmod +x "$standalone_bin/codex"
ln -sf "$standalone_bin/codex" "$visible_bin/codex"
INSTALLER
EOF
chmod +x "$TEST_BIN/curl"

cat > "$TEST_HOME/.codex/config.toml" <<'EOF'
model = "custom-model"

[projects."/tmp/example"]
trust_level = "trusted"

[tui]
theme = "ansi"
EOF

run_install() {
    HOME="$TEST_HOME" PATH="$TEST_BIN:$PATH" PLAYWRIGHT_BROWSERS_PATH="$PLAYWRIGHT_CACHE" \
        TEST_NPM_ROOT="$TEST_NPM_ROOT" NPM_CALLS="$NPM_CALLS" \
        CURL_CALLS="$CURL_CALLS" STANDALONE_ENV="$STANDALONE_ENV" \
        STANDALONE_INSTALL_DIR="$STANDALONE_INSTALL_DIR" \
        CURL_SHOULD_STALL="${CURL_SHOULD_STALL:-}" \
        OCTO_CODEX_INSTALL_TIMEOUT_SECONDS="${OCTO_CODEX_INSTALL_TIMEOUT_SECONDS:-300}" \
        CODEX_INSTALL_DIR="$TEST_ROOT/inherited-bin" \
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
jq -e '.remoteControlAtStartup == true' "$TEST_HOME/.claude/settings.json" >/dev/null
run_install

CONFIG="$TEST_HOME/.codex/config.toml"
cmp -s "$REPO_DIR/global-codex-config.toml" "$CONFIG"
! grep -qFx 'model = "custom-model"' "$CONFIG"
grep -qFx 'max_threads = 20' "$CONFIG"
awk '
    $0 == "[features.multi_agent_v2]" { in_section = 1; next }
    /^\[/ { in_section = 0 }
    in_section && $0 == "max_concurrent_threads_per_session = 20" { found = 1 }
    END { exit !found }
' "$CONFIG"
test "$(grep -c '^\[projects\."/home/clavier/Desktop/fin-[1-6]"\]$' "$CONFIG")" -eq 6
grep -qFx '[hooks.state]' "$CONFIG"
for project_number in 1 2 3 4 5 6; do
    assert_section_line \
        "[projects.\"/home/clavier/Desktop/fin-$project_number\"]" \
        'trust_level = "trusted"'
done
for hook_event in pre_tool_use permission_request post_tool_use session_start user_prompt_submit stop; do
    assert_section_hash \
        "[hooks.state.\"/home/clavier/.codex/hooks.json:$hook_event:0:0\"]"
done
for project_number in 1 2 3 4 5 6; do
    assert_section_hash \
        "[hooks.state.\"/home/clavier/Desktop/fin-$project_number/.codex/hooks.json:subagent_stop:0:0\"]"
done
test -f "$TEST_NPM_ROOT/@openai/codex/bin/codex.js"
grep -q -- "--prefix $TEST_HOME/.local/share/octo-codex" "$NPM_CALLS"
grep -qFx -- '-fsSL https://chatgpt.com/codex/install.sh' "$CURL_CALLS"
test "$(wc -l < "$CURL_CALLS")" -eq 1
grep -qFx '1' "$STANDALONE_ENV"
grep -qFx "$TEST_HOME/.local/bin" "$STANDALONE_INSTALL_DIR"
test ! -e "$TEST_ROOT/inherited-bin/codex"
test -x "$TEST_HOME/.codex/packages/standalone/current/bin/codex"
test -x "$TEST_HOME/.local/bin/codex"
test ! -L "$TEST_HOME/.local/bin/codex"
grep -q -- 'npm view @openai/codex@latest version' "$TEST_HOME/.local/bin/codex"
grep -q -- '--dangerously-bypass-hook-trust' "$TEST_HOME/.local/bin/codex"

chmod -x "$TEST_HOME/.codex/packages/standalone/current/bin/codex"
start_seconds=$SECONDS
CURL_SHOULD_STALL=1 OCTO_CODEX_INSTALL_TIMEOUT_SECONDS=1 run_install
test "$((SECONDS - start_seconds))" -lt 3
test "$(wc -l < "$CURL_CALLS")" -eq 2
test ! -L "$TEST_HOME/.local/bin/codex"
