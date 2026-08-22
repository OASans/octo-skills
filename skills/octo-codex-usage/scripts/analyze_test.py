#!/usr/bin/env python3
"""Tests for the Codex unusual-usage analyzer."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

import analyze


class ClassifyCommandTests(unittest.TestCase):
    def test_ordinary_search_and_json_tools_are_suppressed(self) -> None:
        self.assertEqual(analyze.classify_command("rg todo . | jq .", set()), set())

    def test_inline_python_is_grouped_by_purpose(self) -> None:
        command = "python3 - <<'PY'\nimport json\nprint(json.loads('{}'))\nPY"
        self.assertEqual(
            analyze.classify_command(command, set()),
            {analyze.Candidate("inline", "inline Python: JSON transformation")},
        )

    def test_searching_for_inline_python_is_not_an_inline_execution(self) -> None:
        self.assertEqual(
            analyze.classify_command("rg -n 'python3 -c' scripts", set()), set()
        )

    def test_multiline_search_pattern_is_not_treated_as_commands(self) -> None:
        command = "rg 'class Example:\n    def method(self):' source.py"
        self.assertEqual(analyze.classify_command(command, set()), set())

    def test_normal_python_test_command_is_suppressed(self) -> None:
        self.assertEqual(
            analyze.classify_command("python3 -m unittest discover", set()), set()
        )

    def test_one_line_python_calculation_is_classified(self) -> None:
        self.assertEqual(
            analyze.classify_command("python3 -c 'print(2 + 2)'", set()),
            {
                analyze.Candidate(
                    "inline", "inline Python: one-line calculation or formatting"
                )
            },
        )

    def test_patch_heredoc_body_is_not_treated_as_commands(self) -> None:
        command = "apply_patch <<'PATCH'\n+def secret():\n+    pass\nPATCH"
        self.assertEqual(analyze.classify_command(command, set()), set())

    def test_numbered_file_view_is_suppressed(self) -> None:
        self.assertEqual(analyze.classify_command("nl -ba source.py", set()), set())

    def test_common_javascript_tools_are_suppressed(self) -> None:
        for executable in (
            "eslint",
            "mktemp",
            "prettier",
            "rmdir",
            "tsc",
            "ulimit",
            "unlink",
            "vitest",
        ):
            with self.subTest(executable=executable):
                self.assertEqual(analyze.classify_command(executable, set()), set())

    def test_semicolon_separates_commands(self) -> None:
        self.assertEqual(
            analyze.classify_command("git status; ffmpeg -i in.mov out.mp4", set()),
            {analyze.Candidate("executable", "unusual executable: ffmpeg")},
        )

    def test_wrappers_consume_their_operands(self) -> None:
        expected = {analyze.Candidate("executable", "unusual executable: ffmpeg")}
        self.assertEqual(
            analyze.classify_command("sudo -u root ffmpeg -i in.mov out.mp4", set()),
            expected,
        )
        self.assertEqual(
            analyze.classify_command("timeout 10 ffmpeg -i in.mov out.mp4", set()),
            expected,
        )

    def test_unusual_executable_is_reported_without_arguments(self) -> None:
        self.assertEqual(
            analyze.classify_command("sqlite3 private.db '.tables'", set()),
            {analyze.Candidate("executable", "unusual executable: sqlite3")},
        )

    def test_extra_ignore_suppresses_executable(self) -> None:
        self.assertEqual(
            analyze.classify_command("sqlite3 private.db '.tables'", {"sqlite3"}),
            set(),
        )


class AnalyzeTests(unittest.TestCase):
    def test_analyze_filters_time_and_never_reports_raw_command(self) -> None:
        now = datetime(2026, 8, 22, tzinfo=timezone.utc)
        with tempfile.TemporaryDirectory() as temporary_directory:
            codex_home = Path(temporary_directory)
            sessions = codex_home / "sessions"
            sessions.mkdir()
            transcript = sessions / "rollout-example.jsonl"
            records = [
                self.command_record("2026-08-21T00:00:00Z", "sqlite3 secret.db '.tables'"),
                self.command_record("2026-08-10T00:00:00Z", "ffmpeg -i private.mov out.mp4"),
            ]
            transcript.write_text("\n".join(json.dumps(record) for record in records))

            report = analyze.analyze(codex_home, 7, set(), now=now)
            rendered = analyze.render_report(report, 7, min_count=1, limit=20)

        self.assertEqual(report.executions, 1)
        self.assertIn("unusual executable: sqlite3", rendered)
        self.assertNotIn("secret.db", rendered)
        self.assertNotIn(".tables", rendered)

    @staticmethod
    def command_record(timestamp: str, command: str) -> dict[str, object]:
        return {
            "timestamp": timestamp,
            "type": "event_msg",
            "payload": {
                "type": "item_completed",
                "item": {
                    "type": "CommandExecution",
                    "command": ["/bin/bash", "-lc", command],
                    "status": "completed",
                    "exit_code": 0,
                },
            },
        }


if __name__ == "__main__":
    unittest.main()
