"""Manual audits preserve provenance and only checkpoint completed browser work."""
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
import zipfile
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / 'skills/octo-memory/scripts/transcripts.py'
SPEC = importlib.util.spec_from_file_location('memory_transcripts', PATH)
memory = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(memory)


class MemoryTests(unittest.TestCase):
    def setUp(self):
        printer = patch('builtins.print')
        printer.start()
        self.addCleanup(printer.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / 'repo'
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        subprocess.run(['git', '-C', str(self.repo), 'remote', 'add', 'origin',
                        'https://example.test/team/project.git'], check=True)
        self.root, self.remote, key = memory.project(self.repo)
        self.store = self.base / 'global' / key
        self.sessions = self.base / 'sessions'
        self.sessions.mkdir()
        self.now = datetime.now(timezone.utc)

    def row(self, text, days=0, role='user'):
        return {'timestamp': (self.now - timedelta(days=days)).isoformat(),
                'type': 'response_item', 'payload': {'type': 'message', 'role': role,
                'content': [{'type': 'input_text', 'text': text}]}}

    def session(self, name, rows, cwd=None, **meta):
        path = self.sessions / (name + '.jsonl')
        header = {'type': 'session_meta', 'payload': {'id': name, 'cwd': str(cwd or self.repo),
                                                     'thread_source': 'user', **meta}}
        path.write_text('\n'.join(json.dumps(row) for row in [header, *rows]) + '\n')
        return path

    def prepare(self, days=7, **kw):
        output = self.base / ('packet-' + str(len(list(self.base.glob('packet-*')))))
        options = dict(days=days, sessions=self.sessions, max_chars=200000,
            legacy=self.base / 'legacy', output=output, artifact=[], exclude_session=[], prior_report=[])
        options.update(kw)
        args = SimpleNamespace(**options)
        memory.prepare(args, self.root, self.remote, self.store)
        return output

    def finish(self, packet, valid=True):
        m = json.loads((packet / 'manifest.json').read_text())
        run = self.base / 'browser'
        run.mkdir(exist_ok=True)
        response = 'AUDIT_COMPLETE ' + m['marker'] + '\n' + '\n'.join(e['id'] for b in m['sessions'].values() for e in b['events'])
        (run / 'response.md').write_text(response if valid else 'Unread attachment')
        (run / 'run.json').write_text(json.dumps({'phase': 'complete', 'mode': 'analysis',
            'attachments': [str(packet / 'context.md')], 'url': 'https://chatgpt.com/c/example'}))
        (run / 'network.json').write_text(json.dumps({'submitted_models': ['gpt-6-pro']}))
        memory.finish(SimpleNamespace(packet=packet, browser_run=run), self.store)

    def test_one_day_then_week_skips_processed_events_and_keeps_appends(self):
        path = self.session('a', [self.row('recent'), self.row('older', days=3)])
        day = self.prepare(1)
        self.assertEqual([e['text'] for e in json.loads((day / 'manifest.json').read_text())['sessions']['a']['events']], ['recent'])
        self.finish(day)
        self.finish(day)  # Idempotent receipt replay.
        with path.open('a') as f:
            f.write(json.dumps(self.row('appended')) + '\n')
        week = self.prepare()
        events = json.loads((week / 'manifest.json').read_text())['sessions']['a']['events']
        self.assertEqual([e['text'] for e in events], ['older', 'appended'])
        self.finish(week)
        self.assertFalse(self.prepare().exists())

    def test_failed_analysis_does_not_advance_and_pending_run_resumes(self):
        self.session('a', [self.row('remember a constraint')])
        packet = self.prepare()
        with self.assertRaises(ValueError):
            self.finish(packet, valid=False)
        self.assertEqual(json.loads((self.store / 'ledger.json').read_text())['sessions'], {})
        self.assertFalse(self.prepare().exists())
        self.finish(packet)
        self.assertTrue((self.store / 'reports').is_dir())

    def test_audit_subagent_foreign_reasoning_and_duplicate_representations_are_excluded(self):
        row = self.row('user correction')
        mirror = {'type': 'event_msg', 'payload': {'type': 'user_message', 'message': 'user correction'}}
        hidden = self.row('private reasoning', role='assistant')
        hidden['payload']['channel'] = 'analysis'
        self.session('a', [row, row, mirror, hidden, self.row('# AGENTS.md injected')])
        self.session('approval', [self.row('The following is the Codex agent history whose request action you are assessing.')])
        self.session('subagent', [self.row('worker repetition')], source={'subagent': 'parent'})
        self.session('foreign', [self.row('foreign secret')], cwd=self.base / 'other')
        packet = self.prepare()
        m = json.loads((packet / 'manifest.json').read_text())
        self.assertEqual(list(m['sessions']), ['a'])
        self.assertEqual(len(m['sessions']['a']['events']), 1)
        with zipfile.ZipFile(packet / 'artifacts.zip') as archive:
            self.assertEqual(json.loads(archive.read('verification.json'))['marker'], m['marker'])
            self.assertEqual(archive.read('context.md').decode(), (packet / 'context.md').read_text())

    def test_live_partial_json_record_is_eligible_when_completed(self):
        path = self.session('a', [self.row('complete')])
        partial = json.dumps(self.row('late'))
        with path.open('a') as f:
            f.write(partial[:20])
        packet = self.prepare()
        self.finish(packet)
        with path.open('a') as f:
            f.write(partial[20:] + '\n')
        next_packet = self.prepare()
        events = json.loads((next_packet / 'manifest.json').read_text())['sessions']['a']['events']
        self.assertEqual([e['text'] for e in events], ['late'])

    def test_source_replacement_and_copied_file_do_not_repeat_old_events(self):
        path = self.session('a', [self.row('original')])
        packet = self.prepare()
        self.finish(packet)
        (self.sessions / 'copy.jsonl').write_text(path.read_text())
        self.session('a', [self.row('original'), self.row('new correction')])
        packet = self.prepare()
        self.assertEqual([e['text'] for e in json.loads((packet / 'manifest.json').read_text())['sessions']['a']['events']], ['new correction'])

    def test_legacy_import_once_and_global_identity_separates_same_basename(self):
        legacy = self.base / 'legacy' / 'old-day'
        legacy.mkdir(parents=True)
        (legacy / 'capture.md').write_text('An expensive verified decision')
        packet = self.prepare()
        self.finish(packet)
        self.assertFalse(self.prepare().exists())
        self.assertEqual(memory.identity('git@example.test:team/project.git'), self.remote)
        self.assertNotEqual(memory.identity('https://example.test/other/project.git'), self.remote)

    def test_originless_worktrees_share_identity(self):
        subprocess.run(['git', '-C', str(self.repo), 'remote', 'remove', 'origin'], check=True)
        subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=Test',
                        '-c', 'user.email=test@example.invalid', 'commit', '-q',
                        '--allow-empty', '-m', 'fixture'], check=True)
        worktree = self.base / 'worktree'
        subprocess.run(['git', '-C', str(self.repo), 'worktree', 'add', '-q',
                        '-b', 'fixture', str(worktree)], check=True)
        root, remote, key = memory.project(self.repo)
        worktree_root, worktree_remote, worktree_key = memory.project(worktree)
        self.assertEqual((root, remote), (self.repo.resolve(), ''))
        self.assertEqual((worktree_root, worktree_remote), (worktree.resolve(), ''))
        self.assertEqual(worktree_key, key)
        self.assertNotEqual(key, self.store.name)

    def test_budget_and_malformed_sources_are_reported_without_checkpoint(self):
        self.session('a', [self.row('oversized')])
        bad = self.session('bad', [])
        with bad.open('a') as f:
            f.write('invalid json\n')
        args = SimpleNamespace(days=7, sessions=self.sessions, max_chars=1, legacy=self.base / 'legacy',
            output=self.base / 'unused', artifact=[], exclude_session=[], prior_report=[])
        memory.prepare(args, self.root, self.remote, self.store)
        self.assertFalse(args.output.exists())
        self.assertEqual(json.loads((self.store / 'ledger.json').read_text())['sessions'], {})

    def test_secrets_are_redacted_and_artifacts_cannot_escape_repo(self):
        secret = 'sk-' + 'x' * 30
        self.session('a', [self.row('api_key=secretvalue ' + secret)])
        packet = self.prepare()
        text = (packet / 'context.md').read_text()
        self.assertNotIn(secret, text)
        self.assertNotIn('secretvalue', text)
        with self.assertRaises(ValueError):
            memory.artifacts(self.repo, ['../outside.txt'])

    def test_legacy_default_uses_origin_name_in_a_differently_named_checkout(self):
        old = self.base / '.octo-memory/project/short_term/2026-09-01'
        old.mkdir(parents=True)
        (old / 'capture.md').write_text('legacy origin capture')
        with patch.object(memory.Path, 'home', return_value=self.base):
            packet = self.prepare(legacy=None)
        self.assertEqual(len(json.loads((packet / 'manifest.json').read_text())['legacy']), 1)

    def test_audit_session_exclusion_survives_a_later_invocation(self):
        self.session('audit', [self.row('copied audit report')])
        self.session('task', [self.row('actual project discovery')])
        packet = self.prepare(exclude_session=['audit'])
        self.finish(packet)
        self.assertFalse(self.prepare().exists())

    def test_redaction_keeps_source_control_flow_across_newlines(self):
        code = 'if parts.password:\n    return url\n'
        self.assertEqual(memory.redact(code), code)
        self.assertEqual(memory.redact('password = secretvalue'), 'password = [REDACTED]')


if __name__ == '__main__':
    unittest.main()
