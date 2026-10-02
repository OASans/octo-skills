"""Browser helper safety contracts; real UI behavior is exercised separately."""
from contextlib import contextmanager
import importlib.util
import html
import hashlib
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

    def test_citation_hrefs_are_scoped_to_the_current_assistant_and_exact_context(self):
        url = 'https://www.federalreserve.gov/paper.pdf?edition=1&format=pdf#page=2'
        formula = self.math_html(r'\sqrt{Q_s}')
        markup = ('<main><div><h4>You said:</h4><div data-user-message-bubble>'
                  '<a href="https://example.org/user">Analyze</a></div></div>'
                  '<div><h4>ChatGPT said:</h4><a href="https://example.org/old">Old answer</a></div>'
                  '<div><h4>ChatGPT said:</h4><p>Before <a href="' + html.escape(url) +
                  '">Ross paper ' + formula + '</a> after.</p>'
                  '<a style="display:none" href="https://example.org/hidden">Hidden</a>'
                  '<p>Unlinked https://example.org/unlinked</p><button aria-label="Copy"></button>'
                  '</div></main><a href="https://example.org/sidebar">Sidebar</a>')
        current = self.observe_html(markup)
        self.assertEqual(current['citations'],
                         [{'url': url, 'context_quote': r'Ross paper $\sqrt{Q_s}$'}])
        self.assertIn(current['citations'][0]['context_quote'], current['text'])
        legacy = self.observe_html(markup, lambda page: browser.observe(page, legacy=True))
        self.assertEqual([row['url'] for row in legacy['citations']], [url])
        self.assertIn(legacy['citations'][0]['context_quote'], legacy['text'])
        self.assertNotEqual(current['text'], legacy['text'])

    def test_citation_observation_is_bounded(self):
        links = ''.join(f'<a href="https://example.org/{i}">Source {i}</a>' for i in range(257))
        with self.assertRaisesRegex(browser.BrowserError, 'more than 256 citation links'):
            self.observe_html('<main><div><h4>ChatGPT said:</h4>' + links + '</div></main>')

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


class CitationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = Path(__file__).resolve().parents[1] / '.browser-workspace'
        cls.workspace.mkdir(exist_ok=True)

    def archive(self, directory, text='Ross paper and its proposal.'):
        run = Path(directory)
        state = dict(mode='analysis', phase='complete', prompt='Analyze', page=7,
                     url='https://chatgpt.com/c/6ab83f53-4ee8-83ea-b640-29791f4c725a', tab='closed')
        (run / 'run.json').write_text(json.dumps(state) + '\n')
        (run / 'response.md').write_text(text + '\n')
        (run / 'network.json').write_text(json.dumps(dict(chatgpt_conversation_request=True,
            codex_requests=0, submitted_models=['gpt-6-pro'])) + '\n')
        (run / 'collect.lock').touch()
        observation = dict(url=state['url'], users=['Analyze'], text=text, streaming=False,
                           complete=True, citations=[dict(url='https://www.federalreserve.gov/paper.pdf',
                           context_quote='Ross paper')])
        return run, state, observation

    def banked_bytes(self, run):
        return {name: (run / name).read_bytes() for name in ('run.json', 'response.md', 'network.json')}

    def test_sidecar_hashes_final_metadata_and_exact_response_without_rewriting(self):
        with tempfile.TemporaryDirectory(dir=self.workspace) as directory:
            run, state, observation = self.archive(directory)
            banked = self.banked_bytes(run)
            receipt = browser.save_citations(run, observation, '2026-10-02T01:00:00Z')
            data = (run / receipt['file']).read_bytes()
            payload = json.loads(data)
            self.assertEqual(payload['run_sha256'], hashlib.sha256(banked['run.json']).hexdigest())
            self.assertEqual(payload['response_sha256'], hashlib.sha256(banked['response.md']).hexdigest())
            self.assertEqual(payload['observed_response_sha256'], payload['response_sha256'])
            self.assertEqual(payload['conversation_url'], state['url'])
            self.assertEqual(payload['citations'], observation['citations'])
            self.assertEqual(receipt['sha256'], hashlib.sha256(data).hexdigest())
            self.assertEqual(browser.save_citations(run, observation, '2026-10-03T01:00:00Z'), receipt)
            self.assertEqual((run / receipt['file']).read_bytes(), data)
            self.assertEqual(self.banked_bytes(run), banked)
            self.assertFalse(list(run.glob('.browser-citations-*')))
            changed = {**observation, 'citations': [dict(url='https://example.org/different',
                                                       context_quote='Ross paper')]}
            with self.assertRaisesRegex(browser.BrowserError, 'different observed links'):
                browser.save_citations(run, changed, '2026-10-03T01:00:00Z')
            self.assertEqual((run / receipt['file']).read_bytes(), data)

    def test_bad_observations_never_publish_or_modify_the_archive(self):
        with tempfile.TemporaryDirectory(dir=self.workspace) as directory:
            run, _, observation = self.archive(directory)
            banked = self.banked_bytes(run)
            cases = [dict(text='Different reply'), dict(url='https://example.org/foreign'),
                     dict(citations=[]), dict(citations=[observation['citations'][0]] * 257),
                     dict(citations=[dict(url='https://example.org/paper', context_quote='Invented quote')]),
                     dict(citations=[dict(url='file:///local', context_quote='Ross paper')]),
                     dict(citations=[dict(url='https://example.org/paper', context_quote=' ')])]
            for changed in cases:
                with self.subTest(changed=changed), self.assertRaises(browser.BrowserError):
                    browser.save_citations(run, {**observation, **changed}, '2026-10-02T01:00:00Z')
                self.assertFalse((run / 'source_citations.json').exists())
                self.assertEqual(self.banked_bytes(run), banked)

    def test_sidecar_limits_and_unsafe_existing_evidence_fail(self):
        with tempfile.TemporaryDirectory(dir=self.workspace) as directory:
            run, _, observation = self.archive(directory)
            oversized = [dict(url='https://example.org/' + ('x' * 3000) + str(i),
                              context_quote='Ross paper') for i in range(256)]
            with self.assertRaisesRegex(browser.BrowserError, 'exceeds 512 KiB'):
                browser.save_citations(run, {**observation, 'citations': oversized}, '2026-10-02T01:00:00Z')
            path = run / 'source_citations.json'
            path.symlink_to(run / 'response.md')
            with self.assertRaisesRegex(browser.BrowserError, 'regular file'):
                browser.save_citations(run, observation, '2026-10-02T01:00:00Z')
            path.unlink()
            browser.save_citations(run, observation, '2026-10-02T01:00:00Z')
            state = json.loads((run / 'run.json').read_bytes())
            state['tab'] = 'changed metadata'
            (run / 'run.json').write_text(json.dumps(state) + '\n')
            with self.assertRaisesRegex(browser.BrowserError, 'immutable run and response'):
                browser.capture_citations(SimpleNamespace(run=run))

    def capture_mocks(self, state):
        def command(*args):
            if args == ('new_page', state['url']):
                return '100: Saved conversation (' + state['url'] + ') [selected]'
            if args == ('close_page', 100):
                return 'Owned page closed'
            raise AssertionError('Unexpected browser operation: ' + repr(args))
        return command

    def test_completed_capture_and_replay_preserve_original_files_and_only_close_owned_tab(self):
        with tempfile.TemporaryDirectory(dir=self.workspace) as directory:
            run, state, observation = self.archive(directory)
            banked = self.banked_bytes(run)
            with patch.object(browser, 'cli', side_effect=self.capture_mocks(state)) as cli, \
                    patch.object(browser, 'evaluate', return_value=state['url']), \
                    patch.object(browser, 'observe', return_value=observation), \
                    patch.object(browser, 'composer', return_value=dict(text='', files=[], busy=False)), \
                    patch('builtins.print'):
                browser.capture_citations(SimpleNamespace(run=run))
            self.assertEqual([call.args[0] for call in cli.call_args_list], ['new_page', 'close_page'])
            self.assertEqual(cli.call_args_list[-1].args, ('close_page', 100))
            self.assertEqual(self.banked_bytes(run), banked)
            data = (run / 'source_citations.json').read_bytes()
            with patch.object(browser, 'cli') as cli, patch('builtins.print'):
                browser.capture_citations(SimpleNamespace(run=run))
            cli.assert_not_called()
            self.assertEqual((run / 'source_citations.json').read_bytes(), data)
            self.assertEqual(self.banked_bytes(run), banked)

    def test_legacy_capture_requires_exact_original_bytes(self):
        with tempfile.TemporaryDirectory(dir=self.workspace) as directory:
            run, state, legacy = self.archive(directory, 'Ross paper: R\nQ.')
            current = {**legacy, 'text': r'Ross paper: $R/\sqrt Q$.'}
            with patch.object(browser, 'cli', side_effect=self.capture_mocks(state)), \
                    patch.object(browser, 'evaluate', return_value=state['url']), \
                    patch.object(browser, 'observe', side_effect=[current, legacy, legacy]) as observe, \
                    patch.object(browser, 'composer', return_value=dict(text='', files=[], busy=False)), \
                    patch('builtins.print'):
                browser.capture_citations(SimpleNamespace(run=run))
            observe.assert_any_call(100, legacy=True)
            self.assertEqual(observe.call_args_list[-1].kwargs, {'legacy': True})
            payload = json.loads((run / 'source_citations.json').read_bytes())
            self.assertEqual(payload['observed_response_sha256'], hashlib.sha256(
                (legacy['text'] + '\n').encode()).hexdigest())
            self.assertEqual((run / 'response.md').read_bytes(), (legacy['text'] + '\n').encode())

    def test_capture_refuses_mismatch_wrong_prompt_incomplete_or_absent_actual_links(self):
        changes = [dict(text='Changed reply'), dict(users=['Wrong prompt']),
                   dict(complete=False), dict(citations=[])]
        for changed in changes:
            with self.subTest(changed=changed), tempfile.TemporaryDirectory(dir=self.workspace) as directory:
                run, state, observation = self.archive(directory)
                banked = self.banked_bytes(run)
                with patch.object(browser, 'cli', side_effect=self.capture_mocks(state)) as cli, \
                        patch.object(browser, 'evaluate', return_value=state['url']), \
                        patch.object(browser, 'observe', return_value={**observation, **changed}), \
                        patch.object(browser, 'composer', return_value=dict(text='', files=[], busy=False)), \
                        self.assertRaises(browser.BrowserError):
                    browser.capture_citations(SimpleNamespace(run=run))
                expected = ['new_page', 'close_page'] if changed == dict(citations=[]) else ['new_page']
                self.assertEqual([call.args[0] for call in cli.call_args_list], expected)
                self.assertFalse((run / 'source_citations.json').exists())
                self.assertEqual(self.banked_bytes(run), banked)

    def test_capture_preserves_a_changed_tab_and_rejects_unverified_original_receipt(self):
        with tempfile.TemporaryDirectory(dir=self.workspace) as directory:
            run, state, observation = self.archive(directory)
            with patch.object(browser, 'cli', side_effect=self.capture_mocks(state)) as cli, \
                    patch.object(browser, 'evaluate', return_value=True), \
                    patch.object(browser, 'observe', side_effect=[observation,
                        {**observation, 'url': 'https://example.org/changed'}]), \
                    patch.object(browser, 'composer', return_value=dict(text='', files=[], busy=False)), \
                    self.assertRaisesRegex(browser.BrowserError, 'tab changed'):
                browser.capture_citations(SimpleNamespace(run=run))
            self.assertEqual([call.args[0] for call in cli.call_args_list], ['new_page'])
            self.assertFalse((run / 'source_citations.json').exists())
            (run / 'network.json').write_text(json.dumps(dict(chatgpt_conversation_request=True,
                codex_requests=0, submitted_models=['gpt-5-6'])))
            with patch.object(browser, 'cli') as cli, self.assertRaisesRegex(
                    browser.BrowserError, 'verified GPT-6 Pro'):
                browser.capture_citations(SimpleNamespace(run=run))
            cli.assert_not_called()

    def test_capture_preserves_same_url_drafts_attachments_busy_and_followup(self):
        clean = dict(text='', files=[], busy=False)
        cases = [(dict(text='User draft', files=[], busy=False), None),
                 (dict(text='', files=['user-file.pdf'], busy=False), None),
                 (dict(text='', files=[], busy=True), None),
                 (clean, dict(users=['Analyze', 'User follow-up'])),
                 (clean, dict(users=['Analyze', 'User follow-up'], text='', complete=False))]
        for draft, changed in cases:
            with self.subTest(draft=draft, changed=changed), tempfile.TemporaryDirectory(dir=self.workspace) as directory:
                run, state, observation = self.archive(directory)
                banked = self.banked_bytes(run)
                later = {**observation, **(changed or {})}
                self.assertEqual(later['url'], observation['url'])
                with patch.object(browser, 'cli', side_effect=self.capture_mocks(state)) as cli, \
                        patch.object(browser, 'evaluate', return_value=state['url']), \
                        patch.object(browser, 'observe', side_effect=[observation, later]), \
                        patch.object(browser, 'composer', return_value=draft), \
                        patch('builtins.print') as printed, \
                        self.assertRaisesRegex(browser.BrowserError, 'tab changed'):
                    browser.capture_citations(SimpleNamespace(run=run))
                self.assertEqual([call.args[0] for call in cli.call_args_list], ['new_page'])
                printed.assert_not_called()
                self.assertFalse((run / 'source_citations.json').exists())
                self.assertEqual(self.banked_bytes(run), banked)

    def test_future_collect_binds_sidecar_after_final_run_save_without_hash_cycle(self):
        for linked in (True, False):
            with self.subTest(linked=linked), tempfile.TemporaryDirectory(dir=self.workspace) as directory:
                run, state, observation = self.archive(directory)
                state['phase'] = 'submitted'
                (run / 'run.json').write_text(json.dumps(state))
                if not linked:
                    observation['citations'] = []
                with patch.object(browser, 'observe', return_value=observation), \
                        patch.object(browser, 'network_evidence', return_value=dict(chatgpt_conversation_request=True,
                            codex_requests=0, submitted_models=['gpt-6-pro'])), \
                        patch.object(browser, 'close_completed_tab', return_value='closed'), \
                        patch('builtins.print') as printed:
                    browser.collect(SimpleNamespace(run=run))
                self.assertEqual((run / 'response.md').read_bytes(), (observation['text'] + '\n').encode())
                final = json.loads((run / 'run.json').read_bytes())
                self.assertEqual(final['tab'], 'closed')
                result = json.loads(printed.call_args.args[0])
                path = run / 'source_citations.json'
                self.assertEqual(path.exists(), linked)
                if linked:
                    payload = json.loads(path.read_bytes())
                    self.assertEqual(payload['run_sha256'], hashlib.sha256((run / 'run.json').read_bytes()).hexdigest())
                    self.assertEqual(final['artifacts'][-1], {'file': 'source_citations.json'})
                    self.assertEqual(result['artifacts'][-1]['sha256'], hashlib.sha256(path.read_bytes()).hexdigest())


class CleanupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.workspace = Path(__file__).resolve().parents[1] / '.browser-workspace'
        cls.workspace.mkdir(exist_ok=True)

    def archive(self, directory):
        run = Path(directory)
        text = (r'Use \(R=D-L\) for cash. \[ D=\text{cash deposited},\qquad L=2. \]'
                '\nHistorical XML\n.')
        state = dict(mode='analysis', phase='complete', prompt='Analyze', page=108,
                     url='https://chatgpt.com/c/6ab83f53-4ee8-83ea-b640-29791f4c725a',
                     chat_mode='Chat', model=dict(value='4', text='6\nPro'),
                     tab='kept: tab changed after collection')
        evidence = dict(chatgpt_conversation_request=True, codex_requests=0,
                        submitted_models=['gpt-6-pro'], requests=[dict(method='POST',
                        path='/backend-api/f/conversation', status='200')])
        (run / 'run.json').write_text(json.dumps(state) + '\n')
        (run / 'response.md').write_text(text + '\n')
        (run / 'network.json').write_text(json.dumps(evidence) + '\n')
        (run / 'collect.lock').touch()
        observation = dict(url=state['url'], users=['Analyze'],
            text=r'Use $R=D-L$ for cash. $$D=\text{cash deposited},\qquad' +
                 '\nL=2.$$\nHistorical XML.', streaming=False, complete=True, citations=[])
        # Bank an actual citation sidecar to detect accidental metadata changes.
        linked = dict(url='https://example.org/source', context_quote='Historical XML')
        browser.save_citations(run, dict(observation, text=text, citations=[linked]),
                               '2026-10-02T01:00:00Z')
        return run, state, evidence, observation

    def banked_bytes(self, run):
        return {name: (run / name).read_bytes() for name in
                ('run.json', 'response.md', 'network.json', 'source_citations.json')}

    @contextmanager
    def browser_mocks(self, state, evidence, observation):
        with patch.multiple(browser, require_browser_daemon=DEFAULT, cli=DEFAULT,
                            observe=DEFAULT, composer=DEFAULT, network_evidence=DEFAULT) as mocks, \
                patch('builtins.print'):
            def command(*args):
                if args == ('list_pages',):
                    return str(state['page']) + ': ChatGPT (' + state['url'] + ')'
                if args == ('close_page', state['page']):
                    return 'Owned page closed'
                raise AssertionError('Unexpected browser operation: ' + repr(args))
            mocks['cli'].side_effect = command
            mocks['observe'].return_value = observation
            mocks['composer'].return_value = dict(text='', files=[], busy=False)
            mocks['network_evidence'].return_value = evidence
            yield mocks

    def test_hydration_keeps_words_numbers_currency_and_math_boundaries(self):
        equal = [(r'\(R=D-L\)', '$R=D-L$'),
                 (r'\[ 1 + 2 \]\[\text{cash deposited}\]', '$$1+2$$\n\n$$\\text{cash deposited}$$'),
                 ('Historical XML\n.', 'Historical XML.'),
                 ('Keep\nthese  words.', 'Keep these words.')]
        different = [('not able', 'notable'), ('1 0', '10'),
                     ('Keep these words.', 'Keep those words.'),
                     (r'\(R=2\)', '$R=3$'), (r'\[x\]', '$x$'),
                     ('$10', '10'), ('$10 and $20', '10 and 20'),
                     ('$10 and $20', r'\(10 and \)20'), ('$10$', r'\(10\)'),
                     ('$-10 and $20', r'\(-10 and \)20'),
                     ('$USD 10 and $EUR 20', r'\(USD 10 and \)EUR 20'),
                     (r'\(price=\$10\)', '$price=10$'),
                     (r'\(\text{not able}\)', r'$\text{notable}$'),
                     (r'\[x\]\[y\]', '$$xy$$')]
        for original, current in equal:
            with self.subTest(original=original, current=current):
                self.assertTrue(browser.hydration_equivalent(original, current))
        for original, current in different:
            with self.subTest(original=original, current=current):
                self.assertFalse(browser.hydration_equivalent(original, current))

    def test_cleanup_closes_only_original_page_preserves_archive_and_replays_offline(self):
        with tempfile.TemporaryDirectory(dir=self.workspace) as directory:
            run, state, evidence, observation = self.archive(directory)
            banked = self.banked_bytes(run)
            with self.browser_mocks(state, evidence, observation) as mocks:
                browser.cleanup_completed(SimpleNamespace(run=run))
            self.assertEqual([call.args for call in mocks['cli'].call_args_list],
                             [('list_pages',), ('close_page', 108)])
            self.assertEqual(mocks['observe'].call_count, 2)
            mocks['network_evidence'].assert_called_once_with(108, 'analysis', run=run)
            path = run / 'tab_cleanup.json'
            receipt_bytes = path.read_bytes()
            self.assertEqual(json.loads(receipt_bytes), dict(version=1,
                run_sha256=hashlib.sha256(banked['run.json']).hexdigest(),
                response_sha256=hashlib.sha256(banked['response.md']).hexdigest(),
                conversation_url=state['url'], page=108, tab='closed'))
            with patch.object(browser, 'cli') as cli, \
                    patch.object(browser, 'require_browser_daemon') as daemon, \
                    patch.object(browser.sys, 'argv', ['browser.py', 'cleanup-completed', '--run', str(run)]), \
                    patch('builtins.print'):
                self.assertEqual(browser.main(), 0)
            cli.assert_not_called()
            daemon.assert_not_called()
            self.assertEqual(path.read_bytes(), receipt_bytes)
            self.assertEqual(self.banked_bytes(run), banked)
            self.assertFalse(list(run.glob('.browser-cleanup-*')))
            # Existing citation authentication still succeeds against original bytes.
            browser.existing_citations(run, state, banked['response.md'],
                                       hashlib.sha256(banked['run.json']).hexdigest())

    def test_cleanup_refuses_changed_reply_prompt_followup_completion_or_ownership(self):
        changes = [dict(text='Changed words'), dict(text=r'Use $R=D-L$ for cash. $$D=\text{cash deposited},\qquad L=3.$$\nHistorical XML.'),
                   dict(users=['Wrong prompt']), dict(users=['Analyze', 'Follow up']),
                   dict(complete=False), dict(streaming=True), dict(text=''),
                   dict(url='https://chatgpt.com/c/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa')]
        for changed in changes:
            with self.subTest(changed=changed), tempfile.TemporaryDirectory(dir=self.workspace) as directory:
                run, state, evidence, observation = self.archive(directory)
                banked = self.banked_bytes(run)
                with self.browser_mocks(state, evidence, {**observation, **changed}) as mocks, \
                        self.assertRaises(browser.BrowserError):
                    browser.cleanup_completed(SimpleNamespace(run=run))
                self.assertNotIn(('close_page', 108), [call.args for call in mocks['cli'].call_args_list])
                self.assertFalse((run / 'tab_cleanup.json').exists())
                self.assertEqual(self.banked_bytes(run), banked)
        with tempfile.TemporaryDirectory(dir=self.workspace) as directory:
            run, state, evidence, observation = self.archive(directory)
            with self.browser_mocks(state, evidence, observation) as mocks:
                mocks['cli'].side_effect = None
                mocks['cli'].return_value = '109: Other page (' + state['url'] + ')'
                with self.assertRaisesRegex(browser.BrowserError, 'original owned page'):
                    browser.cleanup_completed(SimpleNamespace(run=run))
            mocks['observe'].assert_not_called()
            self.assertFalse((run / 'tab_cleanup.json').exists())

    def test_cleanup_preserves_drafts_uploads_and_concurrently_changed_tabs(self):
        cases = [(dict(text='Draft', files=[], busy=False), None),
                 (dict(text='', files=['user.pdf'], busy=False), None),
                 (dict(text='', files=[], busy=True), None),
                 (None, dict(text='Changed after verification')),
                 (None, dict(users=['Analyze', 'Follow up']))]
        for draft, later in cases:
            with self.subTest(draft=draft, later=later), tempfile.TemporaryDirectory(dir=self.workspace) as directory:
                run, state, evidence, observation = self.archive(directory)
                banked = self.banked_bytes(run)
                with self.browser_mocks(state, evidence, observation) as mocks:
                    if draft:
                        mocks['composer'].return_value = draft
                    if later:
                        mocks['observe'].side_effect = [observation, {**observation, **later}]
                    with self.assertRaises(browser.BrowserError):
                        browser.cleanup_completed(SimpleNamespace(run=run))
                self.assertNotIn(('close_page', 108), [call.args for call in mocks['cli'].call_args_list])
                self.assertFalse((run / 'tab_cleanup.json').exists())
                self.assertEqual(self.banked_bytes(run), banked)

    def test_cleanup_refuses_unproven_or_extra_original_and_current_submissions(self):
        for origin in ('original', 'current'):
            for change in ('extra', 'failed_extra', 'codex', 'model', 'absent', 'different_path'):
                with self.subTest(origin=origin, change=change), tempfile.TemporaryDirectory(dir=self.workspace) as directory:
                    run, state, evidence, observation = self.archive(directory)
                    changed = json.loads(json.dumps(evidence))
                    if change in ('extra', 'failed_extra'):
                        changed['requests'].append(dict(method='POST', path='/backend-api/f/conversation',
                                                        status='200' if change == 'extra' else 'pending'))
                    elif change == 'codex':
                        changed['requests'].append(dict(method='GET', path='/backend-api/codex/tasks', status='200'))
                    elif change == 'model':
                        changed['submitted_models'] = ['gpt-6']
                    elif change == 'absent':
                        changed.pop('requests')
                    else:
                        changed['requests'][0]['path'] = '/backend-api/conversation'
                    if origin == 'original':
                        (run / 'network.json').write_text(json.dumps(changed))
                        # Different valid original endpoint is allowed if current matches.
                        if change == 'different_path':
                            evidence = changed
                    banked = self.banked_bytes(run)
                    with self.browser_mocks(state, evidence, observation) as mocks:
                        if origin == 'current':
                            mocks['network_evidence'].return_value = changed
                        if origin == 'original' and change == 'different_path':
                            browser.cleanup_completed(SimpleNamespace(run=run))
                        else:
                            with self.assertRaises(browser.BrowserError):
                                browser.cleanup_completed(SimpleNamespace(run=run))
                            self.assertFalse((run / 'tab_cleanup.json').exists())
                            self.assertNotIn(('close_page', 108), [call.args for call in mocks['cli'].call_args_list])
                    self.assertEqual(self.banked_bytes(run), banked)

    def test_cleanup_rejects_invalid_archive_and_symlink_files_before_browser_access(self):
        for changed in (dict(phase='submitted'), dict(mode='images'), dict(page=True),
                        dict(page='108'), dict(url='https://example.org'), dict(prompt=''),
                        dict(model=dict(value='0', text='Instant')), dict(chat_mode='Work'),
                        dict(submitted_prompt='Different'), dict(tab='closed')):
            with self.subTest(changed=changed), tempfile.TemporaryDirectory(dir=self.workspace) as directory:
                run, state, _, _ = self.archive(directory)
                (run / 'run.json').write_text(json.dumps({**state, **changed}))
                with patch.object(browser, 'cli') as cli, self.assertRaises(browser.BrowserError):
                    browser.cleanup_completed(SimpleNamespace(run=run))
                cli.assert_not_called()
                self.assertFalse((run / 'tab_cleanup.json').exists())
        for name in ('run.json', 'response.md', 'network.json', 'source_citations.json', 'collect.lock'):
            with self.subTest(name=name), tempfile.TemporaryDirectory(dir=self.workspace) as directory:
                run, _, _, _ = self.archive(directory)
                path = run / name
                target = run / 'owned-original'
                path.rename(target)
                path.symlink_to(target)
                with patch.object(browser, 'cli') as cli, self.assertRaisesRegex(browser.BrowserError, 'regular'):
                    browser.cleanup_completed(SimpleNamespace(run=run))
                cli.assert_not_called()
                self.assertFalse((run / 'tab_cleanup.json').exists())

    def test_cleanup_receipts_refuse_conflict_malformed_oversized_or_symlink(self):
        for change in ('run_hash', 'response_hash', 'page', 'url', 'tab', 'extra', 'bool', 'malformed', 'oversized', 'symlink'):
            with self.subTest(change=change), tempfile.TemporaryDirectory(dir=self.workspace) as directory:
                run, state, evidence, observation = self.archive(directory)
                with self.browser_mocks(state, evidence, observation):
                    browser.cleanup_completed(SimpleNamespace(run=run))
                path = run / 'tab_cleanup.json'
                payload = json.loads(path.read_bytes())
                key = dict(run_hash='run_sha256', response_hash='response_sha256', page='page',
                           url='conversation_url', tab='tab', extra='extra', bool='version').get(change)
                if key:
                    payload[key] = True if change == 'bool' else 'conflict'
                    path.write_text(json.dumps(payload))
                elif change == 'malformed':
                    path.write_text('{')
                elif change == 'oversized':
                    path.write_text(' ' * (browser.MAX_CLEANUP_BYTES + 1))
                else:
                    target = run / 'receipt-original'
                    path.rename(target)
                    path.symlink_to(target)
                existing = path.read_bytes()
                banked = self.banked_bytes(run)
                with patch.object(browser, 'cli') as cli, \
                        patch.object(browser, 'require_browser_daemon') as daemon, \
                        self.assertRaises((browser.BrowserError, ValueError)):
                    browser.cleanup_completed(SimpleNamespace(run=run))
                cli.assert_not_called()
                daemon.assert_not_called()
                self.assertEqual(path.read_bytes(), existing)
                self.assertEqual(self.banked_bytes(run), banked)

    def test_cleanup_failure_or_archive_change_never_writes_closed_receipt(self):
        for change in ('close_failure', 'archive_change'):
            with self.subTest(change=change), tempfile.TemporaryDirectory(dir=self.workspace) as directory:
                run, state, evidence, observation = self.archive(directory)
                banked = self.banked_bytes(run)
                with self.browser_mocks(state, evidence, observation) as mocks:
                    command = mocks['cli'].side_effect
                    def changed_command(*args):
                        if args[0] == 'close_page':
                            if change == 'close_failure':
                                raise browser.BrowserError('Disconnected')
                            (run / 'network.json').write_bytes(banked['network.json'] + b' ')
                        return command(*args)
                    mocks['cli'].side_effect = changed_command
                    with self.assertRaisesRegex(browser.BrowserError, 'no receipt written'):
                        browser.cleanup_completed(SimpleNamespace(run=run))
                self.assertFalse((run / 'tab_cleanup.json').exists())
                for name, data in banked.items():
                    if name != 'network.json' or change == 'close_failure':
                        self.assertEqual((run / name).read_bytes(), data)


if __name__ == '__main__':
    unittest.main()
