"""Thao tác tiến trình đa nền tảng cho meko.py và host_bridge.py.

Tự chọn cách làm theo hệ điều hành: Windows dùng PowerShell/taskkill, Linux/macOS dùng pgrep/kill.
"""
import os
import signal
import subprocess
import sys
import time
import webbrowser

IS_WINDOWS = os.name == 'nt'
# Cửa sổ ẩn + nhóm tiến trình riêng khi chạy nền (chỉ Windows).
_NO_WINDOW = getattr(subprocess, 'CREATE_NO_WINDOW', 0) if IS_WINDOWS else 0
_NEW_GROUP = getattr(subprocess, 'CREATE_NEW_PROCESS_GROUP', 0) if IS_WINDOWS else 0


def run(args, timeout=180, **kwargs):
    """subprocess.run, không mở cửa sổ phụ trên Windows."""
    flags = _NO_WINDOW if IS_WINDOWS else 0
    return subprocess.run(args, capture_output=True, text=True, encoding='utf-8',
                          errors='replace', timeout=timeout, creationflags=flags, **kwargs)


def find_pids(needle):
    """PID của các tiến trình python có chuỗi `needle` trong dòng lệnh (vd 'collect_checker.py')."""
    try:
        if IS_WINDOWS:
            script = ("Get-CimInstance Win32_Process -Filter \"Name like 'python%'\" | "
                      f"Where-Object {{ $_.CommandLine -like '*{needle}*' }} | "
                      "ForEach-Object { $_.ProcessId }")
            out = run(['powershell', '-NoProfile', '-Command', script], timeout=20).stdout
        else:
            out = run(['pgrep', '-f', needle], timeout=20).stdout
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [int(x) for x in out.split() if x.isdigit()]


def kill_pids(pids):
    """Dừng các PID (kèm tiến trình con)."""
    for pid in pids:
        try:
            if IS_WINDOWS:
                run(['taskkill', '/PID', str(pid), '/T', '/F'], timeout=20)
            else:
                os.kill(pid, signal.SIGTERM)
        except (OSError, subprocess.TimeoutExpired):
            pass
    if not IS_WINDOWS:
        time.sleep(1)
        for pid in pids:
            try:
                os.kill(pid, signal.SIGKILL)
            except OSError:
                pass


def spawn_background(args, cwd, env, log_handle):
    """Chạy một tiến trình nền, tách khỏi tiến trình cha, ghi log vào log_handle."""
    kwargs = dict(cwd=str(cwd), env=env, stdout=log_handle, stderr=subprocess.STDOUT,
                  stdin=subprocess.DEVNULL)
    if IS_WINDOWS:
        kwargs['creationflags'] = _NO_WINDOW | _NEW_GROUP
    else:
        kwargs['start_new_session'] = True
    return subprocess.Popen(args, **kwargs)


def pid_alive(pid):
    """True nếu PID còn chạy (đa nền tảng)."""
    try:
        if IS_WINDOWS:
            out = run(['tasklist', '/FI', f'PID eq {pid}', '/NH'], timeout=15).stdout
            return str(pid) in out
        os.kill(pid, 0)
        return True
    except (OSError, subprocess.TimeoutExpired):
        return False


def python_exe():
    """Trình python để chạy tiến trình nền (tránh pythonw để vẫn ghi được log)."""
    return sys.executable.replace('pythonw.exe', 'python.exe')


def open_url(url):
    try:
        webbrowser.open(url)
    except Exception:
        pass


def lan_ip():
    """IP LAN chính của máy (địa chỉ dùng để ra ngoài), không phải 127.0.0.1."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(('8.8.8.8', 80))      # không gửi gói, chỉ để lấy IP interface định tuyến
        return s.getsockname()[0]
    except OSError:
        try:
            return socket.gethostbyname(socket.gethostname())
        except OSError:
            return '127.0.0.1'
    finally:
        s.close()
