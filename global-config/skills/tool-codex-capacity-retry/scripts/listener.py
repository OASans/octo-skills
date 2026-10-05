"""Bounded, exact-code capacity recovery for loaded local Codex tasks."""

import argparse
import fcntl
import json
import os
from pathlib import Path
import select
import socket
import subprocess
import sys
import time

from app_server import AppServer, RpcError


def save_json(path, value):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def capacity_failure(turn):
    return (turn.get('status') == 'failed'
            and isinstance(turn.get('error'), dict)
            and turn['error'].get('codexErrorInfo') == 'serverOverloaded')


class Recovery:
    def __init__(self, rpc, state, save, notify_thread, max_retries=3, retry_delay=300,
                 clock=time.time, log=print):
        self.rpc = rpc
        self.state = state
        self.save = save
        self.notify_thread = notify_thread
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.clock = clock
        self.log = log
        self.armed_at = int(clock())

    def metadata(self, thread_id):
        return self.rpc.call('thread/read', {'threadId': thread_id, 'includeTurns': False})['thread']

    def latest(self, thread_id):
        try:
            turns = self.rpc.call('thread/turns/list', {
                'threadId': thread_id, 'limit': 1, 'sortDirection': 'desc', 'itemsView': 'summary',
            })['data']
        except RpcError as error:
            empty_history = (f'thread {thread_id} is not materialized yet; '
                             'thread/turns/list is unavailable before first user message')
            unavailable_history = (
                empty_history, 'ephemeral threads do not support thread/turns/list',
            )
            if any(error.error == {'code': -32600, 'message': message}
                   for message in unavailable_history):
                return None
            raise
        return turns[0] if turns else None

    def eligible(self, thread):
        return (thread['id'] != self.notify_thread and not thread.get('parentThreadId')
                and thread.get('canAcceptDirectInput') is True
                and thread['status']['type'] in ('idle', 'systemError'))

    def notify(self, text):
        self.log(text)
        try:
            host = self.metadata(self.notify_thread)
            if host.get('canAcceptDirectInput') is not True:
                raise RpcError('Notification conversation cannot accept input')
            message = ('[tool-codex-capacity-retry notification] ' + text
                       + '\nStatus only: acknowledge briefly and keep following the existing user request. '
                       'Do not take action on the reported task.')
            params = {'threadId': self.notify_thread, 'input': [{'type': 'text', 'text': message}]}
            if host['status']['type'] == 'active':
                turn = self.latest(self.notify_thread)
                if not turn or turn['status'] != 'inProgress':
                    raise RpcError('Notification conversation changed turns')
                params['expectedTurnId'] = turn['id']
                self.rpc.call('turn/steer', params)
            elif host['status']['type'] == 'idle':
                self.rpc.call('turn/start', params)
            else:
                raise RpcError('Notification conversation is unavailable')
        except (OSError, RpcError, KeyError, ValueError) as error:
            self.log(f'Notification failed (not retried): {error}')

    def stop_task(self, thread_id, entry, reason):
        entry['pending'] = None
        entry['awaiting'] = None
        entry['blocked'] = reason
        self.save()
        self.notify(f'Stopped retries for task {thread_id}: {reason}.')

    def observe(self, thread, turn, baseline=False):
        thread_id = thread['id']
        if thread_id == self.notify_thread or thread.get('parentThreadId') or not turn:
            return
        entry = self.state.setdefault(thread_id, {
            'seen': None, 'attempts': 0, 'pending': None, 'awaiting': None, 'blocked': None,
        })
        if entry['blocked']:
            return
        pending = entry['pending']
        if pending and (turn['id'] != pending['turn_id'] or not self.eligible(thread)):
            entry['pending'] = None
            self.save()
        if turn['status'] == 'inProgress':
            return
        if turn['id'] == entry['seen']:
            return
        entry['seen'] = turn['id']
        awaiting = entry['awaiting']
        entry['awaiting'] = None
        if awaiting and turn['id'] == awaiting and not capacity_failure(turn) and turn['status'] != 'completed':
            self.stop_task(thread_id, entry, 'retry ended with a different error or interruption')
            return
        # Startup does not revive old work. Persisted pending retries keep their deadline.
        completed_at = turn.get('completedAt') or turn.get('startedAt') or 0
        if not awaiting and (completed_at < self.armed_at
                             or (baseline and completed_at <= self.armed_at)):
            self.save()
            return
        if capacity_failure(turn) and self.eligible(thread):
            if entry['attempts'] >= self.max_retries:
                self.stop_task(thread_id, entry, f'{self.max_retries} retry attempts exhausted')
                return
            entry['pending'] = {'turn_id': turn['id'], 'due': self.clock() + self.retry_delay}
        self.save()

    def retry_due(self, thread_id):
        entry = self.state[thread_id]
        pending = entry['pending']
        if entry['blocked'] or not pending or self.clock() < pending['due']:
            return
        thread = self.metadata(thread_id)
        turn = self.latest(thread_id)
        if (not self.eligible(thread) or not turn or turn['id'] != pending['turn_id']
                or not capacity_failure(turn)):
            entry['pending'] = None
            self.save()
            return
        goal = self.rpc.call('thread/goal/get', {'threadId': thread_id}).get('goal')
        if goal and goal.get('status') != 'active':
            self.stop_task(thread_id, entry, 'goal is not active')
            return
        if entry['attempts'] >= self.max_retries:
            self.stop_task(thread_id, entry, f'{self.max_retries} retry attempts exhausted')
            return
        entry['attempts'] += 1
        entry['pending'] = None
        # Reserve before sending: a crash or lost reply must never repeat an uncertain send.
        entry['blocked'] = 'retry send outcome unknown'
        self.save()
        attempt = entry['attempts']
        text = (f'Retrying now ({attempt}/{self.max_retries}) after the exact model capacity error. '
                'Continue the existing task from its current state; check prior tool results before '
                'repeating actions. Keep the existing model, permissions, and task scope.')
        result = self.rpc.call('turn/start', {
            'threadId': thread_id, 'input': [{'type': 'text', 'text': text}],
        })
        retry = result['turn']
        if retry['id'] == turn['id']:
            raise RpcError('Retry did not start a new turn; task remains blocked')
        entry['blocked'] = None
        entry['awaiting'] = retry['id']
        self.save()
        self.notify(f'Retry {attempt}/{self.max_retries} sent to task {thread_id} in {thread["cwd"]}.')

    def scan(self, baseline=False):
        loaded = []
        cursor = None
        while True:
            page = self.rpc.call('thread/loaded/list', {'cursor': cursor, 'limit': 100})
            loaded.extend(page['data'])
            cursor = page.get('nextCursor')
            if not cursor:
                break
        loaded = set(loaded)
        for thread_id in loaded:
            if thread_id == self.notify_thread:
                continue
            thread = self.metadata(thread_id)
            if thread.get('parentThreadId') or thread.get('canAcceptDirectInput') is not True:
                continue
            self.observe(thread, self.latest(thread_id), baseline)
        for thread_id, entry in self.state.items():
            if thread_id not in loaded and entry['pending']:
                entry['pending'] = None
                self.save()
            if thread_id in loaded:
                self.retry_due(thread_id)


