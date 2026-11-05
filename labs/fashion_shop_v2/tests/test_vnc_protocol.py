"""RFB readiness must include authentication and actual pixels, not a banner."""
import importlib.util
import io
from pathlib import Path
import struct
from unittest.mock import patch

import pytest

SOURCE = Path(__file__).resolve().parents[1] / 'sandbox/provisioning/files/check-vnc.py'


def module():
    spec = importlib.util.spec_from_file_location('meko_check_vnc', SOURCE)
    result = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(result)
    return result


class Peer:
    def __init__(self, data):
        self.data = bytearray(data)
        self.sent = bytearray()

    def recv(self, size):
        # Deliberately fragment every read, like TCP may do.
        chunk = self.data[:min(size, 3)]
        del self.data[:len(chunk)]
        return bytes(chunk)

    def sendall(self, data):
        self.sent.extend(data)


def greeting(result=0):
    return b'RFB 003.008\n\x01\x02' + bytes(range(16)) + struct.pack('!I', result)


def initialized(width=1440, height=900):
    return struct.pack('!HH', width, height) + bytes(16) + struct.pack('!I', 4) + b'XFCE'


def frame(encoding=0, width=1):
    return b'\x00\x00\x00\x01' + struct.pack('!HHHHi', 0, 0, width, 1, encoding) + b'\x12\x34\x56\x00'


def test_vnc_auth_response_matches_independent_known_vector():
    # DES with password bits reversed, challenge bytes 0..15.
    assert module().challenge_response('Meko1Vnc', bytes(range(16))).hex() == '1dc10102151dfb24987169edb5f3cc68'


def test_probe_requires_password_and_receives_raw_frame():
    peer = Peer(greeting() + initialized() + b'\x02' + frame())  # Bell may precede update.
    info = module().check_session(peer, 'Meko1Vnc')
    assert info == {'authenticated': True, 'width': 1440, 'height': 900, 'frame_received': True}
    assert peer.sent.startswith(b'RFB 003.008\n\x02')
    assert b'Meko1Vnc' not in peer.sent
    assert peer.sent[-10:] == struct.pack('!BBHHHH', 3, 0, 0, 0, 1, 1)


@pytest.mark.parametrize('data,reason', [
    (b'HTTP/1.1 200 ', 'protocol'),
    (b'RFB 003.008\n\x01\x01', 'VncAuth'),
    (b'RFB 003.008\n\x00', 'VncAuth'),
    (greeting(1), 'authentication'),
    (greeting() + initialized(0), 'dimensions'),
    (greeting() + initialized() + frame(5), 'encoding'),
    (greeting() + initialized() + frame(width=2), 'rectangle'),
    (greeting() + initialized() + b'\x03\x00\x00\x00' + struct.pack('!I', 2**30), 'clipboard'),
    (greeting() + initialized() + b'\x00\x00\x00\x02', 'rectangle count'),
    (greeting() + initialized() + b'\x04', 'message'),
    (greeting() + initialized() + b'\x02' * 32, 'did not return'),
    (greeting() + initialized() + frame()[:-1], 'closed'),
    (b'RFB ', 'closed'),
])
def test_probe_rejects_false_readiness(data, reason):
    with pytest.raises(ValueError, match=reason):
        module().check_session(Peer(data), 'Meko1Vnc')


def test_cli_does_not_log_password_on_failure(capsys):
    probe = module()
    with patch.object(probe.sys, 'stdin', io.StringIO('Meko1Vnc\n')), patch.object(
            probe.socket, 'create_connection', side_effect=OSError('connection refused')):
        assert probe.main(['--port', '5900']) == 1
    output = capsys.readouterr()
    assert 'Meko1Vnc' not in output.out + output.err
    assert 'connection refused' in output.err


@pytest.mark.parametrize('password', ['short', 'ninechars', 'ábcdefgh', 'abcd\nefgh'])
def test_invalid_password_never_opens_connection(password):
    probe = module()
    with patch.object(probe.socket, 'create_connection') as connect:
        with pytest.raises(ValueError):
            probe.challenge_response(password, bytes(16))
        connect.assert_not_called()


def test_probe_accepts_rfb37_and_skips_small_clipboard_and_empty_updates():
    peer = Peer(greeting().replace(b'003.008', b'003.007') + initialized()
                + b'\x00\x00\x00\x00' + b'\x03\x00\x00\x00\x00\x00\x00\x02hi' + frame())
    assert module().check_session(peer, 'Meko1Vnc')['frame_received']


def test_probe_bounds_desktop_name_and_total_read_time():
    probe = module()
    data = greeting() + initialized()[:-8] + struct.pack('!I', 100000)
    with pytest.raises(ValueError, match='desktop name'):
        probe.check_session(Peer(data), 'Meko1Vnc')
    with pytest.raises(TimeoutError, match='deadline'):
        probe.check_session(Peer(greeting()), 'Meko1Vnc', timeout=-1)


def test_cli_prints_only_readiness_metadata_on_success(capsys):
    probe = module()
    peer = Peer(greeting() + initialized() + frame())
    with patch.object(probe.sys, 'stdin', io.StringIO('Meko1Vnc\n')), patch.object(
            probe.socket, 'create_connection') as connect:
        connect.return_value.__enter__.return_value = peer
        assert probe.main(['--port', '15900']) == 0
    assert connect.call_args.args[0] == ('127.0.0.1', 15900)
    output = capsys.readouterr()
    assert '"frame_received": true' in output.out
    assert 'Meko1Vnc' not in output.out + output.err


def test_cli_rejects_invalid_port_before_network(capsys):
    probe = module()
    with patch.object(probe.socket, 'create_connection') as connect:
        assert probe.main(['--port', '0']) == 1
    connect.assert_not_called()
    assert 'Invalid VNC port' in capsys.readouterr().err
