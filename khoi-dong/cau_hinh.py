"""Đọc cau-hinh.conf (hoặc cau-hinh.bat cũ) và tự tính các giá trị còn lại.

Người dùng chỉ khai: LABS, POOL (có thể để trống), TEST_IP, WEB.
Tự tính:  COLLECTOR_LABS=LABS, MAIN_LAB=bài đầu, CHECKER_DIRS="name" trong lab.json,
          SSH_CONFIG=ops/<POOL>/management-config (hoặc ssh_config của bài đầu).

Dùng chung cho meko.py và host_bridge.py, chạy giống nhau trên Linux và Windows.
"""
import json
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FORCAD = ROOT / 'platform' / 'ForcAD-demo'
USER_KEYS = ('LABS', 'POOL', 'TEST_IP', 'WEB', 'GATEWAY_BIND')
# GATEWAY_BIND trống = tự lấy IP LAN của máy (mở ra LAN); đặt 127.0.0.1 = chỉ máy này.
DEFAULTS = {'POOL': '', 'TEST_IP': '', 'WEB': 'http://127.0.0.1:18080/', 'GATEWAY_BIND': ''}
# Host SSH (trong management-config) nằm trên mạng thi, dùng làm điểm nối cho tunnel gateway.
GATEWAY_HOP = 'checker'
# Cổng cục bộ đầu tiên; cấp tuần tự nên không trùng dù số đội/dịch vụ tăng.
GATEWAY_BASE_PORT = 20001
CONF = HERE / 'cau-hinh.conf'
LEGACY = HERE / 'cau-hinh.bat'


class ConfigError(ValueError):
    pass


def read_user_values(path=None):
    """Đọc KEY=value (cau-hinh.conf) hoặc set "KEY=value" (cau-hinh.bat cũ)."""
    path = path or (CONF if CONF.exists() else LEGACY)
    if not path.exists():
        raise ConfigError(f'Không thấy tệp cấu hình {path.name}.')
    text = path.read_text(encoding='utf-8', errors='replace')
    values = dict(DEFAULTS)
    pattern = r'^\s*set\s+"([A-Z_]+)=(.*)"\s*$' if path.suffix == '.bat' else r'^\s*([A-Z_]+)\s*=\s*(.*?)\s*$'
    for key, value in re.findall(pattern, text, flags=re.M):
        if key in USER_KEYS:
            values[key] = value.strip().strip('"')
    return values


def load(path=None):
    """Trả dict cấu hình đầy đủ; ném ConfigError (tiếng Việt) nếu khai sai."""
    v = read_user_values(path)
    labs = [lab.strip().replace('\\', '/') for lab in v.get('LABS', '').split(',') if lab.strip()]
    if not labs:
        raise ConfigError('Chưa khai LABS trong cau-hinh.conf.')
    checker_dirs, first_ssh = [], None
    for lab in labs:
        lab_json = ROOT / 'labs' / lab / 'lab.json'
        if not lab_json.is_file():
            raise ConfigError(f'LABS có "{lab}" nhưng không thấy labs/{lab}/lab.json.')
        data = json.loads(lab_json.read_text(encoding='utf-8'))
        name = data.get('name')
        if not name or not (FORCAD / 'checkers' / name).is_dir():
            raise ConfigError(f'labs/{lab}/lab.json có "name": "{name}" nhưng không thấy '
                              f'platform/ForcAD-demo/checkers/{name}/.')
        checker_dirs.append(name)
        first_ssh = first_ssh or data.get('ssh_config')
    if v['POOL']:
        ssh = ROOT / 'ops' / v['POOL'] / 'management-config'
    elif first_ssh:
        ssh = ROOT / first_ssh
    else:
        raise ConfigError('POOL để trống và lab.json của bài đầu không có "ssh_config".')
    if not ssh.is_file():
        rel = ssh.relative_to(ROOT) if ssh.is_relative_to(ROOT) else ssh
        raise ConfigError(f'Không thấy file SSH của pool: {rel}')
    web = v['WEB'] if v['WEB'].endswith('/') else v['WEB'] + '/'
    return {'ROOT': str(ROOT), 'FORCAD': str(FORCAD), 'LABS': ','.join(labs),
            'COLLECTOR_LABS': ','.join(labs), 'MAIN_LAB': labs[0],
            'CHECKER_DIRS': ' '.join(checker_dirs), 'SSH_CONFIG': str(ssh),
            'POOL': v['POOL'] or ssh.parent.name, 'TEST_IP': v['TEST_IP'], 'WEB': web,
            'GATEWAY_BIND': v['GATEWAY_BIND'].strip(), 'GATEWAY_HOP': GATEWAY_HOP}


def gateway_plan(cfg=None):
    """Mỗi (đội × cổng dịch vụ) → một cổng cục bộ, cấp TUẦN TỰ từ GATEWAY_BASE_PORT.

    Cấp tuần tự nên không bao giờ trùng dù số đội hay số dịch vụ tăng bao nhiêu.
    Đọc teams + service_ports trong lab.json. Trả [] nếu không lab nào khai service_ports.
    """
    cfg = cfg or load()
    labs = cfg['LABS'].split(',')
    plan = []
    local = GATEWAY_BASE_PORT
    for lab in labs:
        data = json.loads((ROOT / 'labs' / lab / 'lab.json').read_text(encoding='utf-8'))
        for port in data.get('service_ports') or []:
            for team in data['teams']:
                plan.append({'local': local, 'ip': team['ip'], 'port': int(port),
                             'team': team['name'], 'lab': data.get('name', lab)})
                local += 1
    return plan


if __name__ == '__main__':
    try:
        cfg = load()
    except (ConfigError, OSError, ValueError) as exc:
        print('LỖI CẤU HÌNH:', exc)
        sys.exit(1)
    width = max(map(len, cfg))
    for key, value in cfg.items():
        print(f'{key.ljust(width)} = {value}')
