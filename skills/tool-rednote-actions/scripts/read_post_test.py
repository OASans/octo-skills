"""RedNote retrieval contracts; HTTP is mocked and real links are tested separately."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import Mock


ROOT = Path.cwd()
PATH = Path(__file__).with_name('read_post.py')
SPEC = importlib.util.spec_from_file_location('rednote_reader', PATH)
reader = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reader)
NOTE_ID = '6a0f01840000000008001e78'
OTHER_ID = '6a0f01840000000008001e79'
POST_URL = f'https://www.xiaohongshu.com/discovery/item/{NOTE_ID}?xsec_token=keep%3D'
PNG = b'\x89PNG\r\n\x1a\n' + b'fixture'


def note(**changes):
    return {'noteId': NOTE_ID, 'title': 'A post', 'desc': 'Full caption',
            'user': {'nickName': 'Author'}, 'imageList': [], **changes}


def html(state):
    return '<script>window.__INITIAL_STATE__=' + json.dumps(state) + ';</script>'


def response(**changes):
    return Mock(**{'url': POST_URL, 'text': '', 'content': PNG,
                   'headers': {'Content-Type': 'image/png'}, **changes})


class RedNoteTests(unittest.TestCase):
    def test_share_text_and_query_are_preserved(self):
        url = 'https://xhslink.cn/o/abc?xsec_token=keep%3D&xsec_source=app_share'
        self.assertEqual(reader.shared_url(f'标题 {url}\n复制打开【小红书】'), url)
        self.assertEqual(reader.shared_url(POST_URL), POST_URL)
        self.assertEqual(reader.shared_url('https://xhslink.com/abc。'), 'https://xhslink.com/abc')

    def test_unrelated_urls_and_bare_ids_are_rejected(self):
        for text in [NOTE_ID, 'https://xhslink.cn.attacker.example/abc',
                     'https://user:secret@xhslink.cn/abc', 'file:///etc/passwd']:
            with self.subTest(text=text), self.assertRaises(reader.ReadError):
                reader.shared_url(text)

    def test_login_redirect_does_not_count_as_a_post(self):
        self.assertEqual(reader.post_id(POST_URL), NOTE_ID)
        with self.assertRaises(reader.ReadError):
            reader.post_id('https://www.xiaohongshu.com/login?redirectPath=' + POST_URL)

    def test_requested_note_is_selected_among_other_records(self):
        content = html({'note': {'noteDetailMap': {
            OTHER_ID: {'note': note(noteId=OTHER_ID, desc='Wrong caption')},
            NOTE_ID: {'note': note()}}}})
        self.assertEqual(reader.parse_note(content, NOTE_ID)['desc'], 'Full caption')

    def test_undefined_and_empty_map_are_data_but_quoted_words_are_preserved(self):
        content = html({'note': {'noteDetailMap': {NOTE_ID: {'note': note(
            desc='Keep undefined and new Map([]) exactly', extra=None)}}}})
        content = content.replace('"extra": null', '"extra": undefined, "map": new Map([])')
        parsed = reader.parse_note(content, NOTE_ID)
        self.assertEqual(parsed['desc'], 'Keep undefined and new Map([]) exactly')
        self.assertIsNone(parsed['extra'])
        self.assertEqual(parsed['map'], [])

    def test_mobile_note_and_image_only_caption(self):
        content = html({'noteData': {'data': {'noteData': note(desc='')}}})
        self.assertEqual(reader.parse_note(content, NOTE_ID)['desc'], '')

    def test_missing_wrong_or_incomplete_note_is_rejected(self):
        for state in [{}, {'noteData': {'data': {'noteData': note(noteId=OTHER_ID)}}},
                      {'noteData': {'data': {'noteData': note(desc=None)}}}]:
            with self.subTest(state=state), self.assertRaises(reader.ReadError):
                reader.parse_note(html(state), NOTE_ID)
        with self.assertRaises(reader.ReadError):
            reader.parse_note('<script>window.__INITIAL_STATE__=alert("no");</script>', NOTE_ID)

    def test_media_url_keeps_query_and_transforms(self):
        url = '//sns-webpic.xhscdn.com/file!nd_dft_wlteh_webp_3?token=keep'
        self.assertEqual(reader.image_url({'urlDefault': url}), 'https:' + url)
        self.assertEqual(reader.image_url({'infoList': [{'url': 'https://cdn.example/a'}]}),
                         'https://cdn.example/a')
        with self.assertRaises(reader.ReadError):
            reader.image_url({'url': 'file:///etc/passwd'})

    def test_non_image_and_unknown_bytes_are_rejected(self):
        self.assertEqual(reader.image_extension(PNG, 'image/png'), 'png')
        self.assertEqual(reader.image_extension(b'RIFFxxxxWEBP', 'image/webp'), 'webp')
        for data, mime in [(PNG, 'text/html'), (b'<html>login</html>', 'image/png')]:
            with self.subTest(mime=mime), self.assertRaises(reader.ReadError):
                reader.image_extension(data, mime)

    def test_network_failure_is_reported_at_the_http_boundary(self):
        session = Mock()
        session.get.side_effect = RuntimeError('connection timed out')
        with self.assertRaisesRegex(reader.ReadError, 'HTTP request failed: connection timed out'):
            reader.request_response(session, POST_URL)

    def test_partial_gallery_retains_caption_and_valid_images(self):
        images = [{'urlDefault': 'https://cdn.example/first'},
                  {'urlDefault': 'https://cdn.example/second'}]
        session = Mock()
        session.get.side_effect = [
            response(text=html({'note': {'noteDetailMap': {NOTE_ID: {'note': note(imageList=images)}}}})),
            response(), response(content=b'<html>blocked</html>', headers={'Content-Type': 'text/html'})]
        workspace = ROOT / '.rednote-workspace'
        workspace.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=workspace) as temp:
            output = Path(temp) / 'post'
            result = reader.read_post(session, POST_URL, output)
            self.assertEqual(result['status'], 'partial')
            self.assertEqual(result['body'], 'Full caption')
            self.assertEqual(result['author'], 'Author')
            self.assertEqual((result['image_count'], result['downloaded_count']), (2, 1))
            self.assertEqual(Path(result['images'][0]['path']).read_bytes(), PNG)
            self.assertIn('error', result['images'][1])
            self.assertEqual(json.loads((output / 'note.json').read_text()), result)
            session.get.assert_any_call('https://cdn.example/first', headers={'Referer': POST_URL})

    def test_ascii_locale_cli_integration(self):
        code = r'''
import runpy, sys
from types import SimpleNamespace
from unittest.mock import Mock, patch
test = runpy.run_path(sys.argv[1])
reader = test['reader']
note = test['note'](desc="\u62fc\u8c46\u6559\u7a0b")
state = {'note': {'noteDetailMap': {test['NOTE_ID']: {'note': note}}}}
session = Mock()
session.get.return_value = test['response'](text=test['html'](state))
context = Mock()
context.__enter__ = Mock(return_value=session)
context.__exit__ = Mock(return_value=False)
requests = SimpleNamespace(Session=lambda **kwargs: context)
argv = ['read_post', test['POST_URL'], '--output', sys.argv[2]]
with patch.dict(sys.modules, {'curl_cffi.requests': requests}), patch.object(sys, 'argv', argv):
    sys.exit(reader.main())
'''
        workspace = ROOT / '.rednote-workspace'
        workspace.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=workspace) as temp:
            output = Path(temp) / 'post'
            result = subprocess.run(
                [sys.executable, '-c', code, str(Path(__file__).resolve()), str(output)],
                cwd=ROOT, capture_output=True, timeout=20,
                env={**os.environ, 'LC_ALL': 'C', 'PYTHONUTF8': '0', 'PYTHONCOERCECLOCALE': '0'},
            )
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            saved = json.loads((output / 'note.json').read_text(encoding='utf-8'))
            returned = json.loads(result.stdout.decode('utf-8'))
            self.assertEqual(saved['body'], '拼豆教程')
            self.assertEqual(returned, saved)


if __name__ == '__main__':
    unittest.main()
