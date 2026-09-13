"""Check that skill entrypoints can route to their packaged resources."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


class SkillContractTest(unittest.TestCase):
    def test_skill_identity_and_reference_links(self):
        for base in (ROOT / 'skills', ROOT / '.claude/skills'):
            for skill in base.glob('*/SKILL.md'):
                with self.subTest(skill=skill.parent.name):
                    text = skill.read_text()
                    front, body = text.split('---', 2)[1:]
                    name = re.search(r'^name: (.+)$', front, re.M)
                    self.assertIsNotNone(name)
                    self.assertEqual(name.group(1).strip(), skill.parent.name)
                    self.assertRegex(front, r'(?m)^description:')
                    for target in re.findall(r'\]\((references/[^)#]+)(?:#[^)]*)?\)', body):
                        self.assertTrue((skill.parent / target).is_file(), target)

    def test_explicit_only_skills_have_codex_policy(self):
        for skill in (ROOT / 'skills').glob('*/SKILL.md'):
            front = skill.read_text().split('---', 2)[1]
            if re.search(r'^disable-model-invocation: true$', front, re.M):
                policy = skill.parent / 'agents/openai.yaml'
                with self.subTest(skill=skill.parent.name):
                    self.assertTrue(policy.is_file())
                    self.assertRegex(policy.read_text(), r'policy:\s*\n\s+allow_implicit_invocation: false\s*\n')

    def test_blueprint_documented_examples_have_their_headings(self):
        knowledge = ROOT / '.claude/skills/knowledge-octo-blueprint/SKILL.md'
        entries = knowledge.read_text().split('## Key Files', 1)[1]
        examples = 0
        for line in entries.splitlines():
            headings = re.findall(r'`(### [^`]+)`', line)
            if headings:
                source = ROOT / re.search(r'`([^`]+)`', line).group(1)
                text = source.read_text()
                for heading in headings:
                    self.assertIn(heading, text.splitlines())
                    examples += 1
        self.assertGreater(examples, 0)

    def test_scenario_answers_use_distinct_valid_choices(self):
        import json
        cases = json.loads((ROOT / 'evals/cases.json').read_text())
        self.assertEqual(len({case['id'] for case in cases}), len(cases))
        for case in cases:
            self.assertTrue(set(case['expected']) <= set(case['choices']))
            self.assertEqual(len(set(case['expected'])), len(case['expected']))


if __name__ == '__main__':
    unittest.main()
