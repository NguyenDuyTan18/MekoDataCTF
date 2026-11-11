#!/usr/bin/env python3
"""Bộ bật/tắt MekoDataCTF — chạy giống nhau trên Linux và Windows.

Tự nhận diện hệ điều hành rồi gọi đúng lệnh cho từng việc (Docker, collector, round).
Cấu hình: khoi-dong/cau-hinh.conf. Xem lệnh:  python meko.py --help

Lệnh:
  config               In cấu hình đã tính (bài, pool, SSH...).
  status               Trạng thái tổng: Docker, collector, round.
  server               Bật toàn bộ ForcAD (Docker) + cập nhật schema.
  stop-server          Tắt ForcAD (giữ dữ liệu).
  flag                 Bật "bộ cờ": dịch vụ cờ trong Docker + collector.
  collector start|stop|status
  round  status|start [lab]|stop
  check                Chạy `check` mọi bộ chấm với một đội (phải 101).
  all                  server + flag + mở trang web.
  bridge [install|remove]   Cầu nối cho nút trên web /admin/.
"""
import argparse
import os
from pathlib import Path
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cau_hinh           # noqa: E402
import procs              # noqa: E402

LOG_DIR = Path(__file__).resolve().parent / 'logs'
COLLECTOR_LOG = LOG_DIR / 'collector.log'
GATEWAY_LOG = LOG_DIR / 'gateway.log'
GATEWAY_PID = LOG_DIR / 'gateway.pid'
FLAG_SERVICES = ('postgres', 'redis', 'rabbitmq', 'celery', 'ticker', 'http-receiver')


def cfg():
    try:
        return cau_hinh.load()
    except (cau_hinh.ConfigError, OSError, ValueError) as exc:
        sys.exit(f'LỖI CẤU HÌNH: {exc}\n  Sửa khoi-dong/cau-hinh.conf rồi chạy lại.')


def compose(c, *args, **kwargs):
    return procs.run(['docker', 'compose', '-f', str(Path(c['FORCAD']) / 'docker-compose.yml'), *args],
                     cwd=c['FORCAD'], **kwargs)


# ---- collector --------------------------------------------------------------
def collector_pids():
    return procs.find_pids('collect_checker.py')


def collector_start(c):
    if collector_pids():
        print('Collector đã chạy sẵn.')
        return
    LOG_DIR.mkdir(exist_ok=True)
    env = {**os.environ, 'MEKO_SSH_CONFIG': c['SSH_CONFIG'], 'MEKO_LAB': c['MAIN_LAB'], 'PYTHONUNBUFFERED': '1'}
    with COLLECTOR_LOG.open('a', encoding='utf-8') as fh:
        fh.write(f'\n===== {time.strftime("%Y-%m-%d %H:%M:%S")} bật collector: {c["COLLECTOR_LABS"]} =====\n')
        fh.flush()
        procs.spawn_background([procs.python_exe(), str(Path(c['FORCAD']) / 'collect_checker.py'),
                                '--rpc-only', '--labs', c['COLLECTOR_LABS']], c['ROOT'], env, fh)
    time.sleep(4)
    print('Đã bật collector.' if collector_pids() else 'Collector tắt ngay sau khi bật — xem logs/collector.log.')


def collector_stop():
    pids = collector_pids()
    if not pids:
        print('Collector không chạy.')
        return
    procs.kill_pids(pids)
    time.sleep(1)
    print('Đã dừng collector.' if not collector_pids() else 'Không dừng được collector.')


def collector_status():
    pids = collector_pids()
    print(f'Collector: {"đang chạy (PID " + ", ".join(map(str, pids)) + ")" if pids else "đã dừng"}')


# ---- gateway trung gian (ssh -L, mỗi dịch vụ VM một cổng cục bộ) -------------
def _gateway_pid():
    try:
        pid = int(GATEWAY_PID.read_text())
        return pid if procs.pid_alive(pid) else None
    except (OSError, ValueError):
        return None


def gateway_bind_display(c):
    """(địa_chỉ_bind, host_hiển_thị). GATEWAY_BIND trống = lấy IP LAN của máy (không dùng localhost)."""
    bind = c['GATEWAY_BIND']
    ip = procs.lan_ip()
    if not bind:
        return ip, ip                        # tự: bind + hiển thị IP máy
    if bind == '127.0.0.1':
        return '127.0.0.1', 'localhost'
    if bind == '0.0.0.0':
        return '0.0.0.0', ip                 # mở mọi card mạng, hiển thị IP máy
    return bind, bind


def gateway_forwards(c):
    """Danh sách -L cho ssh, và bảng để in."""
    plan = cau_hinh.gateway_plan(c)
    bind, _ = gateway_bind_display(c)
    flags = []
    for row in plan:
        flags += ['-L', f'{bind}:{row["local"]}:{row["ip"]}:{row["port"]}']
    return plan, flags


