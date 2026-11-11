"""Cầu nối trên máy Windows cho nút "Bật bộ cờ" và "Collector" trong trang quản trị ForcAD.

ForcAD chạy trong Docker nên không tự bật được chương trình trên máy. Cầu nối này chạy trên máy,
CHỈ nghe ở 127.0.0.1:18090 và chỉ làm vài việc cố định:
  - bật các container liên quan tới cờ (docker compose up -d ...)
  - bật / dừng collect_checker.py
  - định kỳ thử SSH tới máy chấm để báo trạng thái
Mọi yêu cầu phải kèm header X-Bridge-Token (mã trong platform/ForcAD-demo/backend/.host-bridge-token,
admin-api đọc được vì thư mục backend được gắn vào container). Trang quản trị gọi qua admin-api.

Bài, pool... đọc từ khoi-dong/cau-hinh.bat qua cau_hinh.py (cùng cấu hình với các nút .bat).
Chạy: pythonw khoi-dong/host_bridge.py  (hoặc cai-cau-noi.bat để tự bật khi đăng nhập Windows).
"""
from datetime import datetime
import hmac
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import re
import secrets
import subprocess
import sys
import threading
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cau_hinh  # noqa: E402
import procs     # noqa: E402  (tiến trình đa nền tảng: Linux + Windows)

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FORCAD = ROOT / 'platform' / 'ForcAD-demo'
TOKEN_FILE = FORCAD / 'backend' / '.host-bridge-token'
LOG_DIR = HERE / 'logs'
COLLECTOR_LOG = LOG_DIR / 'collector.log'
BRIDGE_LOG = LOG_DIR / 'bridge.log'
HOST, PORT = '127.0.0.1', 18090
# Container ForcAD cần cho vòng đời cờ: lưu trữ, ticker (nhịp tick), celery (chạy checker cắm/lấy cờ),
# http-receiver (nhận cờ các đội nộp). admin-api/nginx đã chạy sẵn khi bấm được nút trên web.
FLAG_SERVICES = ('postgres', 'redis', 'rabbitmq', 'celery', 'ticker', 'http-receiver')
SSH_EVERY = 60

lock = threading.Lock()
state = {'job': None, 'ssh': {'ok': None, 'checked_at': None, 'message': 'Chưa kiểm tra'}}


def log(message):
    LOG_DIR.mkdir(exist_ok=True)
    with BRIDGE_LOG.open('a', encoding='utf-8') as fh:
        fh.write(f'{datetime.now():%Y-%m-%d %H:%M:%S} {message}\n')


def load_config():
    """Cấu hình đầy đủ từ cau-hinh.bat (xem cau_hinh.py). Ném cau_hinh.ConfigError nếu khai sai."""
    return cau_hinh.load()


def token():
    if not TOKEN_FILE.exists():
        TOKEN_FILE.write_text(secrets.token_hex(24), encoding='ascii')
    return TOKEN_FILE.read_text(encoding='ascii').strip()


run = procs.run


def collector_pids():
    """Mọi tiến trình collect_checker.py đang chạy (kể cả bật bằng CLI), không chỉ do cầu nối bật."""
    return procs.find_pids('collect_checker.py')


def log_tail(path, lines=15):
    try:
        return path.read_text(encoding='utf-8', errors='replace').splitlines()[-lines:]
    except OSError:
        return []


def services():
    try:
        out = run(['docker', 'ps', '-a', '--filter', 'name=forcad-demo-', '--format', '{{.Names}}|{{.State}}'],
                  timeout=20).stdout
    except (OSError, subprocess.TimeoutExpired):
        return None
    found = dict(line.split('|', 1) for line in out.splitlines() if '|' in line)
    return {name: found.get(f'forcad-demo-{name}-1', 'missing') for name in FLAG_SERVICES}


def check_ssh():
    try:
        cfg = load_config()
    except (cau_hinh.ConfigError, OSError, ValueError) as exc:
        state['ssh'] = {'ok': False, 'checked_at': time.time(), 'message': f'Cấu hình lỗi: {exc}'[:200]}
        return False
    try:
        proc = run(['ssh', '-F', cfg['SSH_CONFIG'], '-o', 'ConnectTimeout=15', '-o', 'BatchMode=yes',
                    'checker', 'echo SSH_OK'], timeout=40)
        ok = 'SSH_OK' in proc.stdout
        message = 'SSH tới máy chấm OK' if ok else (proc.stderr.strip().splitlines() or ['SSH lỗi'])[-1]
    except (OSError, subprocess.TimeoutExpired) as exc:
        ok, message = False, f'SSH lỗi: {type(exc).__name__}'
    state['ssh'] = {'ok': ok, 'checked_at': time.time(), 'message': message[:200]}
    return ok


def ssh_loop():
    while True:
        try:
            check_ssh()
        except Exception as exc:  # không để luồng nền chết
            log(f'ssh check failed: {exc!r}')
        time.sleep(SSH_EVERY)


def start_collector():
    if collector_pids():
        return 'Collector đã chạy sẵn.'
    cfg = load_config()
    env = {**os.environ, 'MEKO_SSH_CONFIG': cfg['SSH_CONFIG'], 'MEKO_LAB': cfg['MAIN_LAB'], 'PYTHONUNBUFFERED': '1'}
    LOG_DIR.mkdir(exist_ok=True)
    with COLLECTOR_LOG.open('a', encoding='utf-8') as fh:
        fh.write(f'\n===== {datetime.now():%Y-%m-%d %H:%M:%S} bật collector: {cfg["COLLECTOR_LABS"]} =====\n')
        fh.flush()
        procs.spawn_background([procs.python_exe(), str(FORCAD / 'collect_checker.py'),
                                '--rpc-only', '--labs', cfg['COLLECTOR_LABS']], ROOT, env, fh)
    time.sleep(4)
    if not collector_pids():
        raise RuntimeError('Collector tắt ngay sau khi bật. Xem log: ' + ' | '.join(log_tail(COLLECTOR_LOG, 3)))
    return 'Đã bật collector.'


