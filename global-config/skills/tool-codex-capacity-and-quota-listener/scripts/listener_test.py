"""Recovery contracts and the daemon's Unix WebSocket boundary."""

import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import socket
import struct
import sys
import tempfile
import threading
import unittest

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('capacity_listener', SCRIPTS / 'listener.py')
listener = importlib.util.module_from_spec(spec)
spec.loader.exec_module(listener)
from app_server import AppServer, RpcError


def failed(turn_id='original', code='serverOverloaded'):
    return {'id': turn_id, 'status': 'failed', 'completedAt': 100,
            'error': {'codexErrorInfo': code, 'message': 'Selected model is at capacity.'}}


def metadata(thread_id, cwd='/project', status='idle'):
    return {'id': thread_id, 'cwd': cwd, 'status': {'type': status},
            'canAcceptDirectInput': True, 'parentThreadId': None}


class FakeRpc:
    def __init__(self):
        self.threads = {'target': metadata('target'), 'host': metadata('host', '/skills')}
        self.turns = {'target': failed(), 'host': {'id': 'host-turn', 'status': 'completed'}}
        self.goals = {}
        self.calls = []
        self.starts = []
        self.send_error = False
        self.used = 20
        self.reset = 10000

    def call(self, method, params):
        self.calls.append((method, copy.deepcopy(params)))
        thread_id = params.get('threadId')
        if method == 'account/rateLimits/read':
            return {'rateLimits': {'limitId': 'codex', 'secondary': {
                'windowDurationMins': 10080, 'usedPercent': self.used, 'resetsAt': self.reset}}}
        if method == 'thread/read':
            return {'thread': copy.deepcopy(self.threads[thread_id])}
        if method == 'thread/turns/list':
            return {'data': [copy.deepcopy(self.turns[thread_id])]}
        if method == 'thread/goal/get':
            return {'goal': self.goals.get(thread_id)}
        if method == 'thread/loaded/list':
            if params.get('cursor') == 'second-page':
                return {'data': ['target'], 'nextCursor': None}
            return {'data': [k for k in self.threads if k != 'target'], 'nextCursor': 'second-page'}
        if method == 'turn/start':
            self.starts.append(copy.deepcopy(params))
            if self.send_error and thread_id == 'target':
                raise RpcError('reply lost')
            turn = {'id': f'retry-{len(self.starts)}', 'status': 'inProgress'}
            self.turns[thread_id] = turn
            self.threads[thread_id]['status']['type'] = 'active'
            return {'turn': copy.deepcopy(turn)}
        if method == 'turn/steer':
            return {}
        raise AssertionError(method)

    def finish_retry(self, code='serverOverloaded'):
        turn_id = self.turns['target']['id']
        self.turns['target'] = failed(turn_id, code)
        self.threads['target']['status']['type'] = 'idle'


