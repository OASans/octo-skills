import json
from pathlib import Path
import tempfile
import unittest

from install_vscode_config import merge_settings, read_settings


class SettingsTests(unittest.TestCase):
    def test_jsonc_and_empty_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text('// settings\n/* comment */')
            self.assertEqual(read_settings(path), {})
            path.write_text('{"url":"https://example.com/*x*/,}", // comment\n"enabled":true,}')
            self.assertEqual(read_settings(path), {
                "url": "https://example.com/*x*/,}", "enabled": True})

    def test_preserves_preferences_and_allowlist_and_is_repeatable(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text(json.dumps({
                "theme": "dark", "files.watcherExclude": {"custom": True},
                "extensions.allowed": {"*": False, "allowed.extension": True,
                                       "ms-python.python": True}}))
            managed = {"extensions.allowed": {"*": True, "ms-python.python": False},
                       "files.watcherExclude": {"**/target/**": True}}
            merge_settings(path, managed)
            settings = read_settings(path)
            self.assertEqual(settings["theme"], "dark")
            self.assertEqual(settings["extensions.allowed"], {
                "*": False, "allowed.extension": True, "ms-python.python": False})
            self.assertEqual(settings["files.watcherExclude"], {
                "custom": True, "**/target/**": True})
            before = path.stat().st_mtime_ns
            merge_settings(path, managed)
            self.assertEqual(path.stat().st_mtime_ns, before)


if __name__ == "__main__":
    unittest.main()
