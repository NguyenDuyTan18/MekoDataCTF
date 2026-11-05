#!/usr/bin/env python3
"""Đóng gói Meko Boutique thành hai ZIP:

- meko-boutique-sandbox.zip: gốc Sandbox Definition cho CyberRangeCZ.
  Giải nén ra có topology.yml, provisioning/, app/, checker/ ngay tại gốc.
- meko-boutique-source.zip: toàn bộ source, test, tài liệu và script đóng gói.

Cả hai loại bỏ runtime (SQLite/state/flags/patches), .venv, cache và file tạm.
Credential nằm trong group_vars/all.yml vẫn được giữ trong gói (theo yêu cầu cấu hình sẵn);
không commit gói ra nơi công khai.
"""
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SANDBOX = ROOT / "sandbox"

SKIP_DIRS = {".venv", "__pycache__", ".pytest_cache", ".runtime", "simulation",
             ".git", "htmlcov"}
SKIP_SUFFIX = {".pyc", ".zip"}
SKIP_NAMES = {"shop.sqlite3", "catalog.sqlite3", "state.json", "patches.json", ".coverage"}


def keep(path: Path) -> bool:
    parts = set(path.parts)
    if parts & SKIP_DIRS or any(p.startswith(".qa-") or p.startswith(".browser-profile") for p in path.parts):
        return False
    if path.name in SKIP_NAMES or path.suffix in SKIP_SUFFIX:
        return False
    return True


def add_tree(zf: zipfile.ZipFile, base: Path, arc_prefix: str = ""):
    for f in sorted(base.rglob("*")):
        if not f.is_file() or not keep(f.relative_to(base)):
            continue
        arcname = (arc_prefix + "/" if arc_prefix else "") + str(f.relative_to(base)).replace("\\", "/")
        zf.write(f, arcname)


def build_sandbox_zip():
    out = ROOT / "meko-boutique-sandbox.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        add_tree(zf, SANDBOX)  # topology.yml, provisioning/, app/, checker/ ở gốc
    return out


def build_source_zip():
    out = ROOT / "meko-boutique-source.zip"
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        add_tree(zf, ROOT, "meko-boutique")
    return out


if __name__ == "__main__":
    import sys
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    s = build_sandbox_zip()
    src = build_source_zip()
    print(f"[OK] {s.name} ({s.stat().st_size // 1024} KB)")
    print(f"[OK] {src.name} ({src.stat().st_size // 1024} KB)")
