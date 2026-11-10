#!/usr/bin/env python3
"""Chuyển ForcAD sang một lab/round khác QUA HTTP ADMIN API (không cần docker).

Chạy TRÊN HOST bằng Python chuẩn (không cần cài gói). Gói lại quy trình có sẵn:
    login -> (stop) -> archive -> prepare(lab) -> (start)
qua các endpoint admin: /api/admin/login, /round-control, /round1/archive, /round1/prepare.

Mặc định DRY-RUN (chỉ in kế hoạch). Thêm --yes mới thực hiện.

Ví dụ:
    python switch_round.py --to round1                     # xem kế hoạch
    python switch_round.py --to round1 --yes --stop --start # dừng, chuyển, bật luôn

Creds admin đọc từ config.yml; đổi endpoint bằng --base nếu không phải cổng 18080.
"""
import argparse
import http.cookiejar
import json
import re
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CRYPTO_LAB = 'mmoiws'
MEKO_LAB = 'meko_boutique'
FULL_WEB_LAB = 'full_rounds'
FULL_CRYPTO_LAB = 'full_rounds_crypto'
INTERMISSION_SECONDS = 600

for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass


def read_admin_creds():
    """Đọc username/password admin từ block `admin:` trong config.yml."""
    text = (ROOT / "config.yml").read_text(encoding="utf-8")
    block = re.search(r"(?ms)^admin:\s*\n((?:[ \t]+\S.*\n?)+)", text)
    if not block:
        raise SystemExit("[!] Không tìm thấy block admin trong config.yml")
    body = block.group(1)
    u = re.search(r"username:\s*(\S+)", body)
    p = re.search(r"password:\s*(\S+)", body)
    if not u or not p:
        raise SystemExit("[!] Thiếu username/password admin trong config.yml")
    return u.group(1), p.group(1)


class Admin:
    def __init__(self, base):
        self.base = base.rstrip("/")
        self.origin = self.base            # server yêu cầu Origin == host_url
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.jar))

    def call(self, path, payload=None, method="POST"):
        url = self.base + path
        data = json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        req.add_header("Origin", self.origin)
        try:
            with self.opener.open(req, timeout=15) as r:
                return r.status, r.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, e.read().decode("utf-8", "replace")
        except urllib.error.URLError as e:
            raise SystemExit(f"[!] Không kết nối {url}: {e}. Kiểm tra --base và Docker còn chạy không.")

    def status(self):
        st, body = self.call("/api/admin/round-control/", method="GET")
        if st != 200:
            raise SystemExit(f"[!] Lấy trạng thái thất bại (HTTP {st}): {body}")
        return json.loads(body)


def _msg(body):
    try:
        return json.loads(body).get("error") or json.loads(body).get("status") or body
    except (ValueError, AttributeError):
        return body


def wait_for_crypto(api, status):
    print('[i] Đang chờ Meko Boutique kết thúc và nghỉ đủ 10 phút...', flush=True)
    while True:
        state = status['round1']
        if state.get('lab') != MEKO_LAB:
            raise SystemExit('[!] Lab hiện tại đã đổi, không tự động bật Crypto AD.')
        finished_at = state.get('finished_at')
        if state.get('phase') == 'archived' and finished_at is None:
            raise SystemExit('[!] Vòng 1 được lưu trước khi kết thúc. Không có mốc để bật vòng 2.')
        if finished_at is not None and not status.get('running'):
            remaining = finished_at + INTERMISSION_SECONDS - time.time()
            if remaining <= 0:
                return status
            time.sleep(min(5, remaining))
        else:
            time.sleep(5)
        status = api.status()


def verify_crypto_collector():
    sys.path.insert(0, str(ROOT / 'checkers' / 'meko_boutique'))
    from common import rpc

    config = json.loads((ROOT.parents[1] / 'labs' / CRYPTO_LAB / 'lab.json').read_text(encoding='utf-8'))
    rpc_dir = ROOT / 'checkers' / CRYPTO_LAB / 'rpc'
    for team in config['teams']:
        result = rpc({'task': 'crypto', 'action': 'check', 'ip': team['ip']}, timeout=12, root=rpc_dir)
        if result['status'] != 101:
            raise SystemExit(f"[!] Collector Crypto AD chưa UP cho {team['name']}: {result['public']}")


