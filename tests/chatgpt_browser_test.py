"""Browser helper safety contracts; real UI behavior is exercised separately."""
import importlib.util
import html
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import DEFAULT, MagicMock, Mock, patch

PATH = Path(__file__).resolve().parents[1] / 'skills/octo-chatgpt-images/scripts/browser.py'
SPEC = importlib.util.spec_from_file_location('chatgpt_browser', PATH)
browser = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(browser)


class BrowserDOMTests(unittest.TestCase):
    """Exercise the observer against synthetic DOMs in isolated, offline Chrome."""

    @classmethod
    def setUpClass(cls):
        cls.chrome = (shutil.which('google-chrome') or shutil.which('chromium') or
                      shutil.which('chromium-browser'))
        if not cls.chrome:
            raise unittest.SkipTest('Offline DOM regression checks require Chrome or Chromium')
        cls.workspace = Path(__file__).resolve().parents[1] / '.browser-workspace'
        cls.workspace.mkdir(exist_ok=True)

    def observe_html(self, markup, reader=None):
        def evaluate_fixture(page, body):
            # /tmp has a per-user quota; keep the profile and Chrome's own
            # temporary files in our disposable disk workspace instead.
            with tempfile.TemporaryDirectory(dir=self.workspace) as directory:
                root = Path(directory)
                fixture = root / 'conversation.html'
                fixture.write_text('<!doctype html><meta charset="utf-8">' + markup +
                    '<pre id="result"></pre><script>window.addEventListener("load", async () => {'
                    'try { const result = await (async () => {' + body + '})();'
                    'document.getElementById("result").textContent = JSON.stringify(result);'
                    '} catch(error) { document.getElementById("result").textContent = '
                    'JSON.stringify({error: String(error)}); }});</script>')
                result = subprocess.run([self.chrome, '--headless', '--no-sandbox', '--disable-gpu',
                    '--disable-dev-shm-usage', '--no-first-run', '--no-default-browser-check',
                    '--user-data-dir=' + str(root / 'profile'), '--dump-dom', fixture.as_uri()],
                    capture_output=True, text=True, timeout=30,
                    env={**os.environ, 'TMPDIR': directory})
                self.assertEqual(result.returncode, 0, result.stderr[-2000:])
                output = re.search(r'<pre id="result">(.*?)</pre>', result.stdout, re.S)
                self.assertIsNotNone(output, result.stdout)
                value = json.loads(html.unescape(output[1]))
                if 'error' in value:
                    raise browser.BrowserError(value['error'])
                return value
        with patch.object(browser, 'evaluate', side_effect=evaluate_fixture):
            return (reader or browser.observe)(1)

    def decorated_link(self, url):
        # The observed composer wraps literal URLs with a decorative SVG widget.
        return (f'<span data-rich-text-generated-autolink="" text-link-href="{url}">'
                '<span class="Label-arpLwJ"><span data-inline-url-icon="" '
                'aria-hidden="true" contenteditable="false" style="display:block">'
                '<span class="IconContainer-K62H88" contenteditable="false">'
                '<svg width="20" height="20"><path d="M10 2.125 L10 17.875"></path></svg>'
                f'</span><span class="Label-arpLwJ"></span></span>{url}</span></span>')

    def composer_html(self, content):
        return ('<form><div role="textbox" contenteditable="true" style="white-space:pre-wrap">'
                + content + '</div><button aria-label="Send"></button></form>')

    def rendered_link(self, url):
        return (f'<a data-inline-mention-interactive="" href="{url}" data-search-result-target="">'
                '<span data-layout="inline-flow"><span data-markdown-copy="exclude" '
                'class="IconContainer-K62H88" style="display:block">'
                '<span class="Favicon-xZwQNw"><img alt="" '
                'src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==">'
                f'</span></span><span class="Label-arpLwJ"><span>{url}</span></span></span></a>')

    def test_rendered_favicon_urls_match_exact_sent_prompt(self):
        first = 'https://www.sec.gov/files/form13f.pdf'
        second = 'https://www.sec.gov/rules-regulations/staff-guidance/frequently-asked-questions-about-form-13f'
        prompt = f'Primary sources:\n\nRead {first} and {second}.\nKeep  two spaces\tand a tab.'
        content = ('<p class="Paragraph-kKnbIo" dir="auto"><span>Primary sources:</span><br><br>'
                   '<span>Read </span>' + self.rendered_link(first) + '<span> and </span>' +
                   self.rendered_link(second) + '<span>.</span><br>'
                   '<span>Keep  two spaces\tand a tab.</span></p>')
        observation = self.observe_html('<main><div><h4>You said:</h4>'
            '<div data-user-message-bubble><div data-search-result-target '
            'style="white-space:pre-wrap">' + content + '</div></div></div></main>')
        self.assertEqual(observation['users'], [prompt])
        browser.verify_conversation(dict(mode='analysis', prompt=prompt), observation)
        for changed in (prompt.replace('form13f.pdf', 'form4.pdf'),
                        prompt.replace(first, '\n' + first),
                        prompt.replace('\n\n', '\n', 1),
                        prompt.replace('Keep  two', 'Keep two')):
            with self.subTest(changed=changed), self.assertRaises(browser.BrowserError):
                browser.verify_conversation(dict(mode='analysis', prompt=changed), observation)

    def test_rendered_link_does_not_hide_other_copy_exclusions(self):
        url = 'https://www.sec.gov/files/form13f.pdf'
        content = '<p>Read ' + self.rendered_link(url) + (
            '<span data-markdown-copy="exclude">changed instruction</span></p>')
        observation = self.observe_html('<main><div data-user-message-bubble>'
            '<div data-search-result-target>' + content + '</div></div></main>')
        self.assertIn('changed instruction', observation['users'][0])
        self.assertFalse(browser.prompt_visible(dict(prompt='Read ' + url), observation))

    def test_decorated_composer_urls_keep_literal_text_and_real_breaks(self):
        first = 'https://www.sec.gov/files/form4.pdf'
        second = 'https://www.sec.gov/data-research/sec-markets-data/insider-transactions-data-sets'
        prompt = f'Primary sources:\n\nRead {first} and {second}.\nKeep  two spaces\tand a tab.\n\nEnd.'
        content = ('<p>Primary sources:<br><br>Read ' + self.decorated_link(first) +
                   ' and ' + self.decorated_link(second) +
                   '.<br>Keep  two spaces\tand a tab.<br><br>End.</p>')
        draft = self.observe_html(self.composer_html(content), browser.composer)
        self.assertEqual(draft['text'], prompt)
        browser.verify_draft(draft, prompt, [])
        for changed in (prompt.replace(first, '\n' + first),
                        prompt.replace('\n\n', '\n', 1),
                        prompt.replace('two spaces', 'different words'),
                        prompt.replace('Keep  two', 'Keep two'),
                        prompt.replace('form4.pdf', 'form3.pdf')):
            with self.subTest(changed=changed), self.assertRaises(browser.BrowserError):
                browser.verify_draft(draft, changed, [])

    def test_decorated_sent_prompt_and_research_chip_preserve_block_separators(self):
        url = 'https://www.sec.gov/files/form4.pdf'
        content = '<p>Read ' + self.decorated_link(url) + '</p><p>Keep\nthese lines.</p>'
        prompt = f'Read {url}\n\nKeep\nthese lines.'
        observation = self.observe_html('<main><div><h4>You said:</h4>'
            '<div data-user-message-bubble><div data-search-result-target>'
            '<div>Deep research</div><div dir="auto" style="white-space:pre-wrap">' +
            content + '</div></div><button>Show more</button></div></div></main>')
        self.assertEqual(observation['users'], ['Deep research\n\n' + prompt])
        self.assertTrue(browser.prompt_visible(dict(mode='research', prompt=prompt,
            submitted_prompt='Deep research ' + prompt), observation))
        plain = self.observe_html('<main><div data-user-message-bubble>'
            '<div dir="auto" style="white-space:pre-wrap">' + content + '</div></div></main>')
        self.assertEqual(plain['users'], [prompt])
        self.assertTrue(browser.prompt_visible(dict(prompt=prompt), plain))
        self.assertFalse(browser.prompt_visible(dict(prompt=prompt.replace('\n\n', '\n')), plain))

    def test_decorated_prompt_does_not_hide_unrelated_content(self):
        url = 'https://www.sec.gov/files/form4.pdf'
        content = '<p>Read ' + self.decorated_link(url) + (
            '<span aria-hidden="true" contenteditable="false">changed instruction</span></p>')
        draft = self.observe_html(self.composer_html(content), browser.composer)
        self.assertIn('changed instruction', draft['text'])
        with self.assertRaises(browser.BrowserError):
            browser.verify_draft(draft, 'Read ' + url, [])

    def image(self, label='Generated image 1'):
        return (f'<img alt="{label}" width="2" height="2" '
                'src="data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==">')

    def test_collapsed_prompt_matches_without_show_more_control(self):
        prompt = 'Extract the character.\n\nKeep every important detail.'
        observation = self.observe_html('<main><div><h4>You said:</h4>'
            '<div data-user-message-bubble><div data-search-result-target style="max-height:20px;overflow:hidden">'
            f'<div dir="auto" style="white-space:pre-wrap">{prompt}</div></div>'
            '<button>Show more</button></div></div><div><h4>ChatGPT said:</h4>' +
            self.image() + '<button aria-label="Copy image"></button></div></main>')
        self.assertEqual(observation['users'], [prompt])
        self.assertTrue(browser.prompt_visible(dict(prompt=prompt), observation))
        self.assertTrue(browser.is_finished('images', observation))
        self.assertEqual(len(observation['images']), 1)

    def test_rendered_research_chip_keeps_its_text_and_block_separator(self):
        observation = self.observe_html('<main><div><h4>You said:</h4>'
            '<div data-user-message-bubble><div data-search-result-target>'
            '<div>Deep research</div><div dir="auto">Research this</div></div>'
            '<button>Show more</button></div></div></main>')
        state = dict(mode='research', prompt='Research this',
                     submitted_prompt='Deep research Research this')
        self.assertTrue(browser.prompt_visible(state, observation))

    def test_current_assistant_text_is_collected_without_role_attributes(self):
        observation = self.observe_html('<main><div><h4>You said:</h4>'
            '<div data-user-message-bubble><div dir="auto">Analyze</div></div></div>'
            '<div><h4>ChatGPT said:</h4><p>The completed answer.</p>'
            '<button aria-label="Copy"></button></div></main>')
        self.assertEqual(observation['text'], 'The completed answer.')
        self.assertTrue(browser.is_finished('analysis', observation))

    def math_html(self, tex, mathml='<mi>x</mi>', display=False):
        # B19's clipped MathML duplicates visual tokens in innerText; its radical
        # is an SVG path, so innerText cannot represent the operation.
        markup = ('<span class="katex"><span class="katex-mathml" '
                  'style="position:absolute;clip:rect(1px,1px,1px,1px)">'
                  '<math><semantics>' + mathml +
                  '<annotation encoding="application/x-tex">' + html.escape(tex) +
                  '</annotation></semantics></math></span>'
                  '<span class="katex-html" aria-hidden="true">'
                  '<span>R</span><span class="sqrt"><svg width="10" height="10">'
                  '<path d="M0 5 L3 8 L6 0 L10 0"></path></svg><span>Q</span>'
                  '</span><sup>2</sup></span></span>')
        return '<span class="katex-display" style="display:block">' + markup + '</span>' if display else markup

    def test_assistant_math_keeps_source_radicals_and_repeated_expressions(self):
        tex = r'a_s=(R_s/\sqrt{Q_s})z_s'
        # Exact MathML body captured from TCSS-02, rather than a text radical.
        mathml = ('<mrow><msub><mi>a</mi><mi>s</mi></msub><mo>=</mo>'
                  '<mo stretchy="false">(</mo><msub><mi>R</mi><mi>s</mi></msub>'
                  '<mi mathvariant="normal">/</mi><msqrt><msub><mi>Q</mi><mi>s</mi>'
                  '</msub></msqrt><mo stretchy="false">)</mo>'
                  '<msub><mi>z</mi><mi>s</mi></msub></mrow>')
        formula = self.math_html(tex, mathml)
        observation = self.observe_html('<main><div><h4>ChatGPT said:</h4>'
            '<p>Before RQ2: ' + formula + '; repeat ' + formula + ' after.</p>'
            '<p>Second paragraph.</p><button aria-label="Copy"></button></div></main>')
        self.assertEqual(observation['text'],
            f'Before RQ2: ${tex}$; repeat ${tex}$ after.\n\nSecond paragraph.')
        self.assertTrue(browser.is_finished('analysis', observation))

    def test_assistant_display_math_preserves_fractions_powers_and_layout(self):
        tex = r'\frac{R_s}{\sqrt{Q_s}}+q^2'
        formula = self.math_html(tex, '<mrow><mfrac><mi>R</mi><msqrt><mi>Q</mi>'
            '</msqrt></mfrac><mo>+</mo><msup><mi>q</mi><mn>2</mn></msup></mrow>', display=True)
        inline = self.math_html(r'x^2')
        observation = self.observe_html('<main><div><h4>ChatGPT said:</h4>'
            '<p>Before.</p>' + formula + '<p>After.<br>New line.</p>'
            '<ul><li>First ' + inline + '</li><li>Second.</li></ul>'
            '<table><tr><th>Name</th><th>Score</th></tr><tr><td>A</td><td>' + inline +
            '</td></tr><tr><td>B</td><td>2</td></tr></table>'
            '<pre>keep  two spaces\n next line</pre>'
            '<p style="white-space:pre-line">Start  here\n  ' + inline +
            '\n End.</p></div></main>')
        self.assertEqual(observation['text'], 'Before.\n\n$$' + tex +
            '$$\n\nAfter.\nNew line.\n\nFirst $x^2$\nSecond.\n'
            'Name\tScore\nA\t$x^2$\nB\t2\nkeep  two spaces\n next line\n\n'
            'Start here\n$x^2$\nEnd.')

    def test_assistant_math_skips_hidden_content(self):
        formula = self.math_html(r'x^2')
        observation = self.observe_html('<main><div><h4>ChatGPT said:</h4>'
            '<p>Visible ' + formula + '<span style="display:none">hidden text</span>'
            '<span style="visibility:hidden">secret ' + self.math_html('', '<mi>bad</mi>') +
            '</span> after.</p><div style="display:none">' + self.math_html('') +
            '</div><p style="display:contents">More ' + formula + '.</p></div></main>')
        self.assertEqual(observation['text'], 'Visible $x^2$ after.\n\nMore $x^2$.')

    def test_assistant_math_without_source_annotation_fails_visibly(self):
        for formula in (self.math_html(''), self.math_html('x').replace(
                '<annotation encoding="application/x-tex">x</annotation>', '')):
            with self.subTest(formula=formula), self.assertRaisesRegex(
                    browser.BrowserError, 'Math expression has no TeX annotation'):
                self.observe_html('<main><div><h4>ChatGPT said:</h4><p>' + formula +
                    '</p><button aria-label="Copy"></button></div></main>')

    def test_completion_toolbar_can_follow_the_reply_outside_its_block(self):
        observation = self.observe_html('<main><div><div><h4>ChatGPT said:</h4>' +
            self.image() + '</div><div><button aria-label="Copy image"></button>'
            '</div></div></main>')
        self.assertTrue(browser.is_finished('images', observation))

    def test_old_images_and_completion_do_not_finish_a_new_reply(self):
        for latest in ('<div><h4>You said:</h4><div data-user-message-bubble>Revise</div></div>',
                       '<div><h4>ChatGPT said:</h4><p>Generating...</p></div>'):
            with self.subTest(latest=latest):
                observation = self.observe_html('<main><div><h4>ChatGPT said:</h4>' +
                    self.image() + '<button aria-label="Copy image"></button></div>' + latest +
                    '</main><div role="status">Response complete</div>')
                self.assertEqual(observation['images'], [])
                self.assertFalse(browser.is_finished('images', observation))

    def test_legacy_reply_and_hidden_controls_are_supported(self):
        observation = self.observe_html('<main><div data-message-author-role="user">'
            '<div data-user-message-bubble>Draw</div></div>'
            '<div data-conversation-role="assistant">Done' + self.image() +
            '<button aria-label="Copy"></button></div>'
            '<div data-conversation-role="assistant" style="display:none">Hidden reply</div>'
            '</main><button aria-label="Stop" style="display:none"></button>')
        self.assertEqual(observation['users'], ['Draw'])
        self.assertEqual(observation['text'], 'Done')
        self.assertTrue(browser.is_finished('images', observation))
        streaming = self.observe_html('<main><div><h4>ChatGPT said:</h4>' + self.image() +
            '<button aria-label="Copy image"></button></div></main>'
            '<button aria-label="Stop streaming"></button>')
        self.assertFalse(browser.is_finished('images', streaming))


