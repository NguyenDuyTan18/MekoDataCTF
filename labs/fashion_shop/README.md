# Fashion Shop · Meko Boutique

Bài lab attack/defense dạng web cho nền tảng **CyberRangeCZ**: website thương mại thời trang
tiếng Việt **Meko Boutique**, dữ liệu riêng theo từng đội, năm nhóm lỗ hổng ứng dụng web có
kiểm soát. Giao diện mua sắm không hiển thị thông tin CTF hay flag.

## Nội dung

```
sandbox/
  app/                 Flask backend + giao diện responsive + ảnh SVG + dữ liệu seed
  topology.yml         Sandbox Definition: 3 đội Kali + gateway
  provisioning/        playbook, group_vars (mật khẩu cấu hình sẵn), trainee-access
  checker/check.py     CLI health/get/put flag qua API có khóa
tests/test_lab.py      Kiểm thử chức năng + 5 thử thách (chạy local)
docs/THI-SINH.md       Hướng dẫn thí sinh (không có lời giải)
docs/GIANG-VIEN.md     Câu chuyện, flag, khai thác, vá, vận hành (nội bộ)
docs/DEPLOYMENT.md     Triển khai CyberRangeCZ, pool, mật khẩu, nghiệm thu
package_lab.py         Tạo ZIP sandbox và ZIP source
```

## Ứng dụng

Meko Boutique có: trang chủ, danh mục, tìm kiếm, chi tiết sản phẩm; đăng ký/đăng nhập/hồ sơ;
giỏ hàng, mã giảm giá, đặt hàng, lịch sử đơn và hóa đơn; bộ sưu tập cá nhân; hạng thành viên;
studio phối đồ; và khu nhân viên quản lý sản phẩm/đơn hàng. Giao diện tiếng Việt, responsive,
ảnh sản phẩm SVG offline, dữ liệu mẫu tĩnh.

## Năm thử thách

| Nhóm | Chức năng | Cơ chế (chi tiết trong docs/GIANG-VIEN.md) |
|---|---|---|
| SQL Injection | `/collections/search` | Nối chuỗi SQL trong catalog bộ sưu tập |
| IDOR | `/account/orders/<id>/invoice` | Thiếu kiểm tra chủ sở hữu đơn hàng |
| Upload | `/outfits/new` | `preview_file` trong manifest JSON, giới hạn trong vùng `simulation` |
| JWT | `/member/benefits` | Chấp nhận token `alg=none` để giả mạo hạng hội viên |
| Backup | `/exports/operations.sql` | Bản xuất vận hành bị công khai (gợi ý trong `robots.txt`) |

Flag `FLAG{...}` đổi theo tick (mặc định 120s). Lỗ hổng upload chỉ cho đọc trong dữ liệu giả lập,
**không** truy cập tùy ý hệ thống host.

## Chạy local (Windows)

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:TEAM_ID = 'team1'
$env:MEKO_DATA = "$PWD\.runtime\team1"
$env:MEKO_STAFF_PASSWORD = 'MekoStaff@2026-ops'
Set-Location sandbox/app
..\..\.venv\Scripts\python.exe app.py
```

Mở http://127.0.0.1:8080 → **Đăng ký** → **Đăng nhập**. Dùng thư mục `MEKO_DATA` riêng cho mỗi đội.
Trên Linux: `python3 -m venv .venv`, `pip install -r requirements.txt`, rồi `python sandbox/app/app.py`.

## Kiểm thử và đóng gói

```powershell
py -m pip install -r requirements-dev.txt
py -m pytest tests -q
py package_lab.py
```

`package_lab.py` tạo `meko-boutique-sandbox.zip` (gốc Sandbox Definition) và
`meko-boutique-source.zip` (toàn bộ source + tài liệu). Loại bỏ runtime, flag, cache, `.venv`.

## Triển khai CyberRangeCZ

Ba đội Kali `team1`–`team3`, IP `10.90.0.11`–`10.90.0.13`, một LAN và router gateway. Mật khẩu
SSH/nhân viên **cấu hình sẵn** trong `sandbox/provisioning/group_vars/all.yml`; **SSH bằng password**;
tài khoản `kali` mặc định **bị khóa**. Yêu cầu image/flavor/quota/GUI Access và chính sách mạng xem
`docs/DEPLOYMENT.md`. Local tests không thay cho nghiệm thu trên pool CyberRange/OpenStack.
