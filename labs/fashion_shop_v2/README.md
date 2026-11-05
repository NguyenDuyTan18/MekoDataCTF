# Fashion Shop V2 · Meko Boutique

Đồ án tốt nghiệp dạng CyberRange: website thương mại thời trang tiếng Việt, dữ liệu riêng theo đội và năm thử thách ứng dụng web. Đây là source mới trong `labs/fashion_shop_v2`; không ghi đè Fashion Shop cũ.

## Thành phần

- `sandbox/app/`: Flask backend, giao diện responsive, SVG sản phẩm và dữ liệu seed tĩnh.
- `sandbox/topology.yml`, `sandbox/provisioning/`: Sandbox Definition cho CyberRangeCZ.
- `sandbox/checker/`: CLI health/put/get flag qua API có khóa.
- `tests/`: kiểm thử chức năng local; dữ liệu test nằm trong thư mục tạm.
- `docs/THI-SINH.md`: hướng dẫn thí sinh, không có lời giải.
- `docs/GIANG-VIEN.md`: câu chuyện, flag, khai thác, vá và vận hành.
- `docs/DEPLOYMENT.md`: cấu hình, pool, log và giới hạn nghiệm thu.

## Chạy local

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
$env:TEAM_ID = 'team1'
$env:MEKO_DATA = "$PWD\.runtime\team1"
Set-Location sandbox/app
..\..\.venv\Scripts\python.exe app.py
```

Mở http://127.0.0.1:8080. Tạo tài khoản cửa hàng để mua; tạo thư mục `MEKO_DATA` riêng cho mỗi đội. Giao diện không hiển thị thông tin CTF hoặc flag khi duyệt mua sắm bình thường.

## Kiểm thử và gói

```powershell
py -m pip install -r requirements-dev.txt
py -m pytest tests -q
py package_lab.py
```

Tạo `meko-boutique-v2-source.zip` và `meko-boutique-v2-sandbox.zip`. Sandbox ZIP có `topology.yml`, `provisioning/`, `app/`, `checker/` ngay tại gốc. Cấu hình credential riêng không nằm trong ZIP.

## CyberRange

Topology mặc định có 4 host `team1`–`team4`, mỗi đội có tài khoản/mật khẩu riêng, một LAN và router gateway. Yêu cầu image/flavor cloud, quota, dải IP, Desktop/GUI Access và chính sách SSH được ghi trong `docs/DEPLOYMENT.md`. Local tests không phải nghiệm thu trên pool CyberRange/OpenStack.

Desktop XFCE/TigerVNC được provision trước website và có entry point sửa riêng `sandbox/provisioning/gui-repair.yml`. Xem [hướng dẫn Open GUI](docs/GUI-FIX.md) khi gặp Waiting for server. Password GUI VNC khác password SSH.
