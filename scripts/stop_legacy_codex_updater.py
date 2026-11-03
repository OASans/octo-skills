"""Stop a verified obsolete updater after Codex rejects its legacy PID record."""

import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import time


def stop_legacy_updater(codex_dir, executable, error):
    match = re.search(
        r"cannot verify pid-managed process (\d+): legacy start time changed", error
    )
    if match is None:
        return False
    path = Path(codex_dir) / "app-server-daemon/app-server-updater.pid"
    try:
        original = path.read_text()
        record = json.loads(original)
        pid = record["pid"]
        if (type(pid) is not int or pid <= 0 or pid != int(match[1])
                or record.get("processIdentity") is not None):
            return False
        command = subprocess.run(
            ["ps", "-p", str(pid), "-o", "args="],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
        if command != f"{executable} app-server daemon pid-update-loop":
            return False
        if path.read_text() != original:
            return False
        os.kill(pid, signal.SIGTERM)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return True
            time.sleep(0.1)
    except (OSError, ValueError, KeyError, TypeError, AttributeError,
            subprocess.CalledProcessError):
        return False
    return False


if __name__ == "__main__":
    sys.exit(0 if stop_legacy_updater(*sys.argv[1:]) else 1)
