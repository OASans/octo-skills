import json
from pathlib import Path
import signal
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from stop_legacy_codex_updater import stop_legacy_updater


class LegacyUpdaterTest(unittest.TestCase):
    executable = "/isolated/codex"
    error = "Error: cannot verify pid-managed process 39901: legacy start time changed"

    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.path = Path(self.directory.name) / "app-server-daemon/app-server-updater.pid"
        self.path.parent.mkdir()
        self.record = {"pid": 39901, "processStartTime": "Sun Sep 13 22:29:47 2026"}
        self.write_record()

    def write_record(self):
        self.path.write_text(json.dumps(self.record))

    def stop(self, error=None):
        return stop_legacy_updater(self.directory.name, self.executable, error or self.error)

    @patch("stop_legacy_codex_updater.os.kill")
    @patch("stop_legacy_codex_updater.subprocess.run")
    def test_stops_only_verified_updater_and_retains_pid_record(self, run, kill):
        run.return_value.stdout = f"{self.executable} app-server daemon pid-update-loop\n"
        kill.side_effect = [None, ProcessLookupError()]
        self.assertTrue(self.stop())
        kill.assert_any_call(39901, signal.SIGTERM)
        self.assertEqual(json.loads(self.path.read_text()), self.record)

    @patch("stop_legacy_codex_updater.os.kill")
    @patch("stop_legacy_codex_updater.subprocess.run")
    def test_refuses_other_commands_including_server(self, run, kill):
        for command in ("unrelated", f"{self.executable} app-server --managed-daemon"):
            with self.subTest(command=command):
                run.return_value.stdout = command
                self.assertFalse(self.stop())
        kill.assert_not_called()

    @patch("stop_legacy_codex_updater.os.kill")
    def test_refuses_other_errors_pids_and_modern_records(self, kill):
        self.assertFalse(self.stop("some other failure"))
        self.assertFalse(self.stop(self.error.replace("39901", "39902")))
        self.record["processIdentity"] = {"uniqueId": 123}
        self.write_record()
        self.assertFalse(self.stop())
        self.path.write_text("invalid json")
        self.assertFalse(self.stop())
        kill.assert_not_called()

    @patch("stop_legacy_codex_updater.os.kill")
    @patch("stop_legacy_codex_updater.subprocess.run")
    def test_refuses_record_changed_during_inspection(self, run, kill):
        def inspect(*args, **kwargs):
            self.record["pid"] = 39902
            self.write_record()
            return subprocess.CompletedProcess(args, 0,
                stdout=f"{self.executable} app-server daemon pid-update-loop")
        run.side_effect = inspect
        self.assertFalse(self.stop())
        kill.assert_not_called()

    @patch("stop_legacy_codex_updater.time.monotonic", side_effect=[0, 11])
    @patch("stop_legacy_codex_updater.os.kill")
    @patch("stop_legacy_codex_updater.subprocess.run")
    def test_reports_timeout_without_force_killing(self, run, kill, monotonic):
        run.return_value.stdout = f"{self.executable} app-server daemon pid-update-loop"
        self.assertFalse(self.stop())
        kill.assert_called_once_with(39901, signal.SIGTERM)


if __name__ == "__main__":
    unittest.main()
