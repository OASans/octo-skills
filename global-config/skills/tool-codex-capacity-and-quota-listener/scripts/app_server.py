"""JSON-RPC over the existing daemon's Unix WebSocket; never spawn a server."""

import base64
import hashlib
import json
import os
import socket
import struct
import time


class RpcError(RuntimeError):
    def __init__(self, message, error=None):
        super().__init__(message)
        self.error = error


class AppServer:
    def __init__(self, path, timeout=10):
        self.socket = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.socket.settimeout(timeout)
        self.timeout = timeout
        self.sequence = 0
        try:
            self.socket.connect(str(path))
            key = base64.b64encode(os.urandom(16)).decode()
            self.socket.sendall((
                'GET / HTTP/1.1\r\nHost: localhost\r\nUpgrade: websocket\r\n'
                f'Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\n'
                'Sec-WebSocket-Version: 13\r\n\r\n'
            ).encode())
            header = bytearray()
            while not header.endswith(b'\r\n\r\n'):
                header.extend(self._read(1))
                if len(header) > 8192:
                    raise RpcError('Oversized WebSocket handshake')
            lines = header.decode('ascii').split('\r\n')
            expected = base64.b64encode(hashlib.sha1(
                (key + '258EAFA5-E914-47DA-95CA-C5AB0DC85B11').encode()
            ).digest()).decode()
            headers = {name.lower(): value.strip() for name, value in
                       (line.split(':', 1) for line in lines[1:] if ':' in line)}
            if ' 101 ' not in lines[0] or headers.get('sec-websocket-accept') != expected:
                raise RpcError('Invalid daemon WebSocket handshake')
            self.call('initialize', {
                'clientInfo': {'name': 'octo_capacity_retry', 'version': '1.0'},
                'capabilities': {'experimentalApi': True},
            })
            self._send(1, json.dumps({'method': 'initialized'}).encode())
        except BaseException:
            self.close()
            raise

    def close(self):
        self.socket.close()

    def _read(self, size):
        chunks = bytearray()
        while len(chunks) < size:
            chunk = self.socket.recv(size - len(chunks))
            if not chunk:
                raise RpcError('Codex daemon disconnected')
            chunks.extend(chunk)
        return bytes(chunks)

    def _send(self, opcode, payload):
        size = len(payload)
        header = bytes([0x80 | opcode])
        if size < 126:
            header += bytes([0x80 | size])
        elif size < 65536:
            header += b'\xfe' + struct.pack('>H', size)
        else:
            header += b'\xff' + struct.pack('>Q', size)
        mask = os.urandom(4)
        encoded = bytes(byte ^ mask[i % 4] for i, byte in enumerate(payload))
        self.socket.sendall(header + mask + encoded)

    def _receive(self, deadline):
        message = bytearray()
        started = False
        while True:
            self.socket.settimeout(max(0.001, deadline - time.monotonic()))
            if time.monotonic() >= deadline:
                raise RpcError('Codex RPC deadline expired')
            first, second = self._read(2)
            opcode, size = first & 15, second & 127
            if first & 0x70 or second & 0x80:
                raise RpcError('Unsupported daemon WebSocket frame')
            if size == 126:
                size = struct.unpack('>H', self._read(2))[0]
            elif size == 127:
                size = struct.unpack('>Q', self._read(8))[0]
            if size + len(message) > 16 * 1024 * 1024:
                raise RpcError('Oversized daemon WebSocket message')
            payload = self._read(size)
            if opcode == 8:
                raise RpcError('Codex daemon closed the connection')
            if opcode == 9:
                self._send(10, payload)
                continue
            if opcode == 10:
                continue
            if opcode == 1 and not started:
                started = True
            elif opcode != 0 or not started:
                raise RpcError('Unexpected daemon WebSocket frame')
            message.extend(payload)
            if first & 0x80:
                return json.loads(message)

    def call(self, method, params):
        self.sequence += 1
        request_id = self.sequence
        self.socket.settimeout(self.timeout)
        self._send(1, json.dumps({'id': request_id, 'method': method, 'params': params}).encode())
        deadline = time.monotonic() + self.timeout
        while True:
            reply = self._receive(deadline)
            if 'method' not in reply and reply.get('id') == request_id:
                if 'error' in reply:
                    raise RpcError(f'{method}: {json.dumps(reply["error"])}', reply['error'])
                return reply['result']
            # Server requests are shared with the task's existing UI. Leave approvals,
            # tool calls, and user input unanswered so its normal client can respond.
