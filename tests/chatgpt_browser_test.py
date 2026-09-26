"""Browser helper safety contracts; real UI behavior is exercised separately."""
import importlib.util
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
import unittest
from unittest.mock import DEFAULT, MagicMock, Mock, patch

PATH = Path(__file__).resolve().parents[1] / 'skills/octo-chatgpt-images/scripts/browser.py'
SPEC = importlib.util.spec_from_file_location('chatgpt_browser', PATH)
browser = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(browser)


class BrowserTests(unittest.TestCase):
    def test_images_accept_instant_only(self):
        browser.validate_model('images', {'text': 'Instant\nInstant, 1 of 5.', 'value': '0'})
        for proof in ({'text': '6\nPro', 'value': '4'},
                      {'text': 'Instant', 'value': '4'},
                      {'text': 'Thinking', 'value': '0'}, {}):
            with self.subTest(proof=proof), self.assertRaises(browser.BrowserError):
                browser.validate_model('images', proof)

    def test_analysis_rejects_wrong_generation_and_effort(self):
        browser.validate_model('analysis', {'text': '6\nPro\nPro, 5 of 5.', 'value': '4'})
        for text, value in [('5.5\nPro', '4'), ('6\nThinking', '4'), ('6\nPro', '0'),
                            ('16\nPro', '4'), ('GPT-6 Sol\nPro', '4'), ('', None)]:
            with self.subTest(text=text), self.assertRaises(browser.BrowserError):
                browser.validate_model('analysis', {'text': text, 'value': value})

    def test_draft_must_match_and_uploads_must_finish(self):
        good = {'text': 'Review this', 'files': ['context.md'], 'send': True, 'busy': False}
        browser.verify_draft(good, 'Review this\n', ['/project/context.md'])
        for change in ({'text': 'Old draft'}, {'busy': True}, {'send': False}, {'files': []}):
            with self.subTest(change=change), self.assertRaises(browser.BrowserError):
                browser.verify_draft({**good, **change}, 'Review this', ['/project/context.md'])

    def test_partial_response_and_preview_are_not_complete(self):
        observation = {'streaming': False, 'complete': True, 'images': [{'alt': 'Generated image 1'}],
                       'text': 'Answer'}
        self.assertTrue(browser.is_finished('images', observation))
        self.assertTrue(browser.is_finished('analysis', observation))
        for mode in ('images', 'analysis'):
            self.assertFalse(browser.is_finished(mode, {**observation, 'streaming': True}))
            self.assertFalse(browser.is_finished(mode, {**observation, 'complete': False}))
        self.assertFalse(browser.is_finished('images', {**observation, 'images': []}))
        self.assertFalse(browser.is_finished('analysis', {**observation, 'text': ''}))

    def test_attachment_names_in_prompt_do_not_count_as_uploads(self):
        with self.assertRaises(browser.BrowserError):
            browser.verify_draft({'text': 'Read context.md', 'form': 'Read context.md',
                                  'files': [], 'send': True}, 'Read context.md', ['context.md'])
        self.assertTrue(browser.attachments_match(['context.md'], ['context(1).md']))
        self.assertFalse(browser.attachments_match(['context.md'], ['other-context.md']))
        self.assertFalse(browser.attachments_match(['context.md'], ['context.md', 'secret.env']))
        self.assertFalse(browser.attachments_match([], ['secret.env']))

    @patch.object(browser, 'request_model', return_value='gpt-5-6')
    @patch.object(browser, 'cli')
    def test_network_evidence_removes_queries_and_rejects_codex(self, cli, request_model):
        cli.return_value = ('reqid=1 POST https://chatgpt.com/backend-api/f/conversation [200]\n'
                            'reqid=2 GET https://chatgpt.com/backend-api/estuary/content?token=SECRET [200]')
        evidence = browser.network_evidence(7, 'images')
        self.assertTrue(evidence['chatgpt_conversation_request'])
        self.assertNotIn('SECRET', json.dumps(evidence))
        cli.return_value += '\nreqid=3 POST https://chatgpt.com/backend-api/codex/responses [200]'
        with self.assertRaises(browser.BrowserError):
            browser.network_evidence(7, 'images')

    @patch.object(browser, 'cli')
    def test_failed_or_absent_submission_is_not_verified(self, cli):
        for response in ('No requests', 'reqid=1 POST https://chatgpt.com/backend-api/f/conversation [429]',
                         'reqid=1 GET https://chatgpt.com/backend-api/f/conversation [200]'):
            cli.return_value = response
            self.assertFalse(browser.network_evidence(1, 'images')['chatgpt_conversation_request'])

    def test_actual_request_model_must_match_policy(self):
        browser.validate_request_model('images', 'gpt-5-6')
        browser.validate_request_model('analysis', 'gpt-6-pro')
        for mode, model in [('images', 'gpt-6-pro'), ('analysis', 'gpt-5-6'),
                            ('analysis', 'gpt-5-pro'), ('images', None)]:
            with self.subTest(mode=mode, model=model), self.assertRaises(browser.BrowserError):
                browser.validate_request_model(mode, model)

    def test_optimistic_url_can_settle_but_wrong_conversation_cannot(self):
        url = 'https://chatgpt.com/c/6ab83f53-4ee8-83ea-b640-29791f4c725a'
        obs = {'url': url, 'users': ['Review']}
        browser.verify_conversation({'prompt': 'Review', 'url': None}, obs)
        browser.verify_conversation({'prompt': 'Review', 'url': 'https://chatgpt.com/c/local-chatgpt%3Aid'}, obs)
        with self.assertRaises(browser.BrowserError):
            browser.verify_conversation({'prompt': 'Different', 'url': url}, obs)
        with self.assertRaises(browser.BrowserError):
            browser.verify_conversation({'prompt': 'Review', 'url': url}, {**obs, 'url': 'https://example.com'})

    @patch.object(browser, 'cli')
    @patch.object(browser, 'evaluate', return_value=True)
    @patch.object(browser, 'click')
    @patch.object(browser, 'model_proof', return_value={})
    def test_model_selection_uses_supported_arrow_controls(self, proof, click, evaluate, cli):
        for mode, direction in [('images', 'ArrowLeft'), ('analysis', 'ArrowRight')]:
            cli.reset_mock()
            browser.select_model(1, mode)
            keys = [call.args[2] for call in cli.call_args_list if call.args[0] == 'press_key']
            self.assertEqual(keys.count(direction), 4)
            self.assertNotIn('End', keys)
            self.assertNotIn('Home', keys)

    @patch.object(browser, 'cli')
    def test_no_implicit_browser_launch(self, cli):
        for status in ('daemon is not running', 'args=["--headless"]', 'args=["--browser-url=http://remote"]'):
            cli.return_value = status
            with self.assertRaises(browser.BrowserError):
                browser.require_browser_daemon()
        cli.return_value = 'args=["--viaCli", "--auto-connect"]'
        browser.require_browser_daemon()

    @patch.object(browser.subprocess, 'run')
    def test_cli_preserves_arguments_without_shell(self, run):
        run.return_value = subprocess.CompletedProcess([], 0, 'Successfully filled', '')
        prompt = 'literal `command` and $(expression)\nsecond line'
        browser.cli('fill', 9, 'uid', prompt)
        self.assertEqual(run.call_args.args[0][-1], prompt)
        self.assertFalse(run.call_args.kwargs.get('shell', False))

    @patch.object(browser.subprocess, 'run')
    def test_cli_errors_are_failures_even_with_zero_exit(self, run):
        for code, output in [(1, ''), (0, 'Could not connect to Chrome'), (0, 'Error: disconnected')]:
            run.return_value = subprocess.CompletedProcess([], code, output, '')
            with self.assertRaises(browser.BrowserError):
                browser.cli('list_pages')

    @patch.object(browser, 'cli')
    def test_evaluation_errors_do_not_parse_as_success(self, cli):
        cli.return_value = 'Required control missing'
        with self.assertRaises(browser.BrowserError):
            browser.evaluate(1, 'return true;')

    @patch.object(browser, 'evaluate')
    def test_download_rejects_html_instead_of_image(self, evaluate):
        evaluate.return_value = {'type': 'text/html', 'data': 'data:text/html;base64,PGh0bWw+'}
        with self.assertRaises(browser.BrowserError):
            browser.download(1, 'https://chatgpt.com/file')

    def test_send_timeout_preserves_uncertainty_and_never_retries(self):
        args = SimpleNamespace(prompt=Mock(), attach=[], mode='images')
        args.prompt.read_text.return_value = 'Draw a cat'
        run = MagicMock()
        saved = []
        with patch.multiple(browser, cli=DEFAULT, save=DEFAULT, wait_until=DEFAULT,
                            evaluate=DEFAULT, composer=DEFAULT, select_model=DEFAULT,
                            model_proof=DEFAULT, snapshot_uid=DEFAULT, click=DEFAULT) as mocks:
            mocks['cli'].return_value = '1: ChatGPT (https://chatgpt.com/) [selected]'
            mocks['composer'].side_effect = [dict(text='', files=[]), dict(text='Draw a cat', send=True, busy=False, form='')]
            mocks['select_model'].return_value = {'text': 'Instant', 'value': '0'}
            mocks['model_proof'].return_value = {'text': 'Instant', 'value': '0'}
            mocks['save'].side_effect = lambda _, state: saved.append(dict(state))
            mocks['wait_until'].side_effect = [True, True, browser.BrowserError('connection lost')]
            with self.assertRaises(browser.BrowserError):
                browser.submit(args, run)
            mocks['click'].assert_called_once_with(1, 'button[aria-label="Send"]')
            self.assertEqual(saved[-2]['phase'], 'sending')
            self.assertEqual(saved[-1]['phase'], 'sending')
            self.assertIn('connection lost', saved[-1]['error'])

    def test_wrong_model_cannot_reach_send(self):
        args = SimpleNamespace(prompt=Mock(), attach=[], mode='analysis')
        args.prompt.read_text.return_value = 'Review'
        with patch.multiple(browser, cli=DEFAULT, save=DEFAULT, wait_until=DEFAULT,
                            evaluate=DEFAULT, composer=DEFAULT, select_model=DEFAULT, click=DEFAULT) as mocks:
            mocks['cli'].return_value = '1: ChatGPT (https://chatgpt.com/) [selected]'
            mocks['composer'].return_value = {'text': '', 'files': []}
            mocks['select_model'].side_effect = browser.BrowserError('Pro unavailable')
            with self.assertRaises(browser.BrowserError):
                browser.submit(args, MagicMock())
            mocks['click'].assert_not_called()

    def test_tab_cleanup_only_closes_unchanged_images(self):
        observation = {'url': 'saved', 'users': ['Draw'], 'complete': True}
        with patch.object(browser, 'observe', return_value=observation) as observe, \
                patch.object(browser, 'composer', return_value=dict(text='', files=[], busy=False)) as composer, \
                patch.object(browser, 'cli') as cli:
            self.assertEqual(browser.close_image_tab(dict(mode='analysis'), observation), 'kept')
            observe.assert_not_called()
            state = dict(mode='images', page=7)
            self.assertEqual(browser.close_image_tab(state, observation), 'closed')
            cli.assert_called_once_with('close_page', 7)
            cli.reset_mock()
            for draft in (dict(text='Follow up', files=[], busy=False),
                          dict(text='', files=['ref.png'], busy=False),
                          dict(text='', files=[], busy=True)):
                composer.return_value = draft
                self.assertTrue(browser.close_image_tab(state, observation).startswith('kept:'))
            composer.return_value = dict(text='', files=[], busy=False)
            observe.return_value = {**observation, 'users': ['Draw', 'Follow up']}
            self.assertTrue(browser.close_image_tab(state, observation).startswith('kept:'))
            cli.assert_not_called()
            observe.return_value = observation
            cli.side_effect = browser.BrowserError('disconnected')
            self.assertEqual(browser.close_image_tab(state, observation), 'close failed: disconnected')

    def test_collection_saves_before_cleanup_and_preserves_tab_on_failure(self):
        url = 'https://chatgpt.com/c/6ab83f53-4ee8-83ea-b640-29791f4c725a'
        observation = dict(url=url, users=['Draw'], streaming=False, complete=True,
                           images=[dict(src='image', width=2, height=2)])
        run = MagicMock()
        (run / 'image-1.png').name = 'image-1.png'
        (run / 'run.json').read_text.return_value = json.dumps(
            dict(phase='submitted', mode='images', prompt='Draw', page=7, url=url))
        args = SimpleNamespace(run=Mock())
        args.run.resolve.return_value = run
        with patch.object(browser.fcntl, 'flock'), patch('builtins.print'), \
                patch.multiple(browser, observe=DEFAULT, network_evidence=DEFAULT,
                               download=DEFAULT, save=DEFAULT, close_image_tab=DEFAULT) as mocks:
            mocks['observe'].return_value = observation
            mocks['network_evidence'].return_value = dict(chatgpt_conversation_request=True)
            mocks['download'].return_value = (b'image data', 'png')
            def close(state, observation):
                self.assertEqual(state['phase'], 'complete')
                mocks['save'].assert_called_once()
                (run / 'image-1.png').write_bytes.assert_called_once_with(b'image data')
                return 'closed'
            mocks['close_image_tab'].side_effect = close
            browser.collect(args)
            self.assertEqual(mocks['save'].call_args.args[1]['tab'], 'closed')
            mocks['close_image_tab'].reset_mock()
            mocks['download'].side_effect = browser.BrowserError('download failed')
            with self.assertRaises(browser.BrowserError):
                browser.collect(args)
            mocks['close_image_tab'].assert_not_called()

    def test_collect_completed_run_does_not_touch_browser_or_resend(self):
        run = MagicMock()
        (run / 'run.json').read_text.return_value = json.dumps({'phase': 'complete', 'url': 'saved'})
        args = SimpleNamespace(run=Mock())
        args.run.resolve.return_value = run
        with patch.object(browser.fcntl, 'flock'), patch.object(browser, 'cli') as cli, patch('builtins.print'):
            browser.collect(args)
        cli.assert_not_called()


if __name__ == '__main__':
    unittest.main()