def stop_collector():
    pids = collector_pids()
    if not pids:
        return 'Collector không chạy.'
    procs.kill_pids(pids)
    time.sleep(1)
    if collector_pids():
        raise RuntimeError('Không dừng được collector.')
    with COLLECTOR_LOG.open('a', encoding='utf-8') as fh:
        fh.write(f'===== {datetime.now():%Y-%m-%d %H:%M:%S} đã dừng collector =====\n')
    return f'Đã dừng collector ({len(pids)} tiến trình).'


def start_flag_system():
    steps = []
    proc = run(['docker', 'compose', '-f', str(FORCAD / 'docker-compose.yml'), 'up', '-d', *FLAG_SERVICES],
               timeout=300, cwd=str(FORCAD))
    if proc.returncode != 0:
        raise RuntimeError('docker compose lỗi: ' + (proc.stderr.strip().splitlines() or ['?'])[-1])
    bad = {k: v for k, v in (services() or {}).items() if v != 'running'}
    if bad:
        raise RuntimeError('Container chưa chạy: ' + ', '.join(f'{k}={v}' for k, v in bad.items()))
    steps.append('Dịch vụ cờ đã chạy.')
    if not check_ssh():
        steps.append('CẢNH BÁO: ' + state['ssh']['message'] + ' — collector vẫn bật nhưng sẽ không cắm được cờ.')
    steps.append(start_collector())
    return ' '.join(steps)


def start_gateway():
    import meko
    return meko.gateway_start(load_config())


def stop_gateway():
    import meko
    return meko.gateway_stop(load_config())


def gateway_info():
    """Trạng thái gateway cho /status: đang chạy + bảng cổng (local -> đội/dịch vụ)."""
    import meko
    try:
        cfg = load_config()
        pid = meko._gateway_pid()
        plan = meko.cau_hinh.gateway_plan(cfg)
        _, host = meko.gateway_bind_display(cfg)
        ports = [{'url': f'{host}:{row["local"]}', 'target': f'{row["team"]} {row["lab"]}:{row["port"]}'} for row in plan]
        return {'running': bool(pid), 'pid': pid, 'host': host, 'ports': ports}
    except Exception as exc:
        return {'running': False, 'pid': None, 'ports': [], 'error': str(exc)}


ACTIONS = {'flag-system/start': ('Bật bộ cờ', start_flag_system),
           'collector/start': ('Bật collector', start_collector),
           'collector/stop': ('Dừng collector', stop_collector),
           'gateway/start': ('Bật gateway', start_gateway),
           'gateway/stop': ('Dừng gateway', stop_gateway)}


def run_job(name, label, func):
    try:
        message, ok = func(), True
    except Exception as exc:
        message, ok = str(exc) or type(exc).__name__, False
    log(f'{name}: {"OK" if ok else "LỖI"} {message}')
    with lock:
        state['job'].update(state='done' if ok else 'failed', message=message, finished_at=time.time())


def status():
    try:
        cfg, config_error = load_config(), None
    except (cau_hinh.ConfigError, OSError, ValueError) as exc:
        cfg, config_error = {}, str(exc)
    pids = collector_pids()
    return {'bridge': 'ok', 'labs': cfg.get('COLLECTOR_LABS'), 'pool': cfg.get('POOL'), 'config_error': config_error,
            'services': services(), 'collector': {'running': bool(pids), 'pids': pids, 'log': log_tail(COLLECTOR_LOG)},
            'gateway': gateway_info(), 'ssh': state['ssh'], 'job': state['job']}


class Handler(BaseHTTPRequestHandler):
    def reply(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def authorized(self):
        if hmac.compare_digest(self.headers.get('X-Bridge-Token', ''), token()):
            return True
        self.reply(403, {'error': 'Sai mã cầu nối.'})
        return False

    def do_GET(self):
        if not self.authorized():
            return
        if self.path != '/status':
            return self.reply(404, {'error': 'Không có'})
        self.reply(200, status())

    def do_POST(self):
        if not self.authorized():
            return
        name = self.path.strip('/')
        if name not in ACTIONS:
            return self.reply(404, {'error': 'Không có thao tác này'})
        label, func = ACTIONS[name]
        with lock:
            job = state['job']
            if job and job['state'] == 'running':
                return self.reply(409, {'error': f'Đang chạy: {job["label"]}. Chờ xong rồi bấm lại.'})
            state['job'] = {'name': name, 'label': label, 'state': 'running', 'message': '',
                            'started_at': time.time(), 'finished_at': None}
        threading.Thread(target=run_job, args=(name, label, func), daemon=True).start()
        self.reply(202, {'status': 'started', 'label': label})

    def log_message(self, *args):
        pass


def main():
    token()
    try:
        server = ThreadingHTTPServer((HOST, PORT), Handler)
    except OSError:
        log('cổng 18090 đã dùng — cầu nối đã chạy sẵn, thoát.')
        return
    threading.Thread(target=ssh_loop, daemon=True).start()
    log(f'cầu nối chạy ở {HOST}:{PORT}')
    server.serve_forever()


if __name__ == '__main__':
    main()
