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
        "$REPO_DIR/install.sh" >/dev/null
}

run_install
cmp -s "$REPO_DIR/global-codex-config.toml" "$TEST_HOME/.codex/config.toml"
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
! grep -q '^\[hooks\.state' "$CONFIG"
test -f "$TEST_NPM_ROOT/@openai/codex/bin/codex.js"
grep -q -- "--prefix $TEST_HOME/.local/share/octo-codex" "$NPM_CALLS"
test -x "$TEST_HOME/.local/bin/codex"
grep -q -- 'npm view @openai/codex@latest version' "$TEST_HOME/.local/bin/codex"
grep -q -- '--dangerously-bypass-hook-trust' "$TEST_HOME/.local/bin/codex"
