"""Phần chuyển yêu cầu dùng chung cho mọi bài (giao thức checker của ForcAD qua hộp thư RPC).

Chép nguyên từ checkers/meko_boutique/common.py; logic không đổi. Bản ở meko_boutique/
vẫn giữ cho các bài cũ. Bài mới dùng tệp này qua checkers/_template/task.py.
"""
import ipaddress
import json
import os
from pathlib import Path
import sys
import time
import uuid

# Mỗi bài truyền root=checkers/<bài>/rpc; collect_checker.py đọc đúng thư mục đó
# và chỉ chuyển tiếp đội/lỗ hổng có trong labs/<bài>/lab.json.
ROOT = Path(__file__).resolve().parent / 'rpc'


def rpc(payload, timeout=40, root=ROOT):
    root.mkdir(parents=True, exist_ok=True)
    identity = uuid.uuid4().hex
    request = root / (identity + '.request.json')
    response = root / (identity + '.response.json')
    temporary = root / (identity + '.tmp')
    temporary.write_text(json.dumps({'id': identity, 'expires': time.time() + timeout, 'payload': payload}), encoding='utf-8')
    os.replace(temporary, request)
    try:
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if response.exists():
                data = json.loads(response.read_text(encoding='utf-8'))
                if data['id'] != identity or data['status'] not in (101, 102, 103, 104, 110):
                    raise ValueError('Invalid collector response')
                return data
            time.sleep(0.1)
        return {'status': 110, 'public': 'SSH collector unavailable', 'private': ''}
    finally:
        request.unlink(missing_ok=True)
        response.unlink(missing_ok=True)


def main(task, root=ROOT):
    try:
        action, ip = sys.argv[1:3]
        if action not in ('check', 'put', 'get'):
            raise ValueError('Invalid action/team')
        ip = str(ipaddress.IPv4Address(ip))
        payload = {'task': task, 'action': action, 'ip': ip}
        if action in ('put', 'get'):
            if len(sys.argv) != 6:
                raise ValueError('Invalid checker arguments')
            payload.update(key=sys.argv[3], locator=sys.argv[3], flag=sys.argv[4])
        result = rpc(payload, root=root)
        print(result.get('public', ''))
        print(result.get('private', ''), file=sys.stderr)
        return result['status']
    except (OSError, ValueError, KeyError, TypeError):
        print('Checker transport failed')
        return 110