class RecoveryTest(unittest.TestCase):
    def setUp(self):
        self.rpc = FakeRpc()
        self.state = {}
        self.saved = []
        self.logs = []
        self.now = 100.5
        self.recovery = self.make_recovery()

    def make_recovery(self):
        return listener.Recovery(self.rpc, self.state,
                                 lambda: self.saved.append(copy.deepcopy(self.state)),
                                 'host', retry_delay=5, clock=lambda: self.now, log=self.logs.append)

    def observe(self, baseline=False):
        self.recovery.observe(self.rpc.threads['target'], self.rpc.turns['target'], baseline)

    def send(self):
        self.now += 5
        self.recovery.retry_due('target')

    def target_starts(self):
        return [p for p in self.rpc.starts if p['threadId'] == 'target']

    def test_only_exact_capacity_code_on_failed_turn(self):
        for code in (None, 'serverOverloaded ', 'ServerOverloaded', 'other', 'rateLimitExceeded',
                     'flexUnavailable', 'usageLimitExceeded', 'internalServerError',
                     {'httpConnectionFailed': {'httpStatusCode': 503}}):
            with self.subTest(code=code):
                self.assertFalse(listener.capacity_failure(failed(code=code)))
        for status in ('completed', 'interrupted', 'inProgress'):
            self.assertFalse(listener.capacity_failure(dict(failed(), status=status)))
        self.assertTrue(listener.capacity_failure(failed()))

    def test_delay_exact_retry_message_and_host_notification(self):
        self.observe()
        self.recovery.retry_due('target')
        self.assertEqual(self.rpc.starts, [])
        self.send()
        self.assertEqual(len(self.target_starts()), 1)
        params = self.target_starts()[0]
        self.assertEqual(set(params), {'threadId', 'input'})
        self.assertIn('Retrying now (1/3)', params['input'][0]['text'])
        self.assertEqual(self.rpc.starts[1]['threadId'], 'host')
        self.assertIn('/project', self.rpc.starts[1]['input'][0]['text'])
        self.assertTrue(any(s['target']['blocked'] == 'retry send outcome unknown' for s in self.saved))

    def test_three_attempts_maximum_survives_restarts(self):
        self.observe()
        for attempt in range(3):
            self.recovery = self.make_recovery()
            self.send()
            self.rpc.finish_retry()
            self.observe()
        for _ in range(4):
            self.recovery = self.make_recovery()
            self.observe()
            self.send()
        self.assertEqual(len(self.target_starts()), 3)
        self.assertEqual(self.state['target']['attempts'], 3)
        self.assertIn('exhausted', self.state['target']['blocked'])

    def test_duplicate_failure_does_not_send_twice(self):
        self.observe()
        self.observe()
        self.send()
        self.recovery.retry_due('target')
        self.assertEqual(len(self.target_starts()), 1)

    def test_new_turn_active_thread_and_changed_error_cancel_pending(self):
        for changed in ('turn', 'active', 'error', 'capability'):
            with self.subTest(changed=changed):
                self.setUp()
                self.observe()
                if changed == 'turn':
                    self.rpc.turns['target'] = failed('manual-turn')
                elif changed == 'active':
                    self.rpc.threads['target']['status']['type'] = 'active'
                elif changed == 'capability':
                    self.rpc.threads['target']['canAcceptDirectInput'] = False
                else:
                    self.rpc.turns['target']['error']['codexErrorInfo'] = 'other'
                self.send()
                self.assertEqual(self.target_starts(), [])
                self.assertIsNone(self.state['target']['pending'])

    def test_other_error_or_interruption_stops_recovery(self):
        for status in ('failed', 'interrupted'):
            self.setUp()
            self.observe()
            self.send()
            self.rpc.finish_retry('rateLimitExceeded')
            self.rpc.turns['target']['status'] = status
            self.observe()
            self.send()
            self.assertEqual(len(self.target_starts()), 1)
            self.assertIsNotNone(self.state['target']['blocked'])

    def test_paused_or_finished_goal_prevents_resume(self):
        for status in ('paused', 'complete', 'blocked', 'budgetLimited'):
            self.setUp()
            self.rpc.goals['target'] = {'status': status}
            self.observe()
            self.send()
            self.assertEqual(self.target_starts(), [])

    def test_uncertain_send_is_persistently_blocked(self):
        self.observe()
        self.rpc.send_error = True
        with self.assertRaises(RpcError):
            self.send()
        self.recovery = self.make_recovery()
        self.send()
        self.assertEqual(len(self.target_starts()), 1)
        self.assertEqual(self.state['target']['blocked'], 'retry send outcome unknown')

    def test_success_does_not_reset_per_task_budget(self):
        self.observe()
        self.send()
        self.rpc.finish_retry()
        self.rpc.turns['target']['status'] = 'completed'
        self.observe()
        self.assertEqual(self.state['target']['attempts'], 1)
        self.assertIsNone(self.state['target']['pending'])

    def test_old_failures_excluded_but_current_turn_can_fail_later(self):
        self.observe(baseline=True)
        self.send()
        self.assertEqual(self.target_starts(), [])
        self.setUp()
        self.rpc.turns['target']['status'] = 'inProgress'
        self.observe(baseline=True)
        self.rpc.turns['target']['status'] = 'failed'
        self.observe()
        self.send()
        self.assertEqual(len(self.target_starts()), 1)

    def test_failure_after_arming_during_baseline_scan_is_recovered(self):
        self.rpc.turns['target']['completedAt'] = 101
        self.observe(baseline=True)
        self.assertIsNotNone(self.state['target']['pending'])
        self.observe()
        self.send()
        self.assertEqual(len(self.target_starts()), 1)

    def test_cross_project_pagination_excludes_host_and_subagents(self):
        self.rpc.threads['child'] = dict(metadata('child'), parentThreadId='target')
        self.rpc.turns['child'] = failed('child-turn')
        self.recovery.scan()
        self.assertIn('target', self.state)
        self.assertNotIn('child', self.state)
        self.assertNotIn('host', self.state)
        self.rpc.threads.pop('target')
        # No unloaded thread is resumed, even if it still has a pending retry.
        self.rpc.call = lambda method, params: {'data': [], 'nextCursor': None}
        self.recovery.scan()
        self.assertIsNone(self.state['target']['pending'])

    def test_active_host_uses_steer_and_notification_failure_is_not_retried(self):
        self.rpc.threads['host']['status']['type'] = 'active'
        self.rpc.turns['host']['status'] = 'inProgress'
        self.observe()
        self.send()
        steers = [p for m, p in self.rpc.calls if m == 'turn/steer']
        self.assertEqual(steers[0]['expectedTurnId'], 'host-turn')
        self.rpc.threads['host']['canAcceptDirectInput'] = False
        self.recovery.notify('test')
        self.assertIn('not retried', self.logs[-1])

    def test_empty_session_is_skipped_but_other_rpc_errors_propagate(self):
        empty = {'code': -32600, 'message': 'thread target is not materialized yet; '
                 'thread/turns/list is unavailable before first user message'}
        def raise_error(method, params):
            raise RpcError('error', empty)
        self.rpc.call = raise_error
        self.assertIsNone(self.recovery.latest('target'))
        empty['message'] += ' unexpected'
        with self.assertRaises(RpcError):
            self.recovery.latest('target')

    def test_daemon_without_list_turns_uses_materialized_history(self):
        original = self.rpc.call
        def call(method, params):
            if method == 'thread/turns/list':
                raise RpcError('unsupported', {'code': -32601,
                                              'message': 'list_turns is not supported yet'})
            result = original(method, params)
            if method == 'thread/read' and params.get('includeTurns'):
                result['thread']['turns'] = [dict(failed('old'), completedAt=90),
                                             self.rpc.turns[params['threadId']]]
            return result
        self.rpc.call = call
        self.assertEqual(self.recovery.latest('target')['id'], 'original')
        self.recovery.scan()
        self.send()
        self.assertEqual(len(self.target_starts()), 1)

    def test_ephemeral_thread_does_not_stop_scans_or_receive_retries(self):
        self.rpc.threads['ephemeral'] = metadata('ephemeral')
        original_call = self.rpc.call

        def call(method, params):
            if method == 'thread/turns/list' and params['threadId'] == 'ephemeral':
                error = {'code': -32600,
                         'message': 'ephemeral threads do not support thread/turns/list'}
                raise RpcError('unsupported history', error)
            return original_call(method, params)

        self.rpc.call = call
        self.recovery.scan(baseline=True)
        self.assertEqual(self.rpc.starts, [])
        self.rpc.turns['target'] = dict(failed('new-failure'), completedAt=101)
        self.now = 101
        self.recovery.scan()
        self.now += 5
        self.recovery.scan()
        self.assertEqual(len(self.target_starts()), 1)
        self.assertNotIn('ephemeral', self.state)

    def test_ephemeral_history_error_cancels_pending_retry(self):
        self.observe()
        original_call = self.rpc.call

        def call(method, params):
            if method == 'thread/turns/list':
                error = {'code': -32600,
                         'message': 'ephemeral threads do not support thread/turns/list'}
                raise RpcError('unsupported history', error)
            return original_call(method, params)

        self.rpc.call = call
        self.send()
        self.assertEqual(self.target_starts(), [])
        self.assertIsNone(self.state['target']['pending'])

    def test_other_history_errors_still_stop_scanning(self):
        original_call = self.rpc.call
        error = {'code': -32600,
                 'message': 'ephemeral threads do not support thread/turns/list unexpected'}

        def call(method, params):
            if method == 'thread/turns/list':
                raise RpcError('history failed', error)
            return original_call(method, params)

        self.rpc.call = call
        with self.assertRaises(RpcError):
            self.recovery.scan()
        error['message'] = 'ephemeral threads do not support thread/turns/list'
        error['code'] = -32000
        with self.assertRaises(RpcError):
            self.recovery.scan()


