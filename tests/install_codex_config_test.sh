#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TEST_ROOT="$(mktemp -d)"
trap 'rm -rf "$TEST_ROOT"' EXIT

TEST_HOME="$TEST_ROOT/home"
PLAYWRIGHT_CACHE="$TEST_ROOT/playwright"
TEST_BIN="$TEST_ROOT/bin"
mkdir -p "$TEST_HOME/.codex" "$PLAYWRIGHT_CACHE/chromium-test" "$TEST_BIN"
for command_name in codex node npm npx sourcekit-lsp; do
    ln -s "$(command -v true)" "$TEST_BIN/$command_name"
done

cat > "$TEST_HOME/.codex/config.toml" <<'EOF'
model = "custom-model"

[projects."/tmp/example"]
trust_level = "trusted"

[tui]
theme = "ansi"
EOF

run_install() {
    HOME="$TEST_HOME" PATH="$TEST_BIN:$PATH" PLAYWRIGHT_BROWSERS_PATH="$PLAYWRIGHT_CACHE" \
        "$REPO_DIR/install.sh" >/dev/null
}

run_install
cmp -s "$REPO_DIR/global-codex-config.toml" "$TEST_HOME/.codex/config.toml"
run_install

CONFIG="$TEST_HOME/.codex/config.toml"
cmp -s "$REPO_DIR/global-codex-config.toml" "$CONFIG"
! grep -qFx 'model = "custom-model"' "$CONFIG"
grep -qFx 'max_threads = 20' "$CONFIG"
! grep -q '^\[hooks\.state' "$CONFIG"
test -x "$TEST_HOME/.local/bin/codex"
grep -q -- '--dangerously-bypass-hook-trust' "$TEST_HOME/.local/bin/codex"
