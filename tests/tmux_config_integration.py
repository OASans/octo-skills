"""Run directly: verify the shared config on an isolated real tmux server."""

import os
from pathlib import Path
import subprocess
import tempfile


def main():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix=".tmux-test-", dir=root) as scratch:
        command = ["tmux", "-S", str(Path(scratch) / "socket")]
        env = {**os.environ, "NO_COLOR": "1"}
        env.pop("TMUX", None)

        def run(*args, check=True):
            return subprocess.run(
                [*command, *args], env=env, check=check,
                capture_output=True, text=True, timeout=10,
            )

        try:
            run("-f", str(root / "global-tmux.conf"), "new-session", "-d",
                "-s", "config-test", "sleep 60")
            result = run("show-environment", "-g")
            assert not any(line.startswith("NO_COLOR=") for line in result.stdout.splitlines())
            assert run("show-options", "-gv", "default-terminal").stdout.strip() == "tmux-256color"
            run("set-environment", "-g", "NO_COLOR", "1")
            run("source-file", str(root / "global-tmux.conf"))
            assert "NO_COLOR=1" not in run("show-environment", "-g").stdout.splitlines()
        finally:
            run("kill-server", check=False)

        # Exercise the destructive helper with a private default-server socket.
        command = ["tmux", "-L", "default"]
        env["TMUX_TMPDIR"] = scratch
        try:
            run("-f", "/dev/null", "new-session", "-d", "-s", "old-pane", "sleep 60")
            old_pid = run("display-message", "-p", "#{pid}").stdout.strip()
            for _ in range(2):
                subprocess.run(
                    ["bash", str(root / "scripts/reboot-tmux.sh")],
                    env=env, check=True, capture_output=True, text=True, timeout=10,
                )
                new_pid = run("display-message", "-p", "#{pid}").stdout.strip()
                assert new_pid != old_pid
                old_pid = new_pid
                assert not run("list-sessions").stdout.strip()
                assert run("show-options", "-gv", "exit-empty").stdout.strip() == "off"
                assert not any(
                    line.startswith("NO_COLOR=")
                    for line in run("show-environment", "-g").stdout.splitlines()
                )
        finally:
            run("kill-server", check=False)
    print("tmux config integration passed")


if __name__ == "__main__":
    main()