class QuotaTest(unittest.TestCase):
    def setUp(self):
        self.rpc = FakeRpc()
        self.state = {}
        self.quota = listener.QuotaGuard(self.rpc, self.state, lambda: None, log=lambda text: None)
        self.recovery = listener.Recovery(self.rpc, {}, lambda: None, 'host',
                                          clock=lambda: 100, quota=self.quota, log=lambda text: None)

    def activate(self, thread_id):
        self.rpc.threads[thread_id]['status']['type'] = 'active'
        self.rpc.turns[thread_id] = {'id': thread_id + '-turn', 'status': 'inProgress'}

    def steers(self):
        return [params for method, params in self.rpc.calls if method == 'turn/steer']

    def test_boundary_all_active_parents_including_host_and_new_chats(self):
        self.activate('host')
        self.activate('target')
        self.rpc.threads['child'] = dict(metadata('child', status='active'), parentThreadId='target')
        self.rpc.turns['child'] = {'id': 'child-turn', 'status': 'inProgress'}
        self.rpc.used = 90
        self.recovery.scan()
        self.assertEqual(self.steers(), [])
        self.rpc.used = 91
        self.recovery.scan()
        self.assertEqual({p['threadId'] for p in self.steers()}, {'target', 'host'})
        self.assertEqual(self.rpc.starts, [])
        self.quota = listener.QuotaGuard(self.rpc, self.state, lambda: None, log=lambda text: None)
        self.recovery.quota = self.quota
        self.recovery.scan()
        self.assertEqual(len(self.steers()), 2)
        self.rpc.threads['new'] = metadata('new', status='active')
        self.rpc.turns['new'] = {'id': 'new-turn', 'status': 'inProgress'}
        self.recovery.scan()
        self.assertEqual(self.steers()[-1]['threadId'], 'new')

    def test_low_quota_cancels_pending_retry_and_never_wakes_idle_chat(self):
        self.recovery.observe(self.rpc.threads['target'], self.rpc.turns['target'])
        self.assertIsNotNone(self.recovery.state['target']['pending'])
        self.rpc.used = 95
        self.recovery.scan()
        self.assertIsNone(self.recovery.state['target']['pending'])
        self.assertEqual(self.rpc.starts, [])
        self.assertEqual(self.steers(), [])
        self.rpc.used = 0
        self.recovery.scan()
        self.assertEqual(self.rpc.starts, [])

    def test_capacity_failure_notification_does_not_wake_host_while_low(self):
        self.recovery.state['target'] = {
            'seen': None, 'attempts': 3, 'pending': None, 'awaiting': None, 'blocked': None,
        }
        self.rpc.used = 95
        self.recovery.scan()
        self.assertEqual(self.rpc.starts, [])
        self.assertEqual(self.steers(), [])

    def test_reset_rearms_but_does_not_resume_work(self):
        self.activate('target')
        self.rpc.used = 99
        self.recovery.scan()
        self.rpc.reset += 10080 * 60
        self.recovery.scan()
        self.assertEqual(len(self.steers()), 2)
        self.rpc.used = 0
        self.recovery.scan()
        self.assertEqual(self.state['notified'], [])
        self.assertEqual(self.rpc.starts, [])

    def test_unknown_usage_stops_before_retries_or_commands(self):
        for used in (None, True, float('nan'), -1, 101):
            self.rpc.used = used
            with self.assertRaises(ValueError):
                self.recovery.scan()
        self.assertEqual(self.rpc.starts, [])
        self.assertEqual(self.steers(), [])

    def test_lost_command_reply_is_not_repeated(self):
        self.activate('target')
        self.rpc.used = 95
        original = self.rpc.call
        def call(method, params):
            result = original(method, params)
            if method == 'turn/steer':
                raise RpcError('reply lost')
            return result
        self.rpc.call = call
        self.recovery.scan()
        self.recovery.scan()
        self.assertEqual(len(self.steers()), 1)


