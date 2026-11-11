#!/usr/bin/env python3
"""Tệp chuyển yêu cầu của ForcAD. Tên tệp = tên lỗ hổng, thư mục chứa tệp = tên bài.

Không sửa nội dung: tạo lỗ hổng mới bằng cách chép tệp này và đặt tên theo lỗ hổng.
Mẫu gốc: checkers/_template/task.py. Phần chung: checkers/_shared/forcad_rpc.py.
"""
from pathlib import Path
import sys

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent.parent / '_shared'))
from forcad_rpc import main

if __name__ == '__main__':
    raise SystemExit(main(HERE.stem, root=HERE.parent / 'rpc'))