def gateway_start(c):
    """Bật tunnel. Trả thông báo; ném RuntimeError nếu lỗi (để cầu nối web dùng được)."""
    if _gateway_pid():
        return 'Gateway đã chạy sẵn.'
    plan, flags = gateway_forwards(c)
    if not plan:
        raise RuntimeError('Không có dịch vụ nào để mở. Thêm "service_ports" vào labs/<bài>/lab.json.')
    LOG_DIR.mkdir(exist_ok=True)
    # SSH trên Windows nuốt dấu "\" trong đường dẫn config -> dùng gạch chéo xuôi (như collector/labconfig).
    ssh_cfg = Path(c['SSH_CONFIG']).as_posix()
    args = (['ssh', '-F', ssh_cfg, '-N', '-o', 'ExitOnForwardFailure=yes',
             '-o', 'ServerAliveInterval=30', '-o', 'ServerAliveCountMax=3'] + flags + [c['GATEWAY_HOP']])
    with GATEWAY_LOG.open('a', encoding='utf-8') as fh:
        fh.write(f'\n===== {time.strftime("%Y-%m-%d %H:%M:%S")} bật gateway ({len(plan)} cổng) =====\n')
        fh.flush()
        proc = procs.spawn_background(args, c['ROOT'], dict(os.environ), fh)
    GATEWAY_PID.write_text(str(proc.pid))
    time.sleep(4)
    if not _gateway_pid():
        raise RuntimeError('Gateway tắt ngay sau khi bật (SSH tới pool lỗi?). Xem logs/gateway.log.')
    _, host = gateway_bind_display(c)
    return f'Đã bật gateway ({len(plan)} cổng) ở {host}.'


def gateway_stop(c=None):
    pid = _gateway_pid()
    if not pid:
        GATEWAY_PID.unlink(missing_ok=True)
        return 'Gateway không chạy.'
    procs.kill_pids([pid])
    GATEWAY_PID.unlink(missing_ok=True)
    return 'Đã dừng gateway.'


def gateway_print(c, plan=None):
    plan = plan if plan is not None else cau_hinh.gateway_plan(c)
    _, host = gateway_bind_display(c)
    for row in plan:
        print(f'  {host}:{row["local"]:<6} -> {row["team"]} {row["lab"]}:{row["port"]}  ({row["ip"]}:{row["port"]})')


def gateway(c, args):
    action = args.gateway_action or 'status'
    if action == 'start':
        try:
            print(gateway_start(c))
            gateway_print(c)
        except RuntimeError as exc:
            sys.exit(str(exc))
    elif action == 'stop':
        print(gateway_stop(c))
    else:
        pid = _gateway_pid()
        print(f'Gateway: {"đang chạy (PID " + str(pid) + ")" if pid else "đã dừng"}')
        gateway_print(c)


# ---- ssh --------------------------------------------------------------------
def ssh_ok(c):
    try:
        r = procs.run(['ssh', '-F', Path(c['SSH_CONFIG']).as_posix(), '-o', 'ConnectTimeout=15',
                       '-o', 'BatchMode=yes', 'checker', 'echo SSH_OK'], timeout=40)
        return 'SSH_OK' in r.stdout, (r.stderr.strip().splitlines() or [''])[-1]
    except (OSError, Exception) as exc:
        return False, str(exc)


# ---- server -----------------------------------------------------------------
def server(c, _args=None):
    if procs.run(['docker', 'version'], timeout=30).returncode != 0:
        sys.exit('Docker chưa chạy. Bật Docker (Desktop/daemon) rồi chạy lại.')
    print('Khởi động ForcAD (Docker)...')
    if compose(c, 'up', '-d', timeout=600).returncode != 0:
        sys.exit('Lỗi docker compose up. Xem: docker compose logs')
    print('Chờ database...')
    for _ in range(30):
        if compose(c, 'exec', '-T', 'postgres', 'pg_isready', '-U', 'forcad', timeout=20).returncode == 0:
            break
        time.sleep(2)
    else:
        sys.exit('Database chưa sẵn sàng. Xem: docker compose logs postgres')
    print('Cập nhật schema...')
    if compose(c, 'exec', '-T', 'ticker', 'python', '/app/scripts/setup_round1.py', timeout=120).returncode != 0:
        sys.exit('Lỗi cập nhật schema.')
    print(f'XONG. Server chạy: {c["WEB"]}')


def stop_server(c, _args=None):
    compose(c, 'stop', timeout=120)
    print('Đã tắt server (dữ liệu vẫn giữ).')


