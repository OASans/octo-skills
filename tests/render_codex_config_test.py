import importlib.util
from pathlib import Path
import unittest

SPEC = importlib.util.spec_from_file_location(
    "renderer", Path(__file__).resolve().parents[1] / "scripts/render_codex_config.py"
)
renderer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(renderer)


class RenderConfigTest(unittest.TestCase):
    def test_preserves_host_trust_and_replaces_model_defaults(self):
        local = '''model = "old-model"
[projects."/Users/someone/My Project"]
trust_level = "trusted"
[projects."/home/another/project"]
trust_level = "untrusted"
[hooks.state."/Users/someone/.codex/hooks.json:session_start:0:0"]
trusted_hash = "sha256:abc"
enabled = false
'''
        source = 'model = "gpt-6-astra"\nmodel_reasoning_effort = "medium"\n'
        actual = renderer.tomllib.loads(renderer.render_config(source, local))
        old = renderer.tomllib.loads(local)
        self.assertEqual(actual["projects"], old["projects"])
        self.assertEqual(actual["hooks"], old["hooks"])
        self.assertEqual(actual["model"], "gpt-6-astra")
        self.assertEqual(actual["model_reasoning_effort"], "medium")

    def test_fresh_install_does_not_invent_trust(self):
        source = 'model = "gpt-6-astra"\n'
        self.assertEqual(renderer.render_config(source, ""), source)

    def test_idempotent_with_quoted_paths_and_inline_trust(self):
        source = 'model = "gpt-6-astra"\n'
        local = '''projects = { 'C:\\Users\\a"b😀' = { trust_level = "trusted" } }
'''
        first = renderer.render_config(source, local)
        self.assertEqual(renderer.render_config(source, first), first)
        self.assertEqual(renderer.tomllib.loads(first)["projects"], renderer.tomllib.loads(local)["projects"])

    def test_rejects_invalid_local_config(self):
        with self.assertRaises(ValueError):
            renderer.render_config('model = "new"', "[invalid")

    def test_rejects_machine_trust_in_managed_source(self):
        with self.assertRaises(ValueError):
            renderer.render_config('[projects."/some/host"]\ntrust_level = "trusted"', "")


if __name__ == "__main__":
    unittest.main()