def main():
    ap = argparse.ArgumentParser(description="Chuyển sang lab/round khác qua HTTP admin API (không cần docker).")
    ap.add_argument("--to", required=True, metavar="LAB", help="Tên lab đích (vd: round1, meko_boutique)")
    ap.add_argument("--base", default="http://127.0.0.1:18080", help="Gốc admin (mặc định http://127.0.0.1:18080)")
    ap.add_argument("--yes", action="store_true", help="Thực hiện thật (bỏ cờ này = chỉ in kế hoạch)")
    ap.add_argument("--stop", action="store_true", help="Tự dừng round đang chạy rồi chờ checker xong")
    ap.add_argument("--start", action="store_true", help="Bật round mới sau khi prepare")
    ap.add_argument('--activate', nargs=argparse.REMAINDER, metavar='COMMAND',
                    help='Lệnh Ansible kích hoạt Crypto AD, đặt tùy chọn này cuối cùng')
    args = ap.parse_args()
    crypto = args.to == CRYPTO_LAB
    full_crypto = args.to == FULL_CRYPTO_LAB
    if (crypto or full_crypto) and args.stop:
        ap.error('Vòng Crypto chờ vòng Web kết thúc tự nhiên. Hãy bỏ --stop.')
    if args.activate and not crypto:
        ap.error('--activate chỉ dùng khi chuyển sang mmoiws.')
    if crypto and args.yes and (not args.activate or not shutil.which(args.activate[0])):
        ap.error('Cần --activate kèm lệnh Ansible khả dụng để chuyển sang mmoiws.')

    username, password = read_admin_creds()
    api = Admin(args.base)

    st, body = api.call("/api/admin/login/", {"username": username, "password": password})
    if st != 200:
        raise SystemExit(f"[!] Đăng nhập admin thất bại (HTTP {st}): {_msg(body)}")

    status = api.status()
    running = status.get("running")
    r1 = status.get("round1", {})
    cur_lab, phase = r1.get("lab"), r1.get("phase")

    print("=== TRẠNG THÁI HIỆN TẠI ===")
    print(f"  lab={cur_lab}  phase={phase}  tick={r1.get('tick')}  running={running}  "
          f"configured={r1.get('configured')}  archive_id={r1.get('archive_id')}")
    print(f"=== ĐÍCH: lab={args.to} ===")

    if cur_lab == args.to and r1.get("configured") and phase != "archived":
        if (crypto or full_crypto) and args.yes and args.start and phase == 'ready' and not running:
            if crypto:
                verify_crypto_collector()
            st, body = api.call('/api/admin/round-control/', {'running': True})
            if st != 200:
                raise SystemExit(f'[!] Bật round thất bại (HTTP {st}): {_msg(body)}')
            print('[ok] Đã bắt đầu 10 phút xem đề Crypto.' if full_crypto else '[ok] Round 2 đã BẬT.')
            return 0
        print(f"\n[i] Đang chạy lab '{args.to}' rồi — không cần chuyển.")
        return 0

    if full_crypto and (cur_lab != FULL_WEB_LAB or phase != 'finished' or running):
        raise SystemExit('[!] Chờ vòng Web Full Rounds kết thúc rồi chuyển sang Crypto.')
    need_archive = bool(r1.get("configured")) and phase != "archived" and not full_crypto
    plan = []
    if crypto:
        plan.append('chờ Meko Boutique kết thúc và nghỉ 10 phút')
    elif running:
        plan.append("stop round" + ("" if args.stop else "  [CẦN --stop, hoặc tự dừng trước]"))
    if need_archive:
        plan.append("archive round hiện tại (lưu hồ sơ)")
    if crypto:
        plan.append('kích hoạt Crypto AD bằng Ansible và thử collector trên mọi VM')
    if full_crypto:
        plan.append('chuyển sang Crypto, giữ điểm và token đội')
    else:
        plan.append(f"prepare lab '{args.to}' (reset điểm, dựng teams/tasks, tick 0)")
    if args.start:
        plan.append("start round mới")

    print("=== KẾ HOẠCH ===")
    for i, p in enumerate(plan, 1):
        print(f"  {i}. {p}")

    if not args.yes:
        print("\n[DRY RUN] Chưa làm gì. Thêm --yes để thực hiện.")
        print(f"    Sau khi bật, nhớ chạy collector với MEKO_LAB={args.to} (BAT-FLAG.bat).")
        return 0

    # --- Thực hiện ---
    if crypto:
        status = wait_for_crypto(api, status)
        running = status.get('running')
        need_archive = status['round1']['phase'] == 'finished'
    if running:
        if not args.stop:
            print("\n[!] Round đang bật. Thêm --stop để tự dừng, hoặc dừng thủ công rồi chạy lại.")
            return 1
        st, body = api.call("/api/admin/round-control/", {"running": False})
        if st != 200:
            raise SystemExit(f"[!] Dừng round thất bại (HTTP {st}): {_msg(body)}")
        print("[ok] Đã gửi lệnh dừng. Chờ checker chuyển sang 'paused'...")
        for _ in range(40):                      # tối đa ~60s
            time.sleep(1.5)
            ph = api.status().get("round1", {}).get("phase")
            if ph in ("paused", "ready", "finished"):
                print(f"[ok] phase={ph}, có thể archive.")
                break
        else:
            raise SystemExit("[!] Checker chưa xong sau ~60s; chờ thêm rồi chạy lại với --yes.")

    if need_archive:
        st, body = api.call("/api/admin/round1/archive/", {"confirm": "ARCHIVE ROUND1"})
        if st != 200:
            raise SystemExit(f"[!] Archive thất bại (HTTP {st}): {_msg(body)}")
        print(f"[ok] Đã lưu hồ sơ round cũ: {json.loads(body).get('archive_id')}")

    if crypto:
        if subprocess.run(args.activate).returncode:
            raise SystemExit('[!] Playbook kích hoạt thất bại. Vòng 2 vẫn đang dừng.')
        verify_crypto_collector()

    st, body = api.call("/api/admin/round1/prepare/", {"confirm": "PREPARE ROUND1", "lab": args.to})
    if st != 200:
        raise SystemExit(f"[!] Prepare lab '{args.to}' thất bại (HTTP {st}): {_msg(body)}")
    print(f"[ok] Đã prepare lab '{args.to}' — " +
          ("Crypto sẵn sàng, điểm Web được giữ." if full_crypto else "phase=ready, tick 0, điểm reset."))

    if args.start:
        st, body = api.call("/api/admin/round-control/", {"running": True})
        if st != 200:
            raise SystemExit(f"[!] Bật round thất bại (HTTP {st}): {_msg(body)}")
        print("[ok] Round mới đã BẬT.")
    else:
        print("[i] Chưa bật round. Bật bằng BAT-ROUND.bat hoặc chạy lại với --start.")
    if full_crypto:
        print('[i] Collector Full Rounds tiếp tục dùng cùng cấu hình cho hai vòng.')
    else:
        print(f"[!] ĐỪNG QUÊN: chạy collector với MEKO_LAB={args.to}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
