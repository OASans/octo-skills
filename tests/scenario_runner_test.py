import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location('runner', Path(__file__).resolve().parents[1] / 'evals/run_scenarios.py')
runner = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(runner)


class ScenarioRunnerTest(unittest.TestCase):
    def setUp(self):
        self.cases = [{'id': 'case', 'task': 'task', 'choices': ['yes', 'no'], 'expected': ['yes']}]

    def test_scores_completed_wrong_answers_as_failures(self):
        scored = runner.score_answer([{'id': 'case', 'actions': ['no']}], self.cases)
        self.assertFalse(scored[0]['passed'])

    def test_rejects_missing_duplicate_and_unknown_answers(self):
        for answer in [[], [{'id': 'unknown', 'actions': []}],
                       [{'id': 'case', 'actions': ['yes']}] * 2]:
            with self.subTest(answer=answer), self.assertRaises(ValueError):
                runner.score_answer(answer, self.cases)

    def test_rejects_invalid_and_duplicate_actions(self):
        for actions in [['unknown'], ['yes', 'yes']]:
            with self.subTest(actions=actions), self.assertRaises(ValueError):
                runner.score_answer([{'id': 'case', 'actions': actions}], self.cases)

    def test_keeps_expected_answers_out_of_prompt(self):
        prompt = runner.make_prompt('fixture instructions', self.cases)
        self.assertNotIn('expected', prompt)
        self.assertIn('fixture instructions', prompt)
        self.assertIn('"choices": ["yes", "no"]', prompt)

    def test_manifest_policy_inputs_exist(self):
        for name in runner.SUITE['policy_files']:
            self.assertTrue((runner.ROOT / name).is_file())

    def test_baseline_uses_its_own_manifest_after_policy_rename(self):
        with patch.object(runner.subprocess, 'check_output', side_effect=[
                '{"policy_files": ["old-policy.md"]}', 'original instructions']) as read:
            self.assertEqual(runner.read_package('old'), 'old-policy.md\noriginal instructions')
        self.assertEqual([call.args[0] for call in read.call_args_list], [
            ['git', 'show', 'old:evals/suite.json'],
            ['git', 'show', 'old:old-policy.md'],
        ])


if __name__ == '__main__':
    unittest.main()
