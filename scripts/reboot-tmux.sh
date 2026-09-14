#!/usr/bin/env bash
# Destroy every session/pane on the default server and restart it empty.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
command -v tmux >/dev/null

if tmux -L default display-message -p '#{pid}' >/dev/null 2>&1; then
    tmux -L default kill-server
fi

# A temporary session keeps startup alive until exit-empty has been disabled.
env -u NO_COLOR tmux -L default -f "$SCRIPT_DIR/../global-tmux.conf" \
    new-session -d -s restart-bootstrap \; \
    set-option -g exit-empty off \; \
    kill-session -t restart-bootstrap

tmux -L default display-message -p 'Default tmux server restarted (pid=#{pid}); no sessions or panes.'
