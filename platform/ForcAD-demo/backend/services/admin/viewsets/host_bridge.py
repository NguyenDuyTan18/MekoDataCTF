"""Chuyển tiếp nút "Bật bộ cờ" / "Collector" của trang quản trị tới cầu nối trên máy (khoi-dong/host_bridge.py).

Chỉ quản trị viên đã đăng nhập gọi được; cầu nối nghe ở 127.0.0.1:18090 của máy, container tới qua
host.docker.internal. Mã cầu nối nằm ở /app/.host-bridge-token (= platform/ForcAD-demo/backend/.host-bridge-token).
"""
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import jsonify, make_response, request

from .authentication import check_session
from .utils import abort_with_error

BRIDGE = 'http://host.docker.internal:18090'
TOKEN_FILE = Path('/app/.host-bridge-token')
ACTIONS = ('flag-system/start', 'collector/start', 'collector/stop', 'gateway/start', 'gateway/stop')
OFFLINE = ('Cầu nối trên máy chưa chạy. Trên máy chủ chạy: python khoi-dong/meko.py bridge install '
           '(cài tự bật khi đăng nhập), hoặc python khoi-dong/meko.py bridge để bật ngay.')


def _call(method, path):
    try:
        token = TOKEN_FILE.read_text(encoding='ascii').strip()
    except OSError:
        return {'error': OFFLINE, 'offline': True}, 503
    req = Request(BRIDGE + path, method=method, data=b'' if method == 'POST' else None,
                  headers={'X-Bridge-Token': token})
    try:
        with urlopen(req, timeout=40) as resp:
            return json.loads(resp.read()), resp.status
    except HTTPError as exc:
        try:
            return json.loads(exc.read()), exc.code
        except ValueError:
            return {'error': f'Cầu nối trả lỗi HTTP {exc.code}.'}, 502
    except (URLError, OSError, ValueError):
        return {'error': OFFLINE, 'offline': True}, 503


def host_status():
    check_session()
    data, code = _call('GET', '/status')
    return make_response(jsonify(data), code)


def host_action(action):
    check_session()
    if request.headers.get('Origin') != request.host_url.rstrip('/'):
        abort_with_error('Invalid origin', 403)
    if action not in ACTIONS:
        abort_with_error('Unknown action', 404)
    data, code = _call('POST', '/' + action)
    return make_response(jsonify(data), code)
