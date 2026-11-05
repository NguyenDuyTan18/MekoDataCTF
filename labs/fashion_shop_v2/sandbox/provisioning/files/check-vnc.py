#!/usr/bin/python3
"""Authenticate RFB and request one pixel. Password is accepted only on stdin."""
import argparse
import json
import socket
import struct
import sys
import time

try:  # Debian's python3-pycryptodome uses the Cryptodome namespace.
    from Cryptodome.Cipher import DES
except ImportError:
    from Crypto.Cipher import DES


def challenge_response(password, challenge):
    if (len(password) != 8 or not password.isascii() or not password.isalnum()
            or len(challenge) != 16):
        raise ValueError('Expected an eight-character ASCII VNC password and 16-byte challenge')
    key = bytes(int(f'{value:08b}'[::-1], 2) for value in password.encode('ascii'))
    return DES.new(key, DES.MODE_ECB).encrypt(challenge)


def check_session(peer, password, timeout=10):
    """Support RFB 3.7/3.8, VncAuth and raw updates, with bounded reads."""
    deadline = time.monotonic() + timeout

    def read(size):
        data = bytearray()
        while len(data) < size:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('VNC frame deadline exceeded')
            if hasattr(peer, 'settimeout'):
                peer.settimeout(remaining)
            chunk = peer.recv(size - len(data))
            if not chunk:
                raise ValueError('VNC connection closed before desktop frame')
            data.extend(chunk)
        return bytes(data)

    version = read(12)
    if version not in (b'RFB 003.007\n', b'RFB 003.008\n'):
        raise ValueError('Unsupported VNC protocol (expected RFB 3.7/3.8)')
    peer.sendall(version)
    count = read(1)[0]
    if count == 0 or 2 not in read(count):
        raise ValueError('VNC server does not offer VncAuth')
    peer.sendall(b'\x02')
    peer.sendall(challenge_response(password, read(16)))
    if struct.unpack('!I', read(4))[0] != 0:
        raise ValueError('VNC authentication rejected')
    peer.sendall(b'\x01')  # Shared: keep existing desktop clients connected.
    header = read(24)
    width, height = struct.unpack('!HH', header[:4])
    if not (1 <= width <= 16384 and 1 <= height <= 16384):
        raise ValueError('Invalid VNC desktop dimensions')
    name_length = struct.unpack('!I', header[20:])[0]
    if name_length > 4096:
        raise ValueError('Oversized VNC desktop name')
    read(name_length)
    # 32 bits/pixel, depth 24, little endian, true colour, RGB shifts 16/8/0.
    pixel_format = struct.pack('!BBBBHHHBBB3x', 32, 24, 0, 1, 255, 255, 255, 16, 8, 0)
    peer.sendall(b'\x00\x00\x00\x00' + pixel_format)
    peer.sendall(struct.pack('!BBHi', 2, 0, 1, 0))  # Raw encoding only.
    peer.sendall(struct.pack('!BBHHHH', 3, 0, 0, 0, 1, 1))
    for _ in range(32):
        message = read(1)[0]
        if message == 2:  # Bell
            continue
        if message == 3:  # ServerCutText
            length = struct.unpack('!3xI', read(7))[0]
            if length > 65536:
                raise ValueError('Oversized VNC clipboard message')
            read(length)
            continue
        if message != 0:
            raise ValueError('Unexpected VNC server message')
        rectangles = struct.unpack('!xH', read(3))[0]
        if rectangles == 0:
            continue
        if rectangles != 1:
            raise ValueError('Unexpected VNC rectangle count')
        x, y, rect_width, rect_height, encoding = struct.unpack('!HHHHi', read(12))
        if encoding != 0:
            raise ValueError('Unexpected VNC frame encoding')
        if (x, y, rect_width, rect_height) != (0, 0, 1, 1):
            raise ValueError('Unexpected VNC frame rectangle')
        read(4)
        return {'authenticated': True, 'width': width, 'height': height, 'frame_received': True}
    raise ValueError('VNC did not return a desktop frame')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=5900)
    parser.add_argument('--timeout', type=float, default=10)
    args = parser.parse_args(argv)
    try:
        if not 1 <= args.port <= 65535 or not 0 < args.timeout <= 60:
            raise ValueError('Invalid VNC port or timeout')
        password = sys.stdin.read(130).removesuffix('\n')
        challenge_response(password, bytes(16))  # Validate before opening a socket.
        with socket.create_connection((args.host, args.port), timeout=args.timeout) as peer:
            result = check_session(peer, password, args.timeout)
        print(json.dumps(result))
        return 0
    except (OSError, ValueError) as error:
        print(f'VNC readiness failed: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