class BrowserTests(unittest.TestCase):
    def test_research_selection_requires_the_actual_plugin(self):
        proof = [{'name': 'deep-research', 'path': 'app://connector_openai_deep_research',
                  'label': 'Deep research'}]
        browser.validate_research(proof)
        for wrong in ([], [{**proof[0], 'path': 'app://another_plugin'}], proof * 2):
            with self.subTest(proof=wrong), self.assertRaises(browser.BrowserError):
                browser.validate_research(wrong)

    def test_research_draft_preserves_prompt_and_attachment_checks(self):
        for text in ('Deep research Research this', 'Research this\nDeep research'):
            draft = dict(text=text, files=['artifacts.zip'], send=True, busy=False)
            browser.verify_research_draft(draft, 'Research this', ['artifacts.zip'])
            for change in ({'text': 'Deep research A different question'}, {'files': []},
                           {'busy': True}, {'send': False}):
                with self.subTest(change=change), self.assertRaises(browser.BrowserError):
                    browser.verify_research_draft({**draft, **change}, 'Research this', ['artifacts.zip'])

    def test_research_submission_recovers_rendered_plugin_line_break(self):
        state = dict(mode='research', prompt='Research this', submitted_prompt='Deep research Research this')
        observation = dict(users=['Deep research\n Research this'], url='https://chatgpt.com/')
        browser.verify_conversation(state, observation)
        with self.assertRaises(browser.BrowserError):
            browser.verify_conversation(state, {**observation, 'users': ['Deep research Research something else']})

    def test_research_acknowledgment_is_not_a_finished_report(self):
        acknowledgment = dict(streaming=False, complete=True, text='Research has started')
        self.assertFalse(browser.is_finished('research', acknowledgment))
        self.assertFalse(browser.is_finished('research', {**acknowledgment, 'research_complete': False}))
        self.assertTrue(browser.is_finished('research', {**acknowledgment, 'research_complete': True}))
        self.assertFalse(browser.is_finished('research', {
            **acknowledgment, 'research_complete': True, 'streaming': True}))

    def test_research_completion_requires_finished_widget_and_report(self):
        data = dict(status='Research completed in 1m', text='Cited report', buttons=['Export'])
        self.assertTrue(browser.research_finished(data))
        for change in ({'status': 'Researching...'}, {'text': ''}, {'buttons': []},
                       {'buttons': ['Export', 'Stop research']}):
            with self.subTest(change=change):
                self.assertFalse(browser.research_finished({**data, **change}))

    def test_research_clarification_without_widget_needs_input(self):
        acknowledgment = dict(complete=True, streaming=False, text='Which country?')
        with patch.object(browser, 'observe', return_value=acknowledgment), \
                patch.object(browser, 'observe_research', return_value=dict(
                    phase='waiting', complete=False, text='')):
            observation = browser.observe_run(7, 'research')
        self.assertEqual(observation['research']['phase'], 'needs_input')
        self.assertFalse(browser.is_finished('research', observation))

    def test_research_root_is_scoped_to_one_named_iframe(self):
        snapshot = ('uid=1 main\n'
                    '  uid=2 Iframe "Another plugin"\n'
                    '    uid=3 main\n'
                    '  uid=4 Iframe "Deep research"\n'
                    '    uid=5 RootWebArea "sandbox"\n'
                    '      uid=6 Iframe\n'
                    '        uid=7 main\n'
                    '  uid=8 main\n')
        self.assertEqual(browser.research_root_uid(snapshot), '7')
        self.assertIsNone(browser.research_root_uid('uid=1 main\n'))
        self.assertIsNone(browser.research_root_uid('uid=1 Iframe "Deep research"\nuid=2 main\n'))
        with self.assertRaises(browser.BrowserError):
            browser.research_root_uid(snapshot + '  uid=9 Iframe "Deep research"\n    uid=10 main\n')

    def test_upload_accepts_button_description_and_requires_unique_match(self):
        with patch.object(browser, 'click'), patch.object(browser, 'cli') as cli, \
                patch.object(browser, 'composer', return_value={'files': ['context.md']}):
            for label in ('Add photos & files', 'Add photos & files Upload from computer'):
                with self.subTest(label=label):
                    cli.reset_mock()
                    cli.return_value = f'  uid=14_132 button "{label}"\n'
                    browser.upload(15, ['context.md'])
                    cli.assert_any_call('upload_file', 15, '14_132', 'context.md')
            for snapshot in ('uid=1 button "Add photos & filesOther"',
                             'uid=1 link "Add photos & files Upload from computer"',
                             'uid=1 button "Add photos & files"\n'
                             'uid=2 button "Add photos & files Upload from computer"'):
                with self.subTest(snapshot=snapshot):
                    cli.reset_mock()
                    cli.return_value = snapshot
                    with self.assertRaises(browser.BrowserError):
                        browser.upload(15, ['context.md'])
                    self.assertFalse(any(c.args[0] == 'upload_file' for c in cli.call_args_list))

    @patch.object(browser, 'cli', return_value='uid=1 textbox "Ask ChatGPT elsewhere"')
    def test_snapshot_matching_is_exact_by_default(self, cli):
        with self.assertRaises(browser.BrowserError):
            browser.snapshot_uid(15, 'textbox', 'Ask ChatGPT')

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

    def test_completed_upload_timestamp_rename_preserves_draft_verification(self):
        draft = dict(text='Review this', files=['context(20261001-004849).md'],
                     send=True, busy=False)
        browser.verify_draft(draft, 'Review this', ['/project/context.md'])
        for names in (['context(20261001-004849).txt'], ['other(20261001-004849).md'],
                      ['context(arbitrary).md'], ['context(20261001-004849).md', 'secret.env'],
                      ['context(20261001-004849).md', 'context.md']):
            with self.subTest(names=names), self.assertRaises(browser.BrowserError):
                browser.verify_draft({**draft, 'files': names}, 'Review this', ['/project/context.md'])

    @patch.object(browser, 'request_model', return_value='gpt-5-6')
    @patch.object(browser, 'cli')
    def test_network_evidence_removes_queries_and_rejects_codex(self, cli, request_model):
        cli.return_value = ('reqid=1 POST https://chatgpt.com/backend-api/f/conversation [200]\n'
                            'reqid=2 GET https://chatgpt.com/backend-api/estuary/content?token=SECRET [200]')
        run = Path('/owned-run')
        evidence = browser.network_evidence(7, 'images', run=run)
        request_model.assert_called_once_with(7, '1', run=run)
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

    def test_request_model_reads_full_body_instead_of_truncated_inline_preview(self):
        body = json.dumps({'prompt': 'long prompt ' * 1200, 'model': 'gpt-6-pro'})
        self.assertGreater(body.index('"model"'), 10000)
        exports = []
        with tempfile.TemporaryDirectory() as directory:
            run = Path(directory)

            def capture(*args):
                self.assertEqual(args[:4], ('get_network_request', 76, '--reqid', '168'))
                if '--requestFilePath' in args:
                    path = Path(args[args.index('--requestFilePath') + 1])
                    self.assertTrue(path.is_relative_to(run))
                    path.write_text(body)
                    exports.append(path)
                return json.dumps({'networkRequest': {'requestBody': body[:10000] + '... <truncated>'}})

            with patch.object(browser.Path, 'cwd', return_value=run), \
                    patch.object(browser, 'cli', side_effect=capture):
                model = browser.request_model(76, '168')
            self.assertEqual(model, 'gpt-6-pro')
            browser.validate_request_model('analysis', model)
            self.assertEqual(len(exports), 1)
            self.assertFalse(exports[0].exists())
            self.assertEqual(list(run.iterdir()), [])

    def test_request_body_cleanup_preserves_parse_and_capture_failures(self):
        cases = (('{', json.JSONDecodeError, None),
                 ('[]', browser.BrowserError, 'Captured submission body is not a JSON object'),
                 ('{"model":"gpt-6-pro"}', browser.BrowserError, 'receipt export failed'))
        for body, error_type, message in cases:
            with self.subTest(body=body), tempfile.TemporaryDirectory() as directory:
                run = Path(directory)

                def capture(*args):
                    path = Path(args[args.index('--requestFilePath') + 1])
                    path.write_text(body)
                    if message == 'receipt export failed':
                        raise browser.BrowserError(message)
                    return 'inline output is deliberately unusable'

                with patch.object(browser, 'cli', side_effect=capture), \
                        self.assertRaises(error_type) as raised:
                    browser.request_model(76, '168', run=run)
                if message:
                    self.assertEqual(str(raised.exception), message)
                self.assertEqual(list(run.iterdir()), [])

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

    def test_tab_cleanup_closes_unchanged_images_and_analysis(self):
        observation = {'url': 'saved', 'users': ['Draw'], 'complete': True}
        with patch.object(browser, 'observe', return_value=observation) as observe, \
                patch.object(browser, 'composer', return_value=dict(text='', files=[], busy=False)) as composer, \
                patch.object(browser, 'cli') as cli:
            for mode in ('images', 'analysis'):
                state = dict(mode=mode, page=7)
                self.assertEqual(browser.close_completed_tab(state, observation), 'closed')
                cli.assert_called_once_with('close_page', 7)
                cli.reset_mock()
            for draft in (dict(text='Follow up', files=[], busy=False),
                          dict(text='', files=['ref.png'], busy=False),
                          dict(text='', files=[], busy=True)):
                composer.return_value = draft
                self.assertTrue(browser.close_completed_tab(state, observation).startswith('kept:'))
            composer.return_value = dict(text='', files=[], busy=False)
            observe.return_value = {**observation, 'users': ['Draw', 'Follow up']}
            self.assertTrue(browser.close_completed_tab(state, observation).startswith('kept:'))
            cli.assert_not_called()
            observe.return_value = observation
            cli.side_effect = browser.BrowserError('disconnected')
            self.assertEqual(browser.close_completed_tab(state, observation), 'close failed: disconnected')

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
                               download=DEFAULT, save=DEFAULT, close_completed_tab=DEFAULT) as mocks:
            mocks['observe'].return_value = observation
            mocks['network_evidence'].return_value = dict(chatgpt_conversation_request=True)
            mocks['download'].return_value = (b'image data', 'png')
            def close(state, observation):
                self.assertEqual(state['phase'], 'complete')
                mocks['save'].assert_called_once()
                (run / 'image-1.png').write_bytes.assert_called_once_with(b'image data')
                return 'closed'
            mocks['close_completed_tab'].side_effect = close
            browser.collect(args)
            self.assertEqual(mocks['save'].call_args.args[1]['tab'], 'closed')
            mocks['close_completed_tab'].reset_mock()
            mocks['download'].side_effect = browser.BrowserError('download failed')
            with self.assertRaises(browser.BrowserError):
                browser.collect(args)
            mocks['close_completed_tab'].assert_not_called()

    def test_analysis_collection_saves_response_before_closing(self):
        url = 'https://chatgpt.com/c/6ab83f53-4ee8-83ea-b640-29791f4c725a'
        observation = dict(url=url, users=['Analyze'], streaming=False, complete=True,
                           text='Analysis result')
        run = MagicMock()
        paths = {}
        run.__truediv__.side_effect = lambda name: paths.setdefault(name, MagicMock())
        (run / 'run.json').read_text.return_value = json.dumps(
            dict(phase='submitted', mode='analysis', prompt='Analyze', page=7, url=url))
        args = SimpleNamespace(run=Mock())
        args.run.resolve.return_value = run
        with patch.object(browser.fcntl, 'flock'), patch('builtins.print'), \
                patch.multiple(browser, observe=DEFAULT, network_evidence=DEFAULT,
                               save=DEFAULT, close_completed_tab=DEFAULT) as mocks:
            mocks['observe'].return_value = observation
            mocks['network_evidence'].return_value = dict(chatgpt_conversation_request=True)

            def close(state, observation):
                (run / 'response.md').write_text.assert_called_once_with('Analysis result\n')
                mocks['save'].assert_called_once()
                self.assertEqual(state['url'], url)
                self.assertEqual(state['phase'], 'complete')
                return 'closed'

            mocks['close_completed_tab'].side_effect = close
            browser.collect(args)
            self.assertEqual(mocks['save'].call_args.args[1]['tab'], 'closed')

    def test_research_collection_saves_report_and_sources_before_closing(self):
        url = 'https://chatgpt.com/c/6ab83f53-4ee8-83ea-b640-29791f4c725a'
        observation = dict(url=url, users=['Deep research\n Research this'], streaming=False,
                           complete=True, text='Research started')
        sources = [dict(title='Official source', url='https://example.com/source')]
        research = dict(phase='complete', complete=True, text='Final research report', links=sources)
        run = MagicMock()
        paths = {}
        run.__truediv__.side_effect = lambda name: paths.setdefault(name, MagicMock())
        (run / 'run.json').read_text.return_value = json.dumps(dict(
            phase='sending', mode='research', prompt='Research this',
            submitted_prompt='Deep research Research this', page=7, url=None))
        args = SimpleNamespace(run=Mock())
        args.run.resolve.return_value = run
        with patch.object(browser.fcntl, 'flock'), patch('builtins.print'), \
                patch.multiple(browser, observe=DEFAULT, observe_research=DEFAULT,
                               network_evidence=DEFAULT, save=DEFAULT, close_completed_tab=DEFAULT) as mocks:
            mocks['observe'].return_value = observation
            mocks['observe_research'].return_value = research
            mocks['network_evidence'].return_value = dict(chatgpt_conversation_request=True)

            def close(state, observation):
                content = (run / 'response.md').write_text.call_args.args[0]
                self.assertIn('Final research report', content)
                self.assertIn('[Official source](https://example.com/source)', content)
                self.assertIn(url, content)
                self.assertNotIn('Research started', content)
                self.assertEqual(json.loads((run / 'sources.json').write_text.call_args.args[0]), sources)
                self.assertEqual(state['phase'], 'complete')
                mocks['save'].assert_called_once()
                return 'closed'

            mocks['close_completed_tab'].side_effect = close
            browser.collect(args)
            self.assertEqual(mocks['save'].call_args.args[1]['tab'], 'closed')

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
