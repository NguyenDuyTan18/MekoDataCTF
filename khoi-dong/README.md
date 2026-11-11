# Bộ bật/tắt MekoDataCTF

Một CLI Python chạy **giống nhau trên Linux và Windows** (tự nhận diện hệ điều hành rồi gọi đúng lệnh).

## Chạy

```bash
# Linux
./meko.sh <lệnh>

# Windows (hoặc bấm đúp meko.bat)
python meko.py <lệnh>
```

| Lệnh | Việc |
|---|---|
| `config` | In cấu hình đã tính (bài, pool, SSH…) |
| `status` | Trạng thái: hệ điều hành, Docker, collector, SSH |
| `server` | Bật toàn bộ ForcAD (Docker) + cập nhật schema |
| `stop-server` | Tắt ForcAD (giữ dữ liệu) |
| `flag` | Bật "bộ cờ": dịch vụ cờ trong Docker + collector |
| `collector start` / `stop` / `status` | Bật/dừng/xem collector |
| `gateway start` / `stop` / `status` | Tunnel SSH mở mỗi dịch vụ VM ra một cổng cục bộ (bảng cổng tự sinh) |
| `round status` / `start [lab]` / `stop` | Xem/mở/dừng round (qua switch_round.py) |
| `check` | Chạy `check` mọi bộ chấm với một đội (phải ra `DAT 101`) |
| `all` | server + flag + mở trang web |
| `bridge` | Chạy cầu nối (cho nút trên web /admin/) |
| `bridge install` / `remove` | Cài/gỡ cầu nối tự bật khi đăng nhập |

## Thứ tự một buổi thi

```
1. meko server          # bật ForcAD (Docker) — làm khi máy chủ tắt hẳn
2. meko flag            # bật dịch vụ cờ + collector   (hoặc bấm nút "Bật bộ cờ" trên /admin/)
3. meko check           # phải DAT 101 trước khi mở round
4. mở round             # web /admin/ > Điều khiển round,  hoặc  meko round start
```
`meko all` làm gộp bước 1–2 và mở trang web.

**Thứ tự bắt buộc:** ForcAD → collector bật → mở round. Mở round khi collector chưa bật thì checker trả `110`, không có cờ.

## Cấu hình: chỉ sửa `cau-hinh.conf`

```
LABS=full_rounds,full_rounds/round2    # bài trong labs/, bài đầu là bài chính
POOL=pool141                           # thư mục trong ops/; trống = ssh_config của lab.json bài đầu
TEST_IP=10.90.0.11                     # IP một đội để thử bộ chấm
WEB=http://127.0.0.1:18080/
```

Phần còn lại (MAIN_LAB, CHECKER_DIRS lấy từ `"name"` trong lab.json, SSH_CONFIG) **tự tính**. Khai sai thì báo lỗi rõ. Xem: `python meko.py config`.

## Nút trên web /admin/

Khung **Hệ thống bộ cờ** có hai nút: **Bật bộ cờ / Dừng bộ cờ** (dịch vụ cờ + collector) và **Thêm gateway trung gian / Dừng gateway** (tunnel SSH mở mỗi dịch vụ VM ra một cổng cục bộ, bảng cổng hiện bên dưới). Cần cầu nối chạy: `python meko.py bridge install` (một lần, tự bật khi đăng nhập). Nút không bật được Docker/nginx — việc đó dùng `meko server`.

## Gateway trung gian

Mở tunnel SSH qua pool (nối vào host `checker` trên mạng thi), trình diễn mỗi dịch vụ VM ra một cổng. Đội + cổng tự đọc từ `labs/<bài>/lab.json` (`teams` + `service_ports`); cổng cấp **tuần tự từ 20001** nên thêm đội bao nhiêu cũng không trùng.

Địa chỉ: `GATEWAY_BIND` trong `cau-hinh.conf` để **trống** = tự lấy IP LAN của máy (vd `10.13.135.36:20001`, truy cập được từ LAN — nhớ mở tường lửa Windows các cổng đó). Đặt `127.0.0.1` nếu chỉ muốn máy này. Bảng cổng hiện trên /admin/ và `meko gateway status`.

## Tệp

| Tệp | Vai trò |
|---|---|
| `meko.py` | CLI chính (nhận diện OS, mọi lệnh) |
| `procs.py` | Xử lý tiến trình/mở trình duyệt đa nền tảng |
| `cau_hinh.py` | Đọc `cau-hinh.conf` và tính cấu hình |
| `host_bridge.py` | Cầu nối cho nút trên web |
| `install_bridge.py` | Cài/gỡ cầu nối tự bật |
| `meko.bat` / `meko.sh` | Tệp mỏng để bấm trên Windows / Linux |
| `cau-hinh.conf` | Cấu hình (chỉ sửa tệp này) |
| `logs/` | Nhật ký collector và cầu nối |
