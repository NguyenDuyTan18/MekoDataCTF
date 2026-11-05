# Bằng chứng kiểm thử local

## Kết quả

- RED sau khi test import đã được cấu hình: `py -m pytest tests/test_lab.py -q` chạy được và báo lỗi thực tế ở checkout (endpoint hóa đơn chưa tồn tại) cùng lỗi cookie fixture JWT (2 failed, 1 passed). Checkout được sửa để chuyển tới hóa đơn, fixture JWT được sửa cho API Werkzeug hiện hành.
- GREEN gần nhất: `py -m pytest tests -q` → `6 passed`.
- `py -m compileall -q sandbox/app sandbox/checker tests` → hoàn tất không lỗi.
- `py -c "import yaml,pathlib; yaml.safe_load(pathlib.Path('sandbox/topology.yml').read_text()); yaml.safe_load(pathlib.Path('sandbox/provisioning/playbook.yml').read_text()); print('YAML parse OK')"` → `YAML parse OK`.
- `py package_lab.py` tạo source ZIP và Sandbox Definition ZIP; package script tự kiểm tra layout và loại trừ state/credentials/cache.
- Smoke qua HTTP local bằng Werkzeug server: health, checker PUT, checker GET → `Live local checker smoke OK`.
- Coverage chưa chạy được trong môi trường hiện tại: `coverage` không được cài (`No module named coverage`). `requirements-dev.txt` khai báo dependency để chạy lại.

## Phạm vi được kiểm tra

| Hành vi | Test |
|---|---|
| Trang chủ, tìm sản phẩm, chi tiết, lưu tủ đồ, coupon, checkout, lịch sử đơn | `test_customer_purchase_and_order_access` |
| SQLi bộ sưu tập, IDOR hóa đơn, upload trong vùng giả lập, JWT hạng hội viên, backup export | `test_five_challenges_and_patches` |
| Vá IDOR/upload/JWT/backup sau restart app | `test_five_challenges_and_patches` |
| Tick đổi flag và state giữ nguyên sau restart | `test_tick_rotates_flags_but_survives_restart` |
| Checker key và put/get flag | `test_checker_auth_and_flag_round_trip` |
| Host/group/network topology khớp | `test_topology_names_and_team_network_are_consistent` |
| Nhân viên thêm sản phẩm, cập nhật đơn | `test_staff_can_manage_products_and_orders` |

Đây là kiểm thử trên Flask test client và parse cấu hình local. Chưa chạy provision Ansible lên image Kali thật; chưa tạo/allocate pool CyberRangeCZ/OpenStack, chưa xác nhận image/flavor, GUI/SSH, routing, Apache trên máy thật hay scoring integration.