def flag(c, _args=None):
    print('Bật dịch vụ cờ...')
    if compose(c, 'up', '-d', *FLAG_SERVICES, timeout=300).returncode != 0:
        sys.exit('Lỗi bật dịch vụ cờ.')
    ok, msg = ssh_ok(c)
    print('SSH máy chấm: OK' if ok else f'SSH máy chấm: LỖI ({msg}) — collector vẫn bật nhưng chưa cắm được cờ.')
    collector_start(c)


# ---- round ------------------------------------------------------------------
def round_cmd(c, args):
    sub = args.round_action
    switch = [procs.python_exe(), str(Path(c['FORCAD']) / 'switch_round.py')]
    if sub == 'status':
        os.execvp(switch[0], switch + ['--to', c['MAIN_LAB']])
    elif sub == 'start':
        lab = args.lab or c['MAIN_LAB']
        os.execvp(switch[0], switch + ['--to', lab, '--yes', '--stop', '--start'])
    elif sub == 'stop':
        os.execvp(switch[0], switch + ['--to', c['MAIN_LAB'], '--yes', '--stop'])


# ---- check ------------------------------------------------------------------
def check(c, _args=None):
    print(f'Kiểm tra bộ chấm với đội {c["TEST_IP"]} (101 = DAT)...')
    shell = (f'cd /checkers && for d in {c["CHECKER_DIRS"]}; do for f in $d/*.py; do '
             f'(python $f check {c["TEST_IP"]} >/dev/null 2>&1; r=$?; '
             f'[ $r = 101 ] && s=DAT || s=LOI; echo "  $s $r $f") & done; done; wait')
    r = procs.run(['docker', 'exec', 'forcad-demo-celery-1', 'sh', '-c', shell], timeout=300)
    print(r.stdout or r.stderr or 'Không chạy được (server đã bật chưa?).')


# ---- status -----------------------------------------------------------------
def status(c, _args=None):
    print(f'Hệ điều hành : {"Windows" if procs.IS_WINDOWS else "Linux/Unix"}')
    print(f'Bài / pool   : {c["LABS"]}  ·  {c["POOL"]}')
    r = procs.run(['docker', 'ps', '--filter', 'name=forcad-demo-', '--format', '{{.Names}}'], timeout=20)
    names = [n for n in r.stdout.split() if n]
    print(f'ForcAD       : {len(names)} container đang chạy' if names else 'ForcAD       : CHƯA chạy (meko server)')
    collector_status()
    gpid = _gateway_pid()
    print(f'Gateway      : {"đang chạy (PID " + str(gpid) + ")" if gpid else "đã dừng"}')
    ok, msg = ssh_ok(c)
    print(f'SSH máy chấm : {"OK" if ok else "LỖI — " + msg}')


# ---- bridge -----------------------------------------------------------------
def bridge(c, args):
    import install_bridge
    if args.bridge_action == 'install':
        install_bridge.install()
    elif args.bridge_action == 'remove':
        install_bridge.remove()
    else:
        import host_bridge
        host_bridge.main()


def all_up(c, _args=None):
    server(c)
    flag(c)
    procs.open_url(c['WEB'])
    print('Mở trang điều khiển. Giữ máy chạy; mở round ở /admin/ hoặc: meko round start')


def main():
    p = argparse.ArgumentParser(description='Bộ bật/tắt MekoDataCTF (Linux + Windows)')
    sub = p.add_subparsers(dest='cmd', required=True)
    for name in ('config', 'status', 'server', 'stop-server', 'flag', 'check', 'all'):
        sub.add_parser(name)
    col = sub.add_parser('collector'); col.add_argument('collector_action', choices=['start', 'stop', 'status'])
    gw = sub.add_parser('gateway'); gw.add_argument('gateway_action', nargs='?', choices=['start', 'stop', 'status'])
    rnd = sub.add_parser('round'); rnd.add_argument('round_action', choices=['status', 'start', 'stop'])
    rnd.add_argument('lab', nargs='?')
    br = sub.add_parser('bridge'); br.add_argument('bridge_action', nargs='?', choices=['install', 'remove'])
    args = p.parse_args()

    if args.cmd == 'config':
        return os.execvp(procs.python_exe(), [procs.python_exe(), str(Path(__file__).parent / 'cau_hinh.py')])
    c = cfg()
    table = {'status': status, 'server': server, 'stop-server': stop_server, 'flag': flag,
             'check': check, 'all': all_up, 'round': round_cmd, 'bridge': bridge, 'gateway': gateway}
    if args.cmd == 'collector':
        return {'start': lambda: collector_start(c), 'stop': collector_stop,
                'status': collector_status}[args.collector_action]()
    table[args.cmd](c, args)


if __name__ == '__main__':
    main()