class WebSocketTest(unittest.TestCase):
    def test_real_unix_handshake_fragmented_rpc_ping_and_exact_error(self):
        failures = []
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'daemon.sock'
            server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            server.bind(str(path))
            server.listen(1)

            def serve():
                try:
                    with server.accept()[0] as client:
                        client.settimeout(3)
                        def exact(size):
                            result = b''
                            while len(result) < size:
                                part = client.recv(size - len(result))
                                if not part:
                                    raise RuntimeError('EOF')
                                result += part
                            return result
                        request = b''
                        while not request.endswith(b'\r\n\r\n'):
                            request += exact(1)
                        headers = dict(line.split(': ', 1) for line in request.decode().split('\r\n') if ': ' in line)
                        accept = base64.b64encode(hashlib.sha1((headers['Sec-WebSocket-Key'] +
                                                              '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()).digest())
                        client.sendall(b'HTTP/1.1 101 Switching Protocols\r\nSec-WebSocket-Accept: ' + accept + b'\r\n\r\n')
                        def frame():
                            first, second = exact(2)
                            self.assertTrue(second & 128)
                            size = second & 127
                            if size == 126:
                                size = struct.unpack('>H', exact(2))[0]
                            mask, payload = exact(4), exact(size)
                            return first & 15, bytes(v ^ mask[i % 4] for i, v in enumerate(payload))
                        def send(first, payload):
                            client.sendall(bytes([first, len(payload)]) + payload)
                        _, raw = frame()
                        initialize = json.loads(raw)
                        send(0x81, json.dumps({'id': initialize['id'], 'result': {}}).encode())
                        _, raw = frame()
                        self.assertEqual(json.loads(raw)['method'], 'initialized')
                        _, raw = frame()
                        request = json.loads(raw)
                        # Request IDs belong to opposite peers and may collide. An
                        # approval must neither consume our RPC nor receive a rejection.
                        send(0x81, json.dumps({'id': request['id'],
                                             'method': 'item/commandExecution/requestApproval',
                                             'params': {}}).encode())
                        send(0x89, b'ping')
                        self.assertEqual(frame(), (10, b'ping'))
                        payload = json.dumps({'id': request['id'], 'result': {'code': 'serverOverloaded'}}).encode()
                        send(0x01, payload[:20])
                        send(0x80, payload[20:])
                        _, raw = frame()
                        request = json.loads(raw)
                        send(0x81, json.dumps({'id': request['id'], 'error': {'code': -32000, 'message': 'other'}}).encode())
                except BaseException as error:
                    failures.append(error)
                finally:
                    server.close()

            worker = threading.Thread(target=serve, daemon=True)
            worker.start()
            rpc = AppServer(path, timeout=3)
            try:
                self.assertEqual(rpc.call('test', {}), {'code': 'serverOverloaded'})
                with self.assertRaises(RpcError):
                    rpc.call('test', {})
            finally:
                rpc.close()
                worker.join(timeout=5)
            self.assertFalse(worker.is_alive())
            self.assertEqual(failures, [])


if __name__ == '__main__':
    unittest.main()
