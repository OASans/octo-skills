"""Weekly quota selection and honest handling of unavailable usage."""

import unittest
from unittest.mock import patch

from check_usage import main, weekly_summary


def window(used, minutes=10080):
    return {'usedPercent': used, 'windowDurationMins': minutes, 'resetsAt': None}


class WeeklyUsageTest(unittest.TestCase):
    def test_weekly_primary(self):
        summary = weekly_summary({'rateLimits': {'primary': window(30)}})
        self.assertIn('70% remaining (30% used)', summary)
        self.assertIn('Resets: unavailable', summary)

    def test_secondary_weekly_and_codex_bucket(self):
        summary = weekly_summary({
            'rateLimits': {'primary': window(99)},
            'rateLimitsByLimitId': {
                'base_model_inference': {'primary': window(0)},
                'codex': {'primary': window(80, 300), 'secondary': window(12.5)},
            },
        })
        self.assertIn('87.5% remaining (12.5% used)', summary)

    def test_does_not_infer_weekly_from_other_quota(self):
        for response in (
            {'rateLimits': {'primary': window(20, 300)}},
            {'rateLimits': {'limitId': 'base_model_inference', 'primary': window(0)}},
            {},
        ):
            with self.subTest(response=response), self.assertRaises(ValueError):
                weekly_summary(response)

    def test_invalid_percentage_is_not_reported_as_capacity(self):
        for used in (None, True, '30', -1, 101, float('nan')):
            with self.subTest(used=used), self.assertRaises(ValueError):
                weekly_summary({'rateLimits': {'primary': window(used)}})

    def test_reset_includes_date_and_timezone(self):
        quota = window(100)
        quota['resetsAt'] = 1791586648
        summary = weekly_summary({'rateLimits': {'primary': quota}})
        self.assertIn('0% remaining (100% used)', summary)
        self.assertRegex(summary, r'Resets: 2026-10-\d{2} .* \(UTC[+-]\d{4}\)')

    def test_reads_only_usage_and_honors_codex_home(self):
        with patch.dict('os.environ', {'CODEX_HOME': '/example/codex'}), \
                patch('check_usage.AppServer') as client, \
                patch('builtins.print') as output:
            client.return_value.call.return_value = {'rateLimits': {'primary': window(30)}}
            self.assertEqual(main(), 0)
            self.assertEqual(str(client.call_args.args[0]),
                             '/example/codex/app-server-control/app-server-control.sock')
            client.return_value.call.assert_called_once_with('account/rateLimits/read', {})
            client.return_value.close.assert_called_once()
            self.assertIn('70% remaining', output.call_args.args[0])


if __name__ == '__main__':
    unittest.main()