def control(directory, command):
    with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
        client.settimeout(10)
        client.connect(str(directory / 'control.sock'))
        client.sendall(command.encode() + b'\n')
        chunks = bytearray()
        while not chunks.endswith(b'\n'):
            part = client.recv(4096)
            if not part:
                raise RuntimeError('Listener control connection closed')
            chunks.extend(part)
        return json.loads(chunks)


def run(args, directory, codex_home):
    lock = (directory / 'listener.lock').open('a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        raise RuntimeError('A listener is already running')
    state_path = directory / 'state.json'
    state = json.loads(state_path.read_text()) if state_path.exists() else {}
    status_path = directory / 'status.json'
    status = {
        'running': True, 'pid': os.getpid(), 'notify_thread': args.notify_thread,
        'max_retries': args.max_retries, 'retry_delay': args.retry_delay,
        'started_at': time.time(), 'error': None,
    }
    rpc = None
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    socket_path = directory / 'control.sock'
    try:
        rpc = AppServer(codex_home / 'app-server-control/app-server-control.sock')
        recovery = Recovery(rpc, state, lambda: save_json(state_path, state),
                            args.notify_thread, args.max_retries, args.retry_delay,
                            log=lambda text: print(text, flush=True))
        host = recovery.metadata(args.notify_thread)
        if host.get('canAcceptDirectInput') is not True:
            raise RuntimeError('Notification thread must be loaded and accept direct input')
        recovery.scan(baseline=True)
        socket_path.unlink(missing_ok=True)
        server.bind(str(socket_path))
        server.listen(4)
        save_json(status_path, status)
        print('Capacity listener started', flush=True)
        next_scan = time.monotonic() + args.poll_interval
        while True:
            readable, _, _ = select.select([server], [], [], max(0, next_scan - time.monotonic()))
            if readable:
                with server.accept()[0] as client:
                    client.settimeout(2)
                    command = client.recv(64).decode().strip()
                    reply = dict(status, tasks=state)
                    client.sendall((json.dumps(reply) + '\n').encode())
                    if command == 'stop':
                        break
            if time.monotonic() >= next_scan:
                recovery.scan()
                next_scan = time.monotonic() + args.poll_interval
    except BaseException as error:
        status['error'] = str(error)
        raise
    finally:
        status['running'] = False
        save_json(status_path, status)
        server.close()
        socket_path.unlink(missing_ok=True)
        if rpc:
            rpc.close()
        lock.close()


def positive(value):
    number = int(value)
    if number < 1:
        raise argparse.ArgumentTypeError('Must be positive')
    return number


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['start', 'run', 'status', 'stop', 'probe'])
    parser.add_argument('--notify-thread', default=os.environ.get('CODEX_THREAD_ID'))
    parser.add_argument('--max-retries', type=positive, default=3)
    parser.add_argument('--retry-delay', type=positive, default=300)
    parser.add_argument('--poll-interval', type=positive, default=15)
    args = parser.parse_args()
    codex_home = Path(os.environ.get('CODEX_HOME', Path.home() / '.codex')).resolve()
    directory = codex_home / 'octo-capacity-retry'
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    if args.command in ('start', 'run', 'probe') and not args.notify_thread:
        parser.error('Provide --notify-thread or CODEX_THREAD_ID')
    if args.command == 'probe':
        rpc = AppServer(codex_home / 'app-server-control/app-server-control.sock')
        try:
            host = rpc.call('thread/read', {'threadId': args.notify_thread, 'includeTurns': False})['thread']
            page = rpc.call('thread/turns/list', {'threadId': args.notify_thread, 'limit': 1})
            print(json.dumps({'connected': True, 'notify_thread': host['id'],
                              'can_accept_input': host.get('canAcceptDirectInput'),
                              'latest_turn_count': len(page['data'])}))
        finally:
            rpc.close()
        return
    if args.command == 'run':
        run(args, directory, codex_home)
        return
    try:
        current = control(directory, 'stop' if args.command == 'stop' else 'status')
    except (OSError, RuntimeError):
        current = None
    if args.command == 'status':
        previous = directory / 'status.json'
        print(json.dumps(current or (dict(json.loads(previous.read_text()), running=False)
                                    if previous.exists() else {'running': False})))
    elif args.command == 'stop':
        print(json.dumps({'stop_requested': current is not None}))
    elif current:
        print(json.dumps(current))
    else:
        with (directory / 'listener.log').open('a') as log:
            process = subprocess.Popen([
                sys.executable, str(Path(__file__).resolve()), 'run',
                '--notify-thread', args.notify_thread, '--max-retries', str(args.max_retries),
                '--retry-delay', str(args.retry_delay), '--poll-interval', str(args.poll_interval),
            ], stdin=subprocess.DEVNULL, stdout=log, stderr=log, start_new_session=True)
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline and process.poll() is None:
            try:
                current = control(directory, 'status')
                break
            except OSError:
                time.sleep(0.1)
        if not current:
            raise RuntimeError(f'Listener did not start; inspect {directory / "listener.log"}')
        print(json.dumps(current))


if __name__ == '__main__':
    try:
        main()
    except (OSError, RuntimeError, ValueError, KeyError) as error:
        print(str(error), file=sys.stderr)
        sys.exit(1)
