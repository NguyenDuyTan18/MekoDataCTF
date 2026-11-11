"""Cài/gỡ cầu nối host_bridge.py tự khởi động khi đăng nhập (Linux + Windows).

Windows: lối tắt trong thư mục Startup của tài khoản (không cần quyền quản trị).
Linux:   tệp .desktop trong ~/.config/autostart (môi trường desktop), áp dụng khi đăng nhập đồ họa.
"""
import os
from pathlib import Path
import subprocess
import sys

import procs

HERE = Path(__file__).resolve().parent
BRIDGE = HERE / 'host_bridge.py'
NAME = 'MekoDataCTF cau noi'


def _win_shortcut():
    return Path(os.environ['APPDATA']) / 'Microsoft/Windows/Start Menu/Programs/Startup' / (NAME + '.lnk')


def _linux_desktop():
    return Path.home() / '.config/autostart/mekodata-bridge.desktop'


def install():
    if procs.IS_WINDOWS:
        pyw = sys.executable.replace('python.exe', 'pythonw.exe')
        link = _win_shortcut()
        link.parent.mkdir(parents=True, exist_ok=True)
        ps = (f"$s=(New-Object -ComObject WScript.Shell).CreateShortcut('{link}');"
              f"$s.TargetPath='{pyw}';$s.Arguments='\"{BRIDGE}\"';"
              f"$s.WorkingDirectory='{HERE}';$s.WindowStyle=7;$s.Save()")
        subprocess.run(['powershell', '-NoProfile', '-Command', ps], check=True)
        print('Đã cài tự khởi động (Windows Startup):', link)
    else:
        path = _linux_desktop()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            '[Desktop Entry]\nType=Application\nName=MekoDataCTF bridge\n'
            f'Exec={procs.python_exe()} "{BRIDGE}"\nX-GNOME-Autostart-enabled=true\n',
            encoding='utf-8')
        print('Đã cài tự khởi động (Linux autostart):', path)
    # Bật ngay một lần
    procs.spawn_background([procs.python_exe(), str(BRIDGE)], HERE, dict(os.environ),
                           subprocess.DEVNULL)
    print('Cầu nối đã bật (127.0.0.1:18090).')


def remove():
    link = _win_shortcut() if procs.IS_WINDOWS else _linux_desktop()
    if link.exists():
        link.unlink()
        print('Đã gỡ tự khởi động:', link)
    else:
        print('Chưa cài tự khởi động.')
    procs.kill_pids(procs.find_pids('host_bridge.py'))
    print('Đã tắt cầu nối (nếu đang chạy).')


if __name__ == '__main__':
    (remove if '--remove' in sys.argv else install)()
